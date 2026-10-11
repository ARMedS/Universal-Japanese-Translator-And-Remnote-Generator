"""OpenRouter key, models, prompts, game name."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..config import MODEL_CHOICES, Config
from .persist import PersistentWindow, start_system_move
from .style import BUTTON_CLOSE, HEADER_BG

LANGUAGES = ["ja", "en", "ch_sim", "ko", "es", "fr", "de", "ru"]


class SettingsWindow(PersistentWindow):
    persist_name = "settings"
    default_w = 520
    default_h = 820
    default_visible = False

    saved = pyqtSignal()

    def __init__(self, cfg: Config) -> None:
        super().__init__(cfg)
        self.setWindowTitle("Settings")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet("background: #1b1b1b;")
        self.setMinimumSize(360, 400)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(28)
        header.setStyleSheet(f"background: {HEADER_BG};")
        h = QHBoxLayout(header)
        h.setContentsMargins(8, 0, 0, 0)
        h.addWidget(QLabel("Settings"))
        h.addStretch(1)
        close_btn = QPushButton("X")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"background: {BUTTON_CLOSE}; font-weight: bold;")
        close_btn.clicked.connect(self.hide)
        h.addWidget(close_btn)
        header.installEventFilter(self)
        self._header = header
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        form = QFormLayout(body)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(8)

        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("sk-or-v1-…")
        form.addRow("OpenRouter API key", self.api_key)

        keys_hint = QLabel(
            '<a href="https://openrouter.ai/keys">Get an API key at openrouter.ai/keys</a>'
        )
        keys_hint.setOpenExternalLinks(True)
        form.addRow("", keys_hint)

        self.vision_model = QComboBox()
        self.vision_model.setEditable(True)
        self.vision_model.addItems(MODEL_CHOICES)
        form.addRow("Vision model", self.vision_model)

        self.flash_model = QComboBox()
        self.flash_model.setEditable(True)
        self.flash_model.addItems(MODEL_CHOICES)
        form.addRow("Flashcard model", self.flash_model)

        self.game_name = QLineEdit()
        form.addRow("Game name", self.game_name)

        self.source_lang = QComboBox()
        self.source_lang.addItems(LANGUAGES)
        self.target_lang = QComboBox()
        self.target_lang.addItems(LANGUAGES)
        lang_row = QWidget()
        lang_l = QHBoxLayout(lang_row)
        lang_l.setContentsMargins(0, 0, 0, 0)
        lang_l.addWidget(self.source_lang)
        swap = QPushButton("⇄")
        swap.setFixedWidth(36)
        swap.clicked.connect(self._swap_langs)
        lang_l.addWidget(swap)
        lang_l.addWidget(self.target_lang)
        form.addRow("Languages", lang_row)

        form.addRow(QLabel("Vision prompt"))
        self.prompt = QPlainTextEdit()
        self.prompt.setMinimumHeight(120)
        form.addRow(self.prompt)

        form.addRow(QLabel("Flashcard prompt (RemNote >> format)"))
        self.flash_prompt = QPlainTextEdit()
        self.flash_prompt.setMinimumHeight(180)
        form.addRow(self.flash_prompt)

        save = QPushButton("Save")
        save.clicked.connect(self._save)
        form.addRow(save)

        keys_path = QLabel("API key is stored in ~/.config/ujt/keys.env (mode 600), not in the project.")
        keys_path.setWordWrap(True)
        keys_path.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        form.addRow(keys_path)

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        self.reload_from_config()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._header and isinstance(event, QMouseEvent):
            if event.type() == event.Type.MouseButtonPress:
                start_system_move(self, event)
                return True
        return super().eventFilter(obj, event)

    def reload_from_config(self) -> None:
        key = self._cfg.api_key()
        self.api_key.setText(key)
        _set_combo(self.vision_model, self._cfg.vision_model)
        _set_combo(self.flash_model, self._cfg.flashcard_model)
        self.game_name.setText(self._cfg.game_name)
        _set_combo(self.source_lang, self._cfg.source_language)
        _set_combo(self.target_lang, self._cfg.target_language)
        self.prompt.setPlainText(self._cfg.load_prompt())
        self.flash_prompt.setPlainText(self._cfg.load_flashcard_prompt())

    def _swap_langs(self) -> None:
        a, b = self.source_lang.currentText(), self.target_lang.currentText()
        _set_combo(self.source_lang, b)
        _set_combo(self.target_lang, a)

    def _save(self) -> None:
        key = self.api_key.text().strip()
        if key:
            self._cfg.save_api_key(key)
        self._cfg.vision_model = self.vision_model.currentText()
        self._cfg.flashcard_model = self.flash_model.currentText()
        self._cfg.game_name = self.game_name.text().strip()
        self._cfg.source_language = self.source_lang.currentText()
        self._cfg.target_language = self.target_lang.currentText()
        self._cfg.save_prompt(self.prompt.toPlainText())
        self._cfg.save_flashcard_prompt(self.flash_prompt.toPlainText())
        self.saved.emit()
        self.hide()

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.hide()


def _set_combo(combo: QComboBox, value: str) -> None:
    if not value:
        return
    idx = combo.findText(value)
    if idx >= 0:
        combo.setCurrentIndex(idx)
    else:
        combo.setEditText(value) if combo.isEditable() else combo.addItem(value)
        if combo.isEditable():
            combo.setCurrentText(value)
