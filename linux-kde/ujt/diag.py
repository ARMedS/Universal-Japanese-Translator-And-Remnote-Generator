"""Diagnostics: a persistent log file plus a startup environment report.

Everything the app logs also lands in ~/.local/state/<config id>/ujt.log
(rotated), including uncaught exceptions and worker-thread tracebacks, so a
problem can be investigated after the fact.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import platform
import shutil
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
from PyQt6.QtGui import QGuiApplication

from . import __version__, x11
from .config import APP_ID, CONFIG_PATH

STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / APP_ID
LOG_PATH = STATE_DIR / "ujt.log"

logger = logging.getLogger("ujt")


def setup() -> None:
    """Attach the rotating file handler and route uncaught errors into it."""
    if logger.handlers:
        return
    logger.setLevel(logging.DEBUG)
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            LOG_PATH, maxBytes=512_000, backupCount=3, encoding="utf-8"
        )
    except OSError as exc:
        print(f"Could not open log file {LOG_PATH}: {exc}", file=sys.stderr)
        return
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)

    def on_exception(exc_type, exc, tb) -> None:
        logger.error("Uncaught exception", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    def on_thread_exception(args) -> None:
        logger.error(
            "Uncaught exception in thread %s", getattr(args.thread, "name", "?"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = on_exception
    threading.excepthook = on_thread_exception


def startup_report(api_key_present: bool, vision_model: str, flashcard_model: str) -> list[str]:
    """Environment facts that matter when something misbehaves."""
    env = os.environ
    lines = [
        f"UJT KDE edition {__version__} - log file {LOG_PATH}",
        f"Python {platform.python_version()}, Qt {QT_VERSION_STR}, PyQt {PYQT_VERSION_STR}, "
        f"platform plugin '{QGuiApplication.platformName()}'",
        f"Session {env.get('XDG_SESSION_TYPE', '?')} / desktop {env.get('XDG_CURRENT_DESKTOP', '?')}, "
        f"DISPLAY={env.get('DISPLAY', '-')} WAYLAND_DISPLAY={env.get('WAYLAND_DISPLAY', '-')}",
        f"OS {platform.platform()}",
    ]
    for screen in QGuiApplication.screens():
        g = screen.geometry()
        lines.append(
            f"Screen {screen.name()}: {g.width()}x{g.height()} at ({g.x()},{g.y()}), "
            f"dpr {screen.devicePixelRatio():g}, {screen.refreshRate():.0f} Hz"
        )
    lines.append(
        f"Capture method: {'X11 root-window grab' if x11.available() and not _wayland() else 'Spectacle + markers'}; "
        f"spectacle={shutil.which('spectacle') or 'missing'}"
    )
    lines.append(f"Config {CONFIG_PATH}; API key {'present' if api_key_present else 'MISSING'}")
    lines.append(f"Models: vision={vision_model}, flashcard={flashcard_model}")
    return lines


def window_snapshot(windows: dict[str, object]) -> str:
    parts = []
    for name, w in windows.items():
        g = w.geometry()  # type: ignore[attr-defined]
        state = "shown" if w.isVisible() else "hidden"  # type: ignore[attr-defined]
        parts.append(f"{name}={state}@{g.x()},{g.y()} {g.width()}x{g.height()}")
    return "; ".join(parts)


def _wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
