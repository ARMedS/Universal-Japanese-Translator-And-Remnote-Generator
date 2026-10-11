"""Simple log console."""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication, QMouseEvent, QTextCursor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from ..config import Config
from ..diag import LOG_PATH
from .persist import EDGE, PersistentWindow, apply_overlay_flags, start_system_move
from .style import BUTTON_CLOSE, HEADER_BG


class LogWindow(PersistentWindow):
    persist_name = "log"
    default_w = 640
    default_h = 320
    default_visible = False

    def __init__(self, cfg: Config) -> None:
        super().__init__(cfg)
        self.setWindowTitle("Log")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
        )
        apply_overlay_flags(self)
        self.setStyleSheet("background: #151515;")

        root = QVBoxLayout(self)
        root.setContentsMargins(EDGE, EDGE, EDGE, EDGE)
        root.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(28)
        header.setStyleSheet(f"background: {HEADER_BG};")
        h = QHBoxLayout(header)
        h.setContentsMargins(8, 0, 0, 0)
        h.addWidget(QLabel("Log"))
        h.addStretch(1)
        copy_btn = QPushButton("Copy all")
        copy_btn.setFixedHeight(28)
        copy_btn.setToolTip(f"Copy this log to the clipboard (file: {LOG_PATH})")
        copy_btn.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.view.toPlainText()))
        h.addWidget(copy_btn)
        close_btn = QPushButton("X")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"background: {BUTTON_CLOSE}; font-weight: bold;")
        close_btn.clicked.connect(self.hide)
        h.addWidget(close_btn)
        header.installEventFilter(self)
        self._header = header
        root.addWidget(header)

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(2000)
        root.addWidget(self.view, 1)
        self.enable_edge_resize()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._header and isinstance(event, QMouseEvent):
            if event.type() == event.Type.MouseButtonPress:
                start_system_move(self, event)
                return True
        return super().eventFilter(obj, event)

    def append(self, line: str) -> None:
        self.view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {line}")
        self.view.moveCursor(QTextCursor.MoveOperation.End)

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.hide()
