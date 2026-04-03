MAIN_QSS = """
/* ─── 전역 ─────────────────────────────────── */
QWidget {
    background-color: #0a0f1a;
    color: #c8d8e8;
    font-family: "맑은 고딕", "Malgun Gothic", "Arial";
    font-size: 13px;
}

QMainWindow {
    background-color: #0a0f1a;
}

/* ─── 스크롤바 ─────────────────────────────── */
QScrollBar:vertical {
    background: #0d1525;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #1e3a5f;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ─── 버튼 ─────────────────────────────────── */
QPushButton {
    background-color: #0d2040;
    color: #4fc3f7;
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    padding: 8px 18px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #1a3a6a;
    border: 1px solid #4fc3f7;
    color: #80d8ff;
}
QPushButton:pressed {
    background-color: #0a1830;
    color: #00b0ff;
}
QPushButton:disabled {
    background-color: #0a1528;
    color: #334455;
    border: 1px solid #1a2535;
}

/* 강조 버튼 (class=primary) */
QPushButton[class="primary"] {
    background-color: #0d3060;
    color: #ffd700;
    border: 1px solid #ffd700;
    font-size: 15px;
    padding: 10px 24px;
}
QPushButton[class="primary"]:hover {
    background-color: #1a4a90;
    color: #ffe066;
    border-color: #ffe066;
}

/* 위험 버튼 (class=danger) */
QPushButton[class="danger"] {
    background-color: #300a0a;
    color: #ef5350;
    border: 1px solid #ef5350;
}
QPushButton[class="danger"]:hover {
    background-color: #4a1010;
    border-color: #ff6e6e;
    color: #ff6e6e;
}

/* ─── 레이블 ────────────────────────────────── */
QLabel {
    background: transparent;
}
QLabel[class="title"] {
    color: #ffd700;
    font-size: 26px;
    font-weight: bold;
    letter-spacing: 2px;
}
QLabel[class="subtitle"] {
    color: #4fc3f7;
    font-size: 15px;
    font-weight: bold;
}
QLabel[class="section"] {
    color: #4fc3f7;
    font-size: 14px;
    font-weight: bold;
    border-bottom: 1px solid #1e3a5f;
    padding-bottom: 4px;
}
QLabel[class="gold"] {
    color: #ffd700;
    font-weight: bold;
    font-size: 14px;
}

/* ─── 테이블 ────────────────────────────────── */
QTableWidget {
    background-color: #0d1525;
    alternate-background-color: #0f1d30;
    gridline-color: #1e3a5f;
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    selection-background-color: #1a3a6a;
}
QTableWidget::item {
    padding: 4px 8px;
}
QHeaderView::section {
    background-color: #0a1830;
    color: #4fc3f7;
    border: none;
    border-bottom: 1px solid #1e3a5f;
    border-right: 1px solid #1e3a5f;
    padding: 6px 8px;
    font-weight: bold;
}

/* ─── 콤보박스 ──────────────────────────────── */
QComboBox {
    background-color: #0d1525;
    color: #c8d8e8;
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    padding: 5px 10px;
    min-width: 120px;
}
QComboBox:hover { border-color: #4fc3f7; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #0d1525;
    color: #c8d8e8;
    selection-background-color: #1a3a6a;
    border: 1px solid #1e3a5f;
}

/* ─── 프레임 / 카드 ─────────────────────────── */
QFrame[class="card"] {
    background-color: #0d1525;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
}
QFrame[class="card"]:hover {
    border-color: #4fc3f7;
}
QFrame[class="card-selected"] {
    background-color: #0f2040;
    border: 2px solid #ffd700;
    border-radius: 6px;
}

/* ─── 구분선 ────────────────────────────────── */
QFrame[frameShape="4"],   /* HLine */
QFrame[frameShape="5"] {  /* VLine */
    color: #1e3a5f;
}

/* ─── 탭 위젯 ───────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #1e3a5f;
    background-color: #0a0f1a;
}
QTabBar::tab {
    background: #0d1525;
    color: #7a9ab8;
    border: 1px solid #1e3a5f;
    border-bottom: none;
    padding: 6px 16px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #0a1830;
    color: #4fc3f7;
    border-top: 2px solid #4fc3f7;
}
QTabBar::tab:hover { color: #c8d8e8; }

/* ─── 입력 필드 ─────────────────────────────── */
QLineEdit {
    background-color: #0d1525;
    color: #c8d8e8;
    border: 1px solid #1e3a5f;
    border-radius: 4px;
    padding: 5px 8px;
}
QLineEdit:focus { border-color: #4fc3f7; }

/* ─── 메시지박스 ────────────────────────────── */
QMessageBox {
    background-color: #0a0f1a;
}
QMessageBox QPushButton { min-width: 80px; }
"""


GRADE_STYLE = {
    "SSS": "color: #FFD700; font-weight: bold;",
    "SS":  "color: #E8E8E8; font-weight: bold;",
    "S":   "color: #C0C0C0; font-weight: bold;",
    "A":   "color: #4FC3F7; font-weight: bold;",
    "B":   "color: #81C784; font-weight: bold;",
    "C":   "color: #FFFFFF;",
    "D":   "color: #FFB74D;",
    "E":   "color: #EF9A9A;",
    "F":   "color: #EF5350;",
}

RACE_COLORS = {
    "테란":    "#4FC3F7",
    "저그":    "#81C784",
    "프로토스": "#CE93D8",
}
