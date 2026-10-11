"""KDE Plasma helper: per-window always-on-top, minimize, and shortcuts."""

from __future__ import annotations

import shutil
import subprocess

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QWidget

from . import x11


def force_on_top(widget: QWidget) -> None:
    """Ask KWin for _NET_WM_STATE_ABOVE (EWMH client message, no subprocess)."""
    if not QGuiApplication.platformName().lower().startswith("xcb"):
        return
    x11.set_above(int(widget.winId()), True)


def clear_on_top(widget: QWidget) -> None:
    if not QGuiApplication.platformName().lower().startswith("xcb"):
        return
    x11.set_above(int(widget.winId()), False)


def minimize(widget: QWidget) -> None:
    widget.showMinimized()


def register_shortcut(name: str, executable: str, binding: str, sequence: str) -> None:
    """Register a global Plasma shortcut for `executable` under `binding`.
    No-op; KDE bind shortcuts via System Settings, this writes the default."""
    kcfg = shutil.which("kwriteconfig5")
    if not kcfg:
        return
    try:
        subprocess.run(
            [
                kcfg,
                "--file",
                "kglobalshortcutsrc",
                "--group",
                "services",
                "--key",
                f"{name}.desktop",
                f"{sequence},none,{binding}",
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        pass


def current_desktop() -> str:
    return QGuiApplication.platformName()
