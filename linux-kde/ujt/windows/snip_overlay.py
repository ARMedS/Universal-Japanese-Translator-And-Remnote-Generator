"""Drag-a-box region picker.

The desktop is grabbed first, then shown frozen and dimmed - one full-screen
pane per monitor (KWin will not let one window span several) - and the user
drags a box on any monitor and gets exactly those pixels back.

These are ordinary windows: no pointer or keyboard grab, so they can never
lock the desktop. The picker always ends: release (selection), Esc /
right-click / focus leaving all panes / a timeout (cancel).
"""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QEvent, QObject, QPoint, QRect, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen
from PyQt6.QtWidgets import QWidget

TIMEOUT_MS = 60_000
MIN_SIDE = 8


class _Pane(QWidget):
    """One monitor's worth of the frozen desktop."""

    chosen = pyqtSignal(QRect)  # rect in this pane's coordinates; empty = cancel
    lost_focus = pyqtSignal()

    def __init__(self, image: QImage, screen_rect: QRect, screen) -> None:
        super().__init__()
        self._image = image
        self._source = screen_rect  # this screen, in image pixels
        self._start: QPoint | None = None
        self._end: QPoint | None = None
        self._armed = False
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window
        )
        self.setScreen(screen)
        self.setGeometry(screen.geometry())  # fullscreen goes to the screen the window sits on
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def arm(self) -> None:
        self._armed = True

    def event(self, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.WindowDeactivate and self._armed:
            self.lost_focus.emit()
        return super().event(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.chosen.emit(QRect())
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = self._end = event.position().toPoint()
            self.update()
        else:
            self.chosen.emit(QRect())

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._start is not None:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton or self._start is None:
            return
        self._end = event.position().toPoint()
        rect = self._selection().intersected(self.rect())
        ok = rect.width() >= MIN_SIDE and rect.height() >= MIN_SIDE
        self.chosen.emit(rect if ok else QRect())

    def _selection(self) -> QRect:
        if self._start is None or self._end is None:
            return QRect()
        x0, x1 = sorted((self._start.x(), self._end.x()))
        y0, y1 = sorted((self._start.y(), self._end.y()))
        return QRect(x0, y0, x1 - x0, y1 - y0)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.drawImage(self.rect(), self._image, self._source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        sel = self._selection()
        if sel.isEmpty():
            painter.setPen(QColor(235, 235, 235))
            painter.drawText(
                self.rect().adjusted(0, 24, 0, 0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                "Drag a box around what to translate  -  Esc or right-click cancels",
            )
            return
        painter.drawImage(sel, self._image, sel.translated(self._source.topLeft()))
        painter.setPen(QPen(QColor(255, 200, 80), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(sel)


class SnipOverlay(QObject):
    """Emits `finished(rect)` in the grabbed image's pixel coordinates (empty = cancelled)."""

    finished = pyqtSignal(QRect)

    def __init__(self, rgb: np.ndarray, origin: tuple[int, int] = (0, 0)) -> None:
        super().__init__()
        self._rgb = np.ascontiguousarray(rgb)
        h, w, _ = self._rgb.shape
        self._image = QImage(self._rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
        self._panes: list[tuple[_Pane, QRect]] = []
        self._done = False
        for screen in QGuiApplication.screens():
            geo = screen.geometry()
            source = QRect(geo.x() - origin[0], geo.y() - origin[1], geo.width(), geo.height())
            source = source.intersected(self._image.rect())
            if source.isEmpty():
                continue
            pane = _Pane(self._image, source, screen)
            pane.chosen.connect(lambda r, p=pane, s=source: self._on_chosen(r, s))
            pane.lost_focus.connect(self._check_focus)
            self._panes.append((pane, source))
        QTimer.singleShot(TIMEOUT_MS, lambda: self._finish(QRect()))

    def start(self) -> None:
        if not self._panes:
            self._finish(QRect())
            return
        for pane, _ in self._panes:
            pane.showFullScreen()
        first = self._panes[0][0]
        first.raise_()
        first.activateWindow()
        first.setFocus()
        QTimer.singleShot(600, lambda: [p.arm() for p, _ in self._panes])

    def _on_chosen(self, rect: QRect, source: QRect) -> None:
        self._finish(rect.translated(source.topLeft()) if not rect.isEmpty() else QRect())

    def _check_focus(self) -> None:
        # Moving from one monitor's pane to another deactivates the first; only a
        # real switch away from every pane cancels.
        QTimer.singleShot(250, self._cancel_if_unfocused)

    def _cancel_if_unfocused(self) -> None:
        if not self._done and not any(p.isActiveWindow() for p, _ in self._panes):
            self._finish(QRect())

    def _finish(self, rect: QRect) -> None:
        if self._done:
            return
        self._done = True
        for pane, _ in self._panes:
            pane.hide()
            pane.deleteLater()
        self.finished.emit(rect)
        self.deleteLater()
