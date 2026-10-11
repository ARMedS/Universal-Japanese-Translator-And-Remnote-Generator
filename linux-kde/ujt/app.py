"""Wire capture → OpenRouter vision → Reader → RemNote flashcards."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import time
from collections import deque
from typing import Callable

from PyQt6.QtCore import QRect, QTimer, Qt
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget

from . import capture, diag, x11
from .capture import capture_frame, capture_snip, rgb_to_png
from .config import ICON_PATH, Config, ensure_config_dir
from .ipc import CommandServer, send_command
from .openrouter import complete_text, force_ipv4, translate_image
from .parser import ParseError, parse_translation
from .radicals import RadicalIndex
from .windows.capture_frame import CaptureFrame
from .windows.reader import ReaderWindow
from .windows.log_window import LogWindow
from .windows.monitor import MonitorWindow
from .windows.settings import SettingsWindow
from .windows.snip_overlay import SnipOverlay
from .windows.persist import apply_overlay_flags
from .windows.style import DARK_QSS
from .worker import CANCELLED, FnWorker


SETTLE_MS = 120
RAISE_SETTLE_MS = 300


class TranslatorApp(QApplication):
    def __init__(self, argv: list[str], capture_on_start: bool = False) -> None:
        super().__init__(argv)
        diag.setup()
        force_ipv4()
        ensure_config_dir()
        self.setApplicationName("ujt")
        self.setApplicationDisplayName("Japanese Translator")
        self.setDesktopFileName("ujt")
        self.setQuitOnLastWindowClosed(True)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.setStyleSheet(DARK_QSS)

        self.cfg = Config()
        self.radicals = RadicalIndex()
        self._workers: list[FnWorker] = []
        self._busy = False
        self._concealed: list[QWidget] = []
        self._snip_overlay = None
        self._last_hash = ""
        self._on_top = True
        self._history: deque[str] = deque(maxlen=10)

        self.log_win = LogWindow(self.cfg)
        self.monitor = MonitorWindow(self.cfg)
        self.reader = ReaderWindow(self.cfg)
        self.settings = SettingsWindow(self.cfg)
        self.frame = CaptureFrame(self.cfg)

        self.frame.capture_requested.connect(self.capture_now)
        self.frame.snip_requested.connect(self.snip_now)
        self.frame.toggle_monitor.connect(lambda: self._toggle(self.monitor))
        self.frame.toggle_reader.connect(lambda: self._toggle(self.reader))
        self.frame.toggle_log.connect(lambda: self._toggle(self.log_win))
        self.frame.toggle_settings.connect(self._show_settings)
        self.frame.quit_requested.connect(self.shutdown)
        self.reader.chunk_clicked.connect(self._on_chunk_clicked)
        self.settings.saved.connect(lambda: self.log("Settings saved"))
        self.aboutToQuit.connect(self._save_all)

        for window in (self.frame, self.monitor, self.reader, self.log_win):
            QShortcut(QKeySequence("Shift+S"), window, activated=self.capture_now)
            QShortcut(QKeySequence("Shift+R"), window, activated=self.raise_overlays)
            QShortcut(QKeySequence("F8"), window, activated=self.raise_overlays)
            QShortcut(QKeySequence("Meta+Shift+U"), window, activated=self.raise_overlays)
            QShortcut(QKeySequence("Meta+Shift+T"), window, activated=self.toggle_on_top)

        try:
            self._ipc = CommandServer(self, self._on_ipc_command)
        except RuntimeError as exc:
            self._ipc = None
            print(f"IPC server not started: {exc}", flush=True)

        self.frame.show()
        if self.monitor.should_restore_visible():
            self.monitor.show()
        if self.reader.should_restore_visible():
            self.reader.show()
        if self.settings.should_restore_visible():
            self.settings.show()
        if self.log_win.should_restore_visible():
            self.log_win.show()

        for line in diag.startup_report(
            bool(self.cfg.api_key()), self.cfg.vision_model, self.cfg.flashcard_model
        ):
            self.log(line)
        self.log("Press the i button on the frame for keys and tips.")
        if not self.cfg.api_key():
            self.log("No OpenRouter key yet - open Settings and paste it, or put OPENROUTER_API_KEY in ~/.config/ujt/keys.env", status=True)

        if capture_on_start:
            QTimer.singleShot(400, self.capture_now)

    def log(self, message: str, status: bool = False) -> None:
        """Log window + log file + stdout. `status=True` also shows it on the frame."""
        print(message, flush=True)
        diag.logger.info(message)
        self.log_win.append(message)
        if status:
            self.frame.set_status(message if len(message) < 48 else message[:45] + "…")

    def _toggle(self, window: QWidget) -> None:
        if window.isVisible():
            window.hide()
        else:
            window.show()
            window.raise_()
            window.activateWindow()

    def _show_settings(self) -> None:
        self.settings.reload_from_config()
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def _overlay_windows(self) -> list[QWidget]:
        return [self.frame, self.monitor, self.reader, self.settings, self.log_win]

    def raise_overlays(self) -> None:
        for window in (self.frame, self.reader, self.monitor, self.log_win):
            if not window.isVisible():
                continue
            apply_overlay_flags(window)
            window.show()
            window.raise_()
        self.frame.show()
        self.frame.raise_()
        if not self.frame.isMinimized():
            self.frame.activateWindow()
        self._on_top = True
        self.log("Brought capture frame to the front (Shift+R / F8).")

    def toggle_on_top(self) -> None:
        self._on_top = not self._on_top
        for window in (self.reader, self.monitor, self.log_win):
            window.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._on_top)
            window.show()
        if self._on_top:
            apply_overlay_flags(self.frame)
            self.log("Pinned above other windows (Super+Shift+T to unpin).")
        else:
            self.frame.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
            self.frame.show()
            self.log("Unpinned — normal stacking (Super+Shift+T to pin again).")

    def _on_ipc_command(self, command: str) -> None:
        if command == "capture":
            self.raise_overlays()
            QTimer.singleShot(RAISE_SETTLE_MS, self.capture_now)  # let KWin restack first
            return
        self.raise_overlays()

    def capture_now(self) -> None:
        if not self._begin_capture():
            return
        self.log("Capturing frame…", status=True)
        # Geometry is read here, on the GUI thread; grabbing and cropping run in a worker.
        spec = self.frame.frame_spec()

        diag.logger.info(
            "Capture request: frame %s,%s %sx%s scale %s chrome_hidden=%s | %s",
            spec.x, spec.y, spec.w, spec.h, spec.scale, spec.chrome_hidden,
            diag.window_snapshot(self._snapshot_windows()),
        )

        def job() -> bytes:
            t0 = time.perf_counter()
            png = capture_frame(spec)
            diag.logger.info("Grabbed + cropped in %.0f ms (%d bytes PNG)", (time.perf_counter() - t0) * 1000, len(png))
            return png

        def start() -> None:
            self._run(job, self._on_png_captured, self._on_capture_fail)

        concealed = self._conceal_overlapping(spec)
        if spec.chrome_hidden:
            self.frame.set_show_button_visible(False)
        if concealed or spec.chrome_hidden:
            QTimer.singleShot(SETTLE_MS, start)  # let the compositor drop them
        else:
            start()

    def _snapshot_windows(self) -> dict[str, QWidget]:
        return {
            "frame": self.frame,
            "monitor": self.monitor,
            "reader": self.reader,
            "log": self.log_win,
            "settings": self.settings,
        }

    def _conceal_overlapping(self, spec) -> list[QWidget]:
        """Make our own windows that sit over the frame transparent while grabbing."""
        frame_rect = QRect(spec.x, spec.y, spec.w, spec.h)
        hidden = []
        for window in (self.monitor, self.reader, self.log_win, self.settings):
            if window.isVisible() and window.geometry().intersects(frame_rect):
                window.setWindowOpacity(0.0)
                hidden.append(window)
        self._concealed = hidden
        if hidden:
            self.log(f"{len(hidden)} window(s) overlap the capture frame - hiding them for the grab.")
        return hidden

    def _reveal_concealed(self) -> None:
        for window in getattr(self, "_concealed", []):
            window.setWindowOpacity(1.0)
        self._concealed = []
        self.frame.set_show_button_visible(True)

    def snip_now(self) -> None:
        if not self._begin_capture():
            return
        grabbed = None
        if x11.available() and not capture.needs_markers():
            size = x11.root_size()
            if size is not None:
                grabbed = x11.grab_rect(0, 0, size[0], size[1])
        if grabbed is None:
            # Wayland: no global grab, so use Spectacle's own picker (in the background).
            self.log("Snip: draw a rectangle in Spectacle (Esc cancels)…", status=True)
            self._run(capture_snip, self._on_png_captured, self._on_capture_fail)
            return
        rgb, ox, oy = grabbed
        self.log("Snip: drag a box around what to translate (Esc cancels).", status=True)
        overlay = SnipOverlay(rgb, (ox, oy))
        self._snip_overlay = overlay  # keep alive

        def done(rect) -> None:
            self._snip_overlay = None
            if rect.isEmpty():
                self._on_capture_fail(CANCELLED)
                return
            crop = rgb[rect.y() : rect.y() + rect.height(), rect.x() : rect.x() + rect.width()]
            diag.logger.info("Snip region %s,%s %sx%s", rect.x() + ox, rect.y() + oy, rect.width(), rect.height())
            self._run(lambda: rgb_to_png(crop), self._on_png_captured, self._on_capture_fail)

        overlay.finished.connect(done)
        overlay.start()

    def _begin_capture(self) -> bool:
        if self._busy:
            self.log("Already translating — wait for the current request.", status=True)
            return False
        if not self.cfg.api_key():
            QMessageBox.warning(
                self.frame,
                "API key needed",
                "Set an OpenRouter API key in Settings (or ~/.config/ujt/keys.env).",
            )
            self._show_settings()
            return False
        self._busy = True
        self.frame.set_busy(True)
        return True

    def _on_capture_fail(self, message: str) -> None:
        self._reveal_concealed()
        self._busy = False
        self.frame.set_busy(False)
        if message == CANCELLED:
            self.log("Snip cancelled.", status=True)
            return
        self.log(f"Capture failed: {message}", status=True)

    def _on_png_captured(self, png: object) -> None:
        self._reveal_concealed()
        data = png if isinstance(png, (bytes, bytearray)) else b""
        if not data:
            self._on_capture_fail("empty screenshot")
            return
        digest = hashlib.sha256(data).hexdigest()
        if digest == self._last_hash:
            self._busy = False
            self.frame.set_busy(False)
            self.log("Screenshot unchanged — skipped.", status=True)
            return
        self._last_hash = digest
        self.monitor.show_png(data)
        self.log(f"Captured {len(data)} bytes — sending to {self.cfg.vision_model}", status=True)

        api_key = self.cfg.api_key()
        model = self.cfg.vision_model
        prompt = self.cfg.load_prompt()

        def work() -> str:
            t0 = time.perf_counter()
            try:
                return translate_image(api_key, model, prompt, bytes(data))
            finally:
                diag.logger.info("Vision request to %s took %.1f s", model, time.perf_counter() - t0)

        self._run(work, self._on_translated, self._on_translate_fail)

    def _on_translated(self, raw: object) -> None:
        self._busy = False
        self.frame.set_busy(False)
        text = str(raw)
        self.log(f"Vision response ({len(text)} chars)")
        try:
            translation = parse_translation(text)
        except ParseError as exc:
            self.log(f"Could not parse model JSON: {exc}")
            self.log(text[:500])
            return
        if translation.japanese:
            self._history.append(translation.japanese)
        self.reader.set_translation(translation)
        if not self.reader.isVisible():
            self.reader.show()
        n = len(translation.chunks)
        self.log(f"Got {n} chunk(s). Click a word for meaning / flashcard.", status=True)

    def _on_translate_fail(self, message: str) -> None:
        self._busy = False
        self.frame.set_busy(False)
        self.log(f"Translation failed: {message}", status=True)

    def _on_chunk_clicked(self, index: int) -> None:
        chunk = self.reader.chunk_at(index)
        if chunk is None:
            return
        if chunk.flashcard_created:
            return
        chunk.flashcard_created = True
        self._generate_flashcard(chunk.jp, chunk.en, chunk.romaji)

    def _generate_flashcard(self, jp: str, en: str, romaji: str) -> None:
        template = self.cfg.load_flashcard_prompt()
        radicals = self.radicals.format_for_prompt(jp) or "none"
        game = self.cfg.game_name or "this game"
        prompt = template.replace("{word}", jp)
        prompt = prompt.replace("{translation}", en)
        prompt = prompt.replace("{romaji}", romaji)
        prompt = prompt.replace("{radicals}", radicals)
        prompt = prompt.replace("{game_name}", game)
        prompt = re.sub(
            r'The current game is:\s*"[^"]*"',
            f'The current game is: "{game}"',
            prompt,
        )
        history = "\n".join(self._history)
        prompt += "\n\n**Generate the student's request:**\n" + history
        self.log(f"Flashcard for {jp}…")

        api_key = self.cfg.api_key()
        model = self.cfg.flashcard_model

        def work() -> str:
            t0 = time.perf_counter()
            try:
                return complete_text(api_key, model, prompt)
            finally:
                diag.logger.info("Flashcard request to %s took %.1f s", model, time.perf_counter() - t0)

        def ok(raw: object) -> None:
            text = str(raw).strip()
            if not text:
                self.log("Flashcard model returned empty text")
                return
            self.reader.append_flashcard(text)
            if not self.reader.isVisible():
                self.reader.show()
            self.log(f"Flashcard ready for {jp}", status=True)

        def fail(message: str) -> None:
            self.log(f"Flashcard failed: {message}", status=True)

        self._run(work, ok, fail)

    def _run(self, fn: Callable, ok, fail) -> None:
        worker = FnWorker(fn, self)
        self._workers.append(worker)

        def cleanup(*_args) -> None:
            if worker in self._workers:
                self._workers.remove(worker)
            worker.deleteLater()

        worker.succeeded.connect(ok)
        worker.failed.connect(fail)
        worker.finished.connect(cleanup)
        worker.start()

    def _save_all(self) -> None:
        for window in (self.frame, self.monitor, self.reader, self.settings, self.log_win):
            window.save_geometry_now()

    def shutdown(self) -> None:
        # aboutToQuit saves every window's geometry.
        if self._ipc is not None:
            self._ipc.close()
        self.quit()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Japanese visual-novel translator (Linux)")
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Take a capture (starts the app, or tells the running copy to capture)",
    )
    parser.add_argument(
        "--raise",
        dest="raise_windows",
        action="store_true",
        help="Bring the running capture frame over the game (for a Plasma shortcut)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    args = parse_args(argv[1:])
    if args.raise_windows and send_command("raise"):
        return 0
    if args.capture and send_command("capture"):
        return 0
    if not args.raise_windows and not args.capture and send_command("raise"):
        print("Already running — brought the existing windows to the front.", flush=True)
        return 0
    app = TranslatorApp(argv, capture_on_start=args.capture)
    return app.exec()
