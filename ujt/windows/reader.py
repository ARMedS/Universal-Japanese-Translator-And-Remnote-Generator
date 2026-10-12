"""Reader: the translation as clickable words, plus the flashcard pane."""

from __future__ import annotations

from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QFont, QMouseEvent, QTextCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..clipboard import copy_text
from ..config import Config
from ..parser import Chunk, Translation
from .persist import EDGE, PersistentWindow, apply_overlay_flags, start_system_move
from .style import BUTTON_CLOSE, HEADER_BG


MAX_FLASHCARDS = 150


class ReaderWindow(PersistentWindow):
    persist_name = "chatbox"
    default_w = 560
    default_h = 780
    default_visible = True

    chunk_clicked = pyqtSignal(int)

    def __init__(self, cfg: Config) -> None:
        super().__init__(cfg)
        self.setWindowTitle("Reader")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
        )
        apply_overlay_flags(self)
        self.setStyleSheet("background: rgba(0,0,0,180);")
        self.setMinimumSize(280, 240)

        self._translation: Translation | None = None
        self._flashcards: list[str] = []
        self._cjk = QFont("Noto Sans CJK JP")
        if not self._cjk.exactMatch():
            self._cjk = QFont("Noto Sans CJK")
        self._cjk.setPointSize(int(cfg.get("chatbox_font_size", 32)))

        root = QVBoxLayout(self)
        root.setContentsMargins(EDGE, EDGE, EDGE, EDGE)
        root.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(28)
        header.setStyleSheet(f"background: {HEADER_BG};")
        h = QHBoxLayout(header)
        h.setContentsMargins(8, 0, 0, 0)
        h.setSpacing(4)
        h.addWidget(QLabel("Reader"))
        h.addStretch(1)
        zoom_out = QPushButton("−")
        zoom_in = QPushButton("+")
        self.export_btn = QPushButton("Export")
        close_btn = QPushButton("X")
        zoom_out.setFixedSize(28, 28)
        zoom_in.setFixedSize(28, 28)
        self.export_btn.setFixedHeight(28)
        self.export_btn.setStyleSheet("background: #32E632; color: #111; font-weight: bold;")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"background: {BUTTON_CLOSE}; font-weight: bold;")
        zoom_out.clicked.connect(lambda: self._zoom(-6))
        zoom_in.clicked.connect(lambda: self._zoom(6))
        self.export_btn.clicked.connect(self.export_flashcards)
        close_btn.clicked.connect(self.hide)
        h.addWidget(zoom_out)
        h.addWidget(zoom_in)
        h.addWidget(self.export_btn)
        h.addWidget(close_btn)
        header.installEventFilter(self)
        self._header = header
        root.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.chunks_view = QTextBrowser()
        self.chunks_view.setOpenLinks(False)
        self.chunks_view.setOpenExternalLinks(False)
        self.chunks_view.setFont(self._cjk)
        self.chunks_view.setStyleSheet("background: transparent; border: none; padding: 8px;")
        self.chunks_view.anchorClicked.connect(self._on_anchor)
        splitter.addWidget(self.chunks_view)

        self.flash_view = QTextEdit()
        self.flash_view.setPlaceholderText("Flashcard output will appear here...")
        self.flash_view.setStyleSheet("background: rgba(0,0,0,80); border: none; padding: 8px;")
        self._apply_fonts()
        splitter.addWidget(self.flash_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self.enable_edge_resize()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._header and isinstance(event, QMouseEvent):
            if event.type() == event.Type.MouseButtonPress:
                start_system_move(self, event)
                return True
        return super().eventFilter(obj, event)

    def set_translation(self, translation: Translation) -> None:
        self._translation = translation
        self._render_chunks()

    def _render_chunks(self) -> None:
        if self._translation is None:
            self.chunks_view.setHtml("")
            return
        parts: list[str] = []
        size = self._cjk.pointSize()
        extra_pt = max(12, size - 14)
        for i, chunk in enumerate(self._translation.chunks):
            extra = ""
            if chunk.cycle == 1 and chunk.en:
                extra = (
                    f' <span style="color:#bbbbbb; font-style:italic; '
                    f'font-size:{extra_pt}pt;">({_esc(chunk.en)})</span>'
                )
            elif chunk.cycle >= 2:
                bits = [chunk.en, chunk.romaji]
                shown = " / ".join(b for b in bits if b)
                if shown:
                    extra = (
                        f' <span style="color:#bbbbbb; font-style:italic; '
                        f'font-size:{extra_pt}pt;">({_esc(shown)})</span>'
                    )
            parts.append(
                f'<a href="chunk:{i}" style="color:#ffffff; text-decoration:none; '
                f'font-size:{size}pt;">{_esc(chunk.jp)}</a>{extra}'
            )
        body = " ".join(parts) if parts else _esc(self._translation.japanese)
        self.chunks_view.setHtml(
            f'<div style="color:white; line-height:1.45; font-size:{size}pt;">{body}</div>'
        )
        self.chunks_view.moveCursor(QTextCursor.MoveOperation.End)

    def _on_anchor(self, url: QUrl) -> None:
        href = url.toString()
        if not href.startswith("chunk:"):
            QDesktopServices.openUrl(url)
            return
        try:
            index = int(href.split(":", 1)[1])
        except ValueError:
            return
        if self._translation is None or not (0 <= index < len(self._translation.chunks)):
            return
        chunk = self._translation.chunks[index]
        chunk.cycle = (chunk.cycle + 1) % 3
        self._render_chunks()
        self.chunk_clicked.emit(index)

    def append_flashcard(self, text: str) -> None:
        self._flashcards.append(text.strip())
        if len(self._flashcards) > MAX_FLASHCARDS:
            # Keep the pane (and the Export copy) bounded; rebuild only on overflow.
            del self._flashcards[: len(self._flashcards) - MAX_FLASHCARDS]
            self.flash_view.setPlainText("\n\n".join(self._flashcards) + "\n\n")
        elif len(self._flashcards) == 1:
            self.flash_view.setPlainText(self._flashcards[0] + "\n\n")
        else:
            self.flash_view.append(self._flashcards[-1] + "\n")
        self.flash_view.moveCursor(QTextCursor.MoveOperation.End)

    def flashcard_text(self) -> str:
        return self.flash_view.toPlainText()

    def export_flashcards(self) -> None:
        text = self.flash_view.toPlainText().strip()
        if not text or text == "Flashcard output will appear here...":
            return
        copy_text(text)
        original = self.export_btn.text()
        self.export_btn.setText("Copied!")
        self.export_btn.setStyleSheet("background: #32c850; color: #111; font-weight: bold;")
        from PyQt6.QtCore import QTimer

        def restore() -> None:
            self.export_btn.setText(original)
            self.export_btn.setStyleSheet("background: #32E632; color: #111; font-weight: bold;")

        QTimer.singleShot(1500, restore)

    def _zoom(self, delta: int) -> None:
        size = max(16, min(120, self._cjk.pointSize() + delta))
        self._cjk.setPointSize(size)
        self._cfg.set("chatbox_font_size", size)
        self._apply_fonts()
        self._render_chunks()

    def _apply_fonts(self) -> None:
        size = self._cjk.pointSize()
        self.chunks_view.setFont(self._cjk)
        flash = QFont(self._cjk)
        flash.setPointSize(max(14, round(size * 0.7)))
        self.flash_view.setFont(flash)
        self.flash_view.document().setDefaultFont(flash)
        self.flash_view.setStyleSheet(
            "background: rgba(0,0,0,80); border: none; padding: 8px; "
            f"font-size: {flash.pointSize()}pt;"
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.hide()

    def chunk_at(self, index: int) -> Chunk | None:
        if self._translation is None:
            return None
        if 0 <= index < len(self._translation.chunks):
            return self._translation.chunks[index]
        return None

    def full_sentence(self) -> str:
        return self._translation.japanese if self._translation else ""


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
