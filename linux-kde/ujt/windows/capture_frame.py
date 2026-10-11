"""Transparent always-on-top capture region - the main window.

The interior (the part that is captured) is click-through: the window's input
shape excludes it, so clicks reach the game underneath. Only the border, the
toolbar and the resize grip take the mouse.
"""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QRect, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPen, QRegion
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizeGrip,
    QVBoxLayout,
    QWidget,
)

from ..capture import (
    BORDER_PX,
    GRIP_H,
    HEADER_H,
    MARKER_RGB,
    MARKER_SIZE,
    FrameSpec,
    needs_markers,
)
from ..config import Config
from .persist import PersistentWindow, apply_overlay_flags, start_system_move
from .style import (
    BORDER_COLOR,
    BUTTON_CAPTURE,
    BUTTON_CLOSE,
    BUTTON_LOG,
    BUTTON_MONITOR,
    BUTTON_READER,
    BUTTON_SETTINGS,
    BUTTON_SNIP,
    BUTTON_TOGGLE,
)

BORDER = BORDER_PX
MIN_FADE = 0.05

HELP_HTML = """
<div style="color:#bdbdbd; font-size:12px; line-height:150%;">
<b>Keys</b><br>
Shift+S &nbsp;capture the frame<br>
Shift+R / F8 &nbsp;bring the frame to the front<br>
Super+Shift+T &nbsp;pin / unpin above other windows<br>
<br>
<b>Tips</b><br>
Clicks pass through the inside of the frame to the game.<br>
Drag the toolbar to move; drag the corner grip to resize.<br>
&minus; / + fade the frame and the toolbar (buttons still work when faint).<br>
Hide keeps just Capture and Show.<br>
Click the popup (or i again) to close it.<br>
Click a word in the Reader for its meaning, again for a flashcard.<br>
<br>
Snip: drag a box around anything on screen (a button, a menu) and just that is translated.
</div>
"""


class CaptureFrame(PersistentWindow):
    persist_name = "capture_frame"
    default_w = 900
    default_h = 380
    default_visible = True

    capture_requested = pyqtSignal()
    snip_requested = pyqtSignal()
    toggle_monitor = pyqtSignal()
    toggle_reader = pyqtSignal()
    toggle_log = pyqtSignal()
    toggle_settings = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, cfg: Config) -> None:
        super().__init__(cfg)
        self.setWindowTitle("Japanese Translator")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
        )
        apply_overlay_flags(self)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(280, 140)

        self._chrome_hidden = False
        self._border_opacity = cfg.border_opacity
        self._draw_markers = needs_markers()
        self._help: QLabel | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(BORDER, 0, BORDER, BORDER)
        root.setSpacing(0)

        # ---- toolbar -------------------------------------------------------
        self.header = QWidget()
        self.header.setFixedHeight(HEADER_H)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 12, 8, 4)
        header_layout.setSpacing(6)

        self.hide_btn = QPushButton("Hide")
        self.capture_btn = QPushButton("Capture")
        self.snip_btn = QPushButton("Snip")
        self.monitor_btn = QPushButton("Monitor")
        self.reader_btn = QPushButton("Reader")
        self.log_btn = QPushButton("Log")
        self.settings_btn = QPushButton("Settings")
        self.opacity_minus = QPushButton("−")
        self.opacity_plus = QPushButton("+")
        self.info_btn = QPushButton("i")
        self.close_btn = QPushButton("X")

        self.capture_btn.setStyleSheet(f"background: {BUTTON_CAPTURE}; font-weight: bold;")
        self.hide_btn.setStyleSheet(f"background: {BUTTON_TOGGLE};")
        self.snip_btn.setStyleSheet(f"background: {BUTTON_SNIP};")
        self.monitor_btn.setStyleSheet(f"background: {BUTTON_MONITOR};")
        self.reader_btn.setStyleSheet(f"background: {BUTTON_READER};")
        self.log_btn.setStyleSheet(f"background: {BUTTON_LOG};")
        self.settings_btn.setStyleSheet(f"background: {BUTTON_SETTINGS};")
        self.close_btn.setStyleSheet(f"background: {BUTTON_CLOSE}; font-weight: bold;")
        for small in (self.opacity_minus, self.opacity_plus, self.info_btn):
            small.setFixedWidth(28)
        self.close_btn.setFixedWidth(32)
        self.capture_btn.setToolTip("Capture the area inside this frame (Shift+S)")
        self.snip_btn.setToolTip("Drag a box around any part of the screen to translate just that")
        self.reader_btn.setToolTip("Translated text, word by word, and flashcards")
        self.monitor_btn.setToolTip("Preview of the last capture")
        self.info_btn.setToolTip("Keys and tips")

        for btn in (
            self.hide_btn,
            self.capture_btn,
            self.snip_btn,
            self.monitor_btn,
            self.reader_btn,
            self.log_btn,
            self.settings_btn,
        ):
            header_layout.addWidget(btn)
        header_layout.addStretch(1)
        self.status = QLabel("")
        self.status.setStyleSheet("color: #9a9a9a; font-size: 11px; background: transparent;")
        header_layout.addWidget(self.status)
        header_layout.addWidget(self.opacity_minus)
        header_layout.addWidget(self.opacity_plus)
        header_layout.addWidget(self.info_btn)
        header_layout.addWidget(self.close_btn)
        self.header.setObjectName("toolbar")
        self.header.setStyleSheet("QWidget#toolbar { background: rgba(32,32,32,220); }")
        root.addWidget(self.header)

        # ---- interior (click-through) ---------------------------------------
        self.body = QWidget()
        self.body.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        root.addWidget(self.body, 1)

        grip_row = QHBoxLayout()
        grip_row.addStretch(1)
        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(GRIP_H, GRIP_H)
        grip_row.addWidget(self.grip, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        root.addLayout(grip_row)

        # ---- mini bar: all that remains after Hide ---------------------------
        self.mini_bar = QWidget(self)
        mini = QHBoxLayout(self.mini_bar)
        mini.setContentsMargins(4, 4, 4, 4)
        mini.setSpacing(6)
        self.mini_capture_btn = QPushButton("Capture")
        self.mini_capture_btn.setStyleSheet(f"background: {BUTTON_CAPTURE}; font-weight: bold;")
        self.show_btn = QPushButton("Show")
        self.show_btn.setStyleSheet(f"background: {BUTTON_TOGGLE};")
        mini.addWidget(self.mini_capture_btn)
        mini.addWidget(self.show_btn)
        self.mini_bar.setObjectName("minibar")
        self.mini_bar.setStyleSheet("QWidget#minibar { background: rgba(32,32,32,220); }")
        self.mini_bar.adjustSize()
        self.mini_bar.move(BORDER + 6, BORDER + 6)
        self.mini_bar.hide()

        self._effects: dict[QWidget, QGraphicsOpacityEffect] = {}
        for bar in (self.header, self.mini_bar):
            effect = QGraphicsOpacityEffect(bar)
            bar.setGraphicsEffect(effect)
            bar.installEventFilter(self)
            self._effects[bar] = effect

        self.hide_btn.clicked.connect(self.hide_chrome)
        self.show_btn.clicked.connect(self.show_chrome)
        for btn in (self.capture_btn, self.mini_capture_btn):
            btn.clicked.connect(self.capture_requested.emit)
        self.snip_btn.clicked.connect(self.snip_requested.emit)
        self.monitor_btn.clicked.connect(self.toggle_monitor.emit)
        self.reader_btn.clicked.connect(self.toggle_reader.emit)
        self.log_btn.clicked.connect(self.toggle_log.emit)
        self.settings_btn.clicked.connect(self.toggle_settings.emit)
        self.close_btn.clicked.connect(self.quit_requested.emit)
        self.info_btn.clicked.connect(self._toggle_help)
        self.opacity_minus.clicked.connect(lambda: self._nudge_opacity(-0.1))
        self.opacity_plus.clicked.connect(lambda: self._nudge_opacity(0.1))

        self._refresh_fade()
        self._update_input_shape()

    # ------------------------------------------------------------ events

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj in self._effects:
            kind = event.type()
            if obj is self.header and isinstance(event, QMouseEvent):
                if kind == QEvent.Type.MouseButtonPress:
                    start_system_move(self, event)
                    return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_S and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.capture_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        QTimer.singleShot(0, self._update_input_shape)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_input_shape()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        color = QColor(BORDER_COLOR)
        color.setAlphaF(self._border_opacity)
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        outer = QColor(127, 0, 0, int(80 * self._border_opacity))
        thick = QPen(outer)
        thick.setWidth(BORDER)
        painter.setPen(thick)
        painter.drawRect(self.rect().adjusted(BORDER // 2, BORDER // 2, -(BORDER // 2) - 1, -(BORDER // 2) - 1))
        r = self.rect()
        if not self._chrome_hidden:
            # Everything below this line (the grip row) is not captured.
            painter.setPen(QPen(color, 1))
            gy = r.bottom() - BORDER - GRIP_H + 1
            painter.drawLine(BORDER, gy, r.right() - BORDER, gy)
        if self._draw_markers:
            # Wayland only: corner markers let the capture find the frame.
            marker = QColor(*MARKER_RGB)
            s = MARKER_SIZE
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(r.left(), r.top(), s, s, marker)
            painter.fillRect(r.right() - s + 1, r.top(), s, s, marker)
            painter.fillRect(r.left(), r.bottom() - s + 1, s, s, marker)
            painter.fillRect(r.right() - s + 1, r.bottom() - s + 1, s, s, marker)

    # ------------------------------------------------------------ chrome

    def hide_chrome(self) -> None:
        self._chrome_hidden = True
        self._close_help()
        self.header.hide()
        self.grip.hide()
        self.mini_bar.adjustSize()
        self.mini_bar.show()
        self.mini_bar.raise_()
        self._refresh_fade()
        self._update_input_shape()
        self.update()

    def show_chrome(self) -> None:
        self._chrome_hidden = False
        self.header.show()
        self.grip.show()
        self.mini_bar.hide()
        self._refresh_fade()
        self._update_input_shape()
        self.update()

    @property
    def chrome_hidden(self) -> bool:
        return self._chrome_hidden

    def set_status(self, text: str) -> None:
        self.status.setText(text)

    def set_busy(self, busy: bool) -> None:
        for btn in (self.capture_btn, self.mini_capture_btn):
            btn.setEnabled(not busy)
            btn.setText("Working…" if busy else "Capture")
        self.snip_btn.setEnabled(not busy)
        self.mini_bar.adjustSize()

    def set_show_button_visible(self, visible: bool) -> None:
        """The mini bar sits inside the capture area; hide it while grabbing."""
        if self._chrome_hidden:
            self.mini_bar.setVisible(visible)

    def frame_spec(self) -> FrameSpec:
        return FrameSpec.from_widget(self, self._chrome_hidden)

    def interior_local_rect(self) -> QRect:
        """The captured area in window coordinates (matches capture._crop_interior)."""
        top = BORDER if self._chrome_hidden else HEADER_H
        bottom = BORDER if self._chrome_hidden else BORDER + GRIP_H
        return QRect(BORDER, top, max(1, self.width() - 2 * BORDER), max(1, self.height() - top - bottom))

    # ------------------------------------------------------- click-through

    def _update_input_shape(self) -> None:
        """Restrict the window (and so its input) to everything except the interior."""
        region = QRegion(self.rect()).subtracted(QRegion(self.interior_local_rect()))
        if self._chrome_hidden and self.mini_bar.isVisible():
            region = region.united(QRegion(self.mini_bar.geometry()))
        self.setMask(region)

    # ------------------------------------------------------------- fading

    def _refresh_fade(self) -> None:
        """Toolbar and mini bar follow the same −/+ level as the border."""
        level = max(MIN_FADE, self._border_opacity)
        for effect in self._effects.values():
            effect.setOpacity(level)

    def _nudge_opacity(self, delta: float) -> None:
        self._border_opacity = max(0.05, min(1.0, self._border_opacity + delta))
        self._cfg.border_opacity = self._border_opacity
        self._refresh_fade()
        self.update()

    # --------------------------------------------------------------- help

    def _toggle_help(self) -> None:
        if self._help is not None:
            self._close_help()
            return
        self._help = _HelpPopup(HELP_HTML)
        self._help.destroyed.connect(lambda *_: setattr(self, "_help", None))
        anchor = self.info_btn.mapToGlobal(self.info_btn.rect().bottomRight())
        self._help.move(anchor.x() - self._help.width(), anchor.y() + 4)
        self._help.show()

    def _close_help(self) -> None:
        popup, self._help = self._help, None
        if popup is not None:
            popup.close()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._close_help()
        super().hideEvent(event)


class _HelpPopup(QLabel):
    """Tips box. A plain tool window: it never grabs the mouse or keyboard
    (a Qt.Popup does, and a stuck grab locks the whole desktop on X11).
    Closes on click, after a timeout, or when its owner hides."""

    AUTO_CLOSE_MS = 20000

    def __init__(self, html: str) -> None:
        super().__init__(html)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet("background: rgba(24,24,24,235); border: 1px solid #444444; padding: 10px;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adjustSize()
        QTimer.singleShot(self.AUTO_CLOSE_MS, self.close)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.close()
