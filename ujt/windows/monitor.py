"""Last-captured screenshot preview."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QMouseEvent, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ..config import Config
from PyQt6.QtGui import QGuiApplication

from .persist import EDGE, PersistentWindow, apply_overlay_flags, start_system_move
from .style import BUTTON_CLOSE, HEADER_BG


class MonitorWindow(PersistentWindow):
    persist_name = "monitor"
    default_w = 720
    default_h = 420
    default_visible = True

    def __init__(self, cfg: Config) -> None:
        super().__init__(cfg)
        self.setWindowTitle("Monitor")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
        )
        apply_overlay_flags(self)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet("background: #111111;")

        root = QVBoxLayout(self)
        root.setContentsMargins(EDGE, EDGE, EDGE, EDGE)
        root.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(28)
        header.setStyleSheet(f"background: {HEADER_BG};")
        h = QHBoxLayout(header)
        h.setContentsMargins(8, 0, 0, 0)
        title = QLabel("Monitor")
        title.setStyleSheet("font-weight: bold;")
        h.addWidget(title)
        h.addStretch(1)
        close_btn = QPushButton("X")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"background: {BUTTON_CLOSE}; font-weight: bold;")
        close_btn.clicked.connect(self.hide)
        h.addWidget(close_btn)
        header.installEventFilter(self)
        self._header = header
        root.addWidget(header)

        self.image = QLabel("No capture yet")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setStyleSheet("color: #888888; background: #000000;")
        self.image.setMinimumHeight(120)
        self._original: QPixmap | None = None
        root.addWidget(self.image, 1)

        self.status = QLabel("")
        self.status.setStyleSheet("color: #aaaaaa; padding: 4px 8px;")
        root.addWidget(self.status)
        self._last_size: tuple[int, int] | None = None
        self.enable_edge_resize()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._header and isinstance(event, QMouseEvent):
            if event.type() == event.Type.MouseButtonPress:
                start_system_move(self, event)
                return True
        return super().eventFilter(obj, event)

    def show_png(self, png: bytes) -> None:
        image = QImage.fromData(png, "PNG")
        if image.isNull():
            self.image.setText("Could not decode PNG")
            return
        self._original = QPixmap.fromImage(image)
        self.status.setText(f"{image.width()}×{image.height()}")
        size = (image.width(), image.height())
        if size != self._last_size:
            self._last_size = size
            self._fit_to_image(size)
        self._rescale()

    def _fit_to_image(self, size: tuple[int, int]) -> None:
        """Resize so the capture shows 1:1, capped to 70% of the screen."""
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return
        avail = screen.availableGeometry()
        extra_w, extra_h = 2 * EDGE, 2 * EDGE + 28 + 28  # ring + header + status
        w = min(size[0] + extra_w, int(avail.width() * 0.7))
        h = min(size[1] + extra_h, int(avail.height() * 0.7))
        self.resize(max(260, w), max(160, h))

    def _rescale(self) -> None:
        if self._original is None or self._original.isNull():
            return
        self.image.setPixmap(
            self._original.scaled(
                self.image.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._rescale()

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.hide()
