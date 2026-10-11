"""Save/restore window size, position, and visibility (KDE edition)."""

from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QCursor, QGuiApplication, QMouseEvent
from PyQt6.QtWidgets import QWidget

from ..config import Config
from ..kde import force_on_top


EDGE = 8  # px ring around resizable windows that grabs the mouse
CORNER = 22  # px square at the bottom corners


class _CornerGrip(QWidget):
    """Invisible, generous resize handle sitting over a bottom corner."""

    def __init__(self, parent: QWidget, edges: Qt.Edge, cursor: Qt.CursorShape) -> None:
        super().__init__(parent)
        self._edges = edges
        self.setFixedSize(CORNER, CORNER)
        self.setCursor(QCursor(cursor))
        self.setStyleSheet("background: transparent;")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        handle = self.window().windowHandle()
        if event.button() == Qt.MouseButton.LeftButton and handle is not None:
            handle.startSystemResize(self._edges)


class PersistentWindow(QWidget):
    persist_name = ""
    default_w = 640
    default_h = 400
    default_visible = True

    def __init__(self, cfg: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(250)
        self._save_timer.timeout.connect(self.save_geometry_now)
        self._persist_enabled = True
        self._placed = False
        self._grips: list[tuple[_CornerGrip, bool]] = []
        self._restore_geometry()

    def enable_edge_resize(self) -> None:
        """Make the whole border ring and both bottom corners easy to grab.

        The window's root layout must use EDGE-px content margins so the ring is
        not covered by child widgets.
        """
        self.setMouseTracking(True)
        left = _CornerGrip(self, Qt.Edge.LeftEdge | Qt.Edge.BottomEdge, Qt.CursorShape.SizeBDiagCursor)
        right = _CornerGrip(self, Qt.Edge.RightEdge | Qt.Edge.BottomEdge, Qt.CursorShape.SizeFDiagCursor)
        self._grips = [(left, False), (right, True)]
        self._place_grips()

    def _place_grips(self) -> None:
        for grip, is_right in self._grips:
            x = self.width() - CORNER if is_right else 0
            grip.move(x, self.height() - CORNER)
            grip.raise_()

    def _edges_at(self, x: int, y: int) -> Qt.Edge:
        edges = Qt.Edge(0)
        if x < EDGE:
            edges |= Qt.Edge.LeftEdge
        elif x >= self.width() - EDGE:
            edges |= Qt.Edge.RightEdge
        if y < EDGE:
            edges |= Qt.Edge.TopEdge
        elif y >= self.height() - EDGE:
            edges |= Qt.Edge.BottomEdge
        return edges

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._grips:
            e = self._edges_at(int(event.position().x()), int(event.position().y()))
            horizontal = bool(e & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
            vertical = bool(e & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
            if horizontal and vertical:
                diag = (e & Qt.Edge.LeftEdge and e & Qt.Edge.BottomEdge) or (
                    e & Qt.Edge.RightEdge and e & Qt.Edge.TopEdge
                )
                self.setCursor(Qt.CursorShape.SizeBDiagCursor if diag else Qt.CursorShape.SizeFDiagCursor)
            elif horizontal:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif vertical:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.unsetCursor()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._grips and event.button() == Qt.MouseButton.LeftButton:
            e = self._edges_at(int(event.position().x()), int(event.position().y()))
            handle = self.windowHandle()
            if e and handle is not None:
                handle.startSystemResize(e)
                return
        super().mousePressEvent(event)

    def _restore_geometry(self) -> None:
        saved = self._cfg.window(self.persist_name) if self.persist_name else None
        if not saved:
            self.resize(self.default_w, self.default_h)
            return
        w = int(saved.get("w") or self.default_w)
        h = int(saved.get("h") or self.default_h)
        self.resize(max(200, w), max(80, h))

    def _apply_saved_position(self) -> None:
        saved = self._cfg.window(self.persist_name) if self.persist_name else None
        if not saved or "x" not in saved or "y" not in saved:
            return
        x, y = int(saved["x"]), int(saved["y"])
        w = max(200, int(saved.get("w") or self.width()))
        h = max(80, int(saved.get("h") or self.height()))
        screens = QGuiApplication.screens()
        if not screens:
            return
        named = str(saved.get("screen") or "")
        target = None
        for screen in screens:
            if named and screen.name() == named:
                target = screen
                break
        on_a_screen = any(s.geometry().adjusted(-80, -80, 80, 80).contains(x, y) for s in screens)
        self._persist_enabled = False
        if on_a_screen:
            self.setGeometry(x, y, w, h)
        elif target is not None:
            avail = target.availableGeometry()
            self.setGeometry(
                avail.x() + 48,
                avail.y() + 48,
                min(w, avail.width() - 80),
                min(h, avail.height() - 80),
            )
        self._persist_enabled = True
        self._placed = True

    def should_restore_visible(self) -> bool:
        saved = self._cfg.window(self.persist_name) if self.persist_name else None
        if not saved or "visible" not in saved:
            return self.default_visible
        return bool(saved["visible"])

    def set_persist_enabled(self, enabled: bool) -> None:
        self._persist_enabled = enabled

    def save_geometry_now(self) -> None:
        if not self.persist_name or not self._persist_enabled:
            return
        geo = self.geometry()
        screen = QGuiApplication.screenAt(geo.center())
        self._cfg.set_window(
            self.persist_name,
            geo.x(),
            geo.y(),
            geo.width(),
            geo.height(),
            self.isVisible(),
            screen.name() if screen is not None else "",
        )

    def schedule_save(self) -> None:
        self._save_timer.start()

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        self.schedule_save()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._place_grips()
        self.schedule_save()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._placed:
            QTimer.singleShot(50, self._apply_saved_position)
            QTimer.singleShot(350, self._apply_saved_position)

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        self.save_geometry_now()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.save_geometry_now()
        super().closeEvent(event)


def start_system_move(widget: QWidget, event: QMouseEvent) -> None:
    if event.button() != Qt.MouseButton.LeftButton:
        return
    handle = widget.window().windowHandle()
    if handle is not None:
        handle.startSystemMove()


def apply_overlay_flags(widget: QWidget) -> None:
    if not widget.windowFlags() & Qt.WindowType.WindowStaysOnTopHint:
        widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
    if widget.isVisible():
        force_on_top(widget)


def _is_wayland() -> bool:
    try:
        return QGuiApplication.platformName().lower().startswith("wayland")
    except Exception:
        return False
