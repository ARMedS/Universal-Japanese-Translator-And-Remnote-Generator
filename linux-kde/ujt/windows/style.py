DARK_QSS = """
QWidget {
    color: #f2f2f2;
    font-size: 13px;
}
QPushButton {
    background: #5f5f5f;
    color: white;
    border: 1px solid #dddddd;
    padding: 4px 8px;
    min-height: 22px;
}
QPushButton:hover { background: #727272; }
QPushButton:pressed { background: #444444; }
QPushButton:disabled { background: #3a3a3a; color: #888888; }
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox {
    background: #202020;
    color: #f2f2f2;
    border: 1px solid #555555;
    padding: 4px;
    selection-background-color: #4569b0;
}
QComboBox QAbstractItemView {
    background: #202020;
    color: #f2f2f2;
    selection-background-color: #4569b0;
}
QLabel#headerTitle { font-weight: bold; }
QScrollArea { border: none; background: transparent; }
QSplitter::handle { background: #555555; }
"""

HEADER_BG = "#CC202020"
BORDER_COLOR = "#CF7F0000"
BUTTON_MONITOR = "#4569B0"
BUTTON_READER = "#45B069"
BUTTON_LOG = "#6A6A6A"
BUTTON_SNIP = "#9945B0"
BUTTON_TOGGLE = "#4A5F73"  # Hide / Show: muted slate, same for both
BUTTON_SETTINGS = "#6A6A6A"
BUTTON_CAPTURE = "#B07D45"
BUTTON_CLOSE = "#E63232"
BUTTON_SHOW = "#14B414"
