"""마이 스타리그 — 모던 라이트 테마 v3"""

# ── 컬러 토큰 ────────────────────────────────────────────────
C_BG      = "#F8F9FA"
C_CARD    = "#FFFFFF"
C_BORDER  = "#E9ECEF"
C_INDIGO  = "#5B6CF6"
C_CORAL   = "#FF6B6B"
C_GREEN   = "#51CF66"
C_TEXT    = "#212529"
C_SUBTEXT = "#868E96"
C_GOLD    = "#F59E0B"
C_HOVER   = "#F1F3F5"
C_SELECTED = "#EEF2FF"

MAIN_QSS = """
/* ─── 전역 ─────────────────────────────────── */
QWidget {
    background-color: #F8F9FA;
    color: #212529;
    font-family: "맑은 고딕", "Malgun Gothic", "Noto Sans KR", "Arial";
    font-size: 13px;
}
QMainWindow { background-color: #F8F9FA; }

/* ─── 스크롤바 ─────────────────────────────── */
QScrollBar:vertical {
    background: #F1F3F5;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #CED4DA;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #5B6CF6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ─── 기본 버튼 ─────────────────────────────── */
QPushButton {
    background-color: #FFFFFF;
    color: #495057;
    border: 1px solid #DEE2E6;
    border-radius: 10px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #F1F3F5;
    border-color: #5B6CF6;
    color: #5B6CF6;
}
QPushButton:pressed {
    background-color: #E7E9FB;
}
QPushButton:disabled {
    background-color: #F8F9FA;
    color: #ADB5BD;
    border-color: #E9ECEF;
}

/* 강조 버튼 (primary) */
QPushButton[class="primary"] {
    background-color: #5B6CF6;
    color: #FFFFFF;
    border: none;
    font-size: 14px;
    padding: 10px 24px;
    border-radius: 10px;
}
QPushButton[class="primary"]:hover {
    background-color: #4A5CE0;
}
QPushButton[class="primary"]:pressed {
    background-color: #3A4BC8;
}
QPushButton[class="primary"]:disabled {
    background-color: #ADB5BD;
    color: #FFFFFF;
}

/* 위험 버튼 (danger) */
QPushButton[class="danger"] {
    background-color: #FFF5F5;
    color: #FF6B6B;
    border: 1px solid #FF6B6B;
    border-radius: 10px;
}
QPushButton[class="danger"]:hover {
    background-color: #FFE3E3;
    border-color: #FF4444;
    color: #FF4444;
}

/* ─── 레이블 ────────────────────────────────── */
QLabel { background: transparent; }
QLabel[class="title"] {
    color: #212529;
    font-size: 24px;
    font-weight: bold;
}
QLabel[class="subtitle"] {
    color: #5B6CF6;
    font-size: 15px;
    font-weight: bold;
}
QLabel[class="section"] {
    color: #5B6CF6;
    font-size: 14px;
    font-weight: bold;
    border-bottom: 2px solid #5B6CF6;
    padding-bottom: 4px;
}
QLabel[class="gold"] {
    color: #F59E0B;
    font-weight: bold;
    font-size: 14px;
}

/* ─── 테이블 ────────────────────────────────── */
QTableWidget {
    background-color: #FFFFFF;
    alternate-background-color: #FAFAFA;
    gridline-color: #E9ECEF;
    border: 1px solid #E9ECEF;
    border-radius: 8px;
    selection-background-color: #EEF2FF;
    selection-color: #212529;
}
QTableWidget::item {
    padding: 6px 8px;
    border: none;
    color: #212529;
}
QTableWidget::item:hover { background-color: #F8F9FA; }
QTableWidget::item:selected { background-color: #EEF2FF; color: #212529; }
QHeaderView::section {
    background-color: #F1F3F5;
    color: #868E96;
    border: none;
    border-bottom: 1px solid #E9ECEF;
    border-right: 1px solid #E9ECEF;
    padding: 7px 8px;
    font-weight: bold;
    font-size: 12px;
}

/* ─── 콤보박스 ──────────────────────────────── */
QComboBox {
    background-color: #FFFFFF;
    color: #212529;
    border: 1px solid #DEE2E6;
    border-radius: 8px;
    padding: 6px 12px;
    min-width: 120px;
}
QComboBox:hover { border-color: #5B6CF6; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #212529;
    selection-background-color: #EEF2FF;
    border: 1px solid #E9ECEF;
    border-radius: 8px;
}

/* ─── 프레임 / 카드 ─────────────────────────── */
QFrame[class="card"] {
    background-color: #FFFFFF;
    border: 1px solid #E9ECEF;
    border-radius: 16px;
}
QFrame[class="card"]:hover {
    border-color: #5B6CF6;
    background-color: #FAFAFA;
}
QFrame[class="card-selected"] {
    background-color: #EEF2FF;
    border: 2px solid #5B6CF6;
    border-radius: 16px;
}

/* ─── 구분선 ────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #E9ECEF;
}

/* ─── 탭 ────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #E9ECEF;
    background-color: #FFFFFF;
    border-radius: 8px;
}
QTabBar::tab {
    background: #F8F9FA;
    color: #868E96;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 8px 18px;
    margin-right: 4px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: #F8F9FA;
    color: #5B6CF6;
    border-bottom: 2px solid #5B6CF6;
}
QTabBar::tab:hover { color: #5B6CF6; }

/* ─── 입력 필드 ─────────────────────────────── */
QLineEdit {
    background-color: #FFFFFF;
    color: #212529;
    border: 1px solid #DEE2E6;
    border-radius: 8px;
    padding: 6px 10px;
}
QLineEdit:focus { border-color: #5B6CF6; }

/* ─── 메시지박스 ────────────────────────────── */
QMessageBox { background-color: #FFFFFF; }
QMessageBox QLabel { color: #212529; }
QMessageBox QPushButton { min-width: 80px; }

/* ─── 프로그레스바 ──────────────────────────── */
QProgressBar {
    background-color: #E9ECEF;
    border-radius: 5px;
    border: none;
}
QProgressBar::chunk {
    background-color: #FF6B6B;
    border-radius: 5px;
}

/* ─── 리스트 ────────────────────────────────── */
QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #E9ECEF;
    border-radius: 8px;
    color: #212529;
}
QListWidget::item { padding: 6px 10px; border-radius: 6px; }
QListWidget::item:selected { background-color: #EEF2FF; color: #5B6CF6; }
QListWidget::item:hover { background-color: #F8F9FA; }

/* ─── 스크롤 영역 ───────────────────────────── */
QScrollArea { border: none; background: transparent; }
QSplitter::handle { background: #E9ECEF; }
"""

# ── 등급 스타일 ───────────────────────────────────────────────
GRADE_STYLE = {
    "SSS": "color: #B8860B; font-weight: bold; background: #FFF3CD; border-radius: 4px; padding: 1px 6px;",
    "SS":  "color: #5A5A5A; font-weight: bold; background: #E8E8E8; border-radius: 4px; padding: 1px 6px;",
    "S":   "color: #1971C2; font-weight: bold; background: #DBE9FF; border-radius: 4px; padding: 1px 6px;",
    "A":   "color: #2B8A3E; font-weight: bold; background: #D3F9D8; border-radius: 4px; padding: 1px 6px;",
    "B":   "color: #495057; font-weight: bold; background: #F1F3F5; border-radius: 4px; padding: 1px 6px;",
    "C":   "color: #495057;",
    "D":   "color: #E67700;",
    "E":   "color: #FF6B6B;",
    "F":   "color: #C92A2A; font-weight: bold;",
}

# ── 종족 컬러 ────────────────────────────────────────────────
RACE_COLORS = {
    "테란":    "#3B82F6",
    "저그":    "#A855F7",
    "프로토스": "#F59E0B",
}

# ── 종족 표시명 (오리지널 IP — DB 값은 유지, UI 표시만 변경) ──
# PRD v11: 스타크래프트 IP 제거. 전술 삼각 시스템 아키타입과 연동.
#   테란 → 기동대 (Mobility archetype — 유연한 전술 운용)
#   저그 → 공세대 (Aggression archetype — 빠른 압박)
#   프로토스 → 수호대 (Defense archetype — 견고한 방어)
RACE_DISPLAY = {
    "테란":    "기동대",
    "저그":    "공세대",
    "프로토스": "수호대",
}
