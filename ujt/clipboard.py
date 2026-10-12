"""Copy text via wl-copy, with Qt clipboard as fallback."""

from __future__ import annotations

import shutil
import subprocess

from PyQt6.QtWidgets import QApplication


def copy_text(text: str) -> None:
    if not text:
        return
    wl_copy = shutil.which("wl-copy")
    if wl_copy:
        result = subprocess.run(
            [wl_copy, "--", text],
            input=text.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        clipboard.setText(text)
