"""선수 랭킹 화면"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QTabBar, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from database.db import get_connection
from ui.widgets import make_separator
from ui.styles import RACE_COLORS, GRADE_STYLE

# ── 상수 ──────────────────────────────────────────────────────────
RACES = ["전체", "테란", "저그", "프로토스"]

COLS = ["순위", "선수명", "종족", "등급", "OVR", "경기", "승", "패", "승률", "랭킹점수"]
COL_WIDTHS = [50, 110, 75, 55, 60, 55, 45, 45, 65, 80]

# 순위 색상
RANK_COLORS = {
    1: "#F59E0B",  # 금
    2: "#868E96",  # 은
    3: "#CD7F32",  # 동
}

# 승률 임계값
WIN_RATE_HIGH = 60.0
WIN_RATE_LOW  = 40.0


# ── SQL ───────────────────────────────────────────────────────────
_BASE_SQL = """
SELECT
    p.id,
    p.name,
    p.race,
    p.grade,
    p.overall,
    COUNT(mr.match_id)                                              AS games,
    SUM(CASE WHEN mr.winner_id = p.id THEN 1 ELSE 0 END)          AS wins
FROM players p
LEFT JOIN match_results mr
       ON (mr.player_a_id = p.id OR mr.player_b_id = p.id)
{where}
GROUP BY p.id
ORDER BY (
    p.overall * 10
    + SUM(CASE WHEN mr.winner_id = p.id THEN 1 ELSE 0 END) * 15
    - (COUNT(mr.match_id) - SUM(CASE WHEN mr.winner_id = p.id THEN 1 ELSE 0 END)) * 5
) DESC
"""


def _load_ranking(race: str = "전체") -> list[dict]:
    where = "" if race == "전체" else "WHERE p.race = ?"
    sql = _BASE_SQL.format(where=where)
    params = () if race == "전체" else (race,)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    result = []
    for rank, row in enumerate(rows, start=1):
        games = row["games"] or 0
        wins  = row["wins"]  or 0
        losses = games - wins
        win_rate = (wins / games * 100) if games > 0 else 0.0
        score = int(row["overall"] * 10 + wins * 15 - losses * 5)
        result.append({
            "rank":     rank,
            "name":     row["name"],
            "race":     row["race"],
            "grade":    row["grade"],
            "overall":  row["overall"],
            "games":    games,
            "wins":     wins,
            "losses":   losses,
            "win_rate": win_rate,
            "score":    score,
        })
    return result


# ── 화면 위젯 ─────────────────────────────────────────────────────
class RankingScreen(QWidget):
    sig_back = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_race: str = "전체"
        self._data: list[dict] = []
        self._build_ui()

    # ── UI 구성 ──────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # 헤더 ─────────────────────────────────────────────────
        hdr = QHBoxLayout()

        title = QLabel("선수 랭킹")
        title.setStyleSheet(
            "color: #212529; font-size: 22px; font-weight: bold; background: transparent;"
        )

        self.btn_back = QPushButton("← 돌아가기")
        self.btn_back.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #868E96;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 12px;
            }
            QPushButton:hover { color: #5B6CF6; }
        """)
        self.btn_back.clicked.connect(self.sig_back)

        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.btn_back)

        # 종족 탭 ──────────────────────────────────────────────
        self.tab_bar = QTabBar()
        self.tab_bar.setStyleSheet("""
            QTabBar::tab {
                background: #F8F9FA;
                color: #868E96;
                border: none;
                border-bottom: 2px solid transparent;
                padding: 6px 18px;
                margin-right: 4px;
                font-size: 12px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #F8F9FA;
                color: #5B6CF6;
                border-bottom: 2px solid #5B6CF6;
            }
            QTabBar::tab:hover { color: #5B6CF6; }
        """)
        for race in RACES:
            self.tab_bar.addTab(race)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)

        # 테이블 ───────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setShowGrid(True)

        hh = self.table.horizontalHeader()
        for col, w in enumerate(COL_WIDTHS):
            self.table.setColumnWidth(col, w)
        # 선수명 컬럼은 남은 공간 채우기
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        # 레이아웃 조립 ────────────────────────────────────────
        root.addLayout(hdr)
        root.addWidget(make_separator())
        root.addWidget(self.tab_bar)
        root.addWidget(self.table, 1)

    # ── 슬롯 ─────────────────────────────────────────────────────
    def _on_tab_changed(self, idx: int):
        self._current_race = RACES[idx] if idx < len(RACES) else "전체"
        self._reload_table()

    # ── 데이터 로드 ───────────────────────────────────────────────
    def refresh(self):
        """외부에서 화면 전환 시 호출 — DB 재조회 후 테이블 갱신"""
        self._current_race = RACES[self.tab_bar.currentIndex()]
        self._reload_table()

    def _reload_table(self):
        self._data = _load_ranking(self._current_race)
        self._fill_table()

    # ── 테이블 렌더링 ─────────────────────────────────────────────
    def _fill_table(self):
        data = self._data
        self.table.setRowCount(len(data))

        for row_idx, entry in enumerate(data):
            rank      = entry["rank"]
            rank_color = RANK_COLORS.get(rank)

            # 각 컬럼 데이터
            cells = [
                str(rank),
                entry["name"],
                entry["race"],
                entry["grade"],
                f"{entry['overall']:.1f}",
                str(entry["games"]),
                str(entry["wins"]),
                str(entry["losses"]),
                f"{entry['win_rate']:.1f}%",
                str(entry["score"]),
            ]

            for col_idx, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                    if col_idx != 1
                    else Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )

                # ── 순위 색상 강조 ──
                if rank_color and col_idx == 0:
                    item.setForeground(QColor(rank_color))
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)

                # ── 선수명 ──
                elif col_idx == 1 and rank_color:
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)

                # ── 종족 색상 ──
                elif col_idx == 2:
                    color = RACE_COLORS.get(entry["race"], "#212529")
                    item.setForeground(QColor(color))
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)

                # ── 등급 색상 ──
                elif col_idx == 3:
                    self._apply_grade_cell(item, entry["grade"])

                # ── 승률 색상 ──
                elif col_idx == 8:
                    wr = entry["win_rate"]
                    if wr >= WIN_RATE_HIGH:
                        item.setForeground(QColor("#51CF66"))
                    elif wr < WIN_RATE_LOW:
                        item.setForeground(QColor("#FF6B6B"))
                    else:
                        item.setForeground(QColor("#212529"))

                # ── 랭킹점수 ──
                elif col_idx == 9:
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)

                self.table.setItem(row_idx, col_idx, item)

            # 행 높이
            self.table.setRowHeight(row_idx, 32)

    # ── 등급 셀 스타일 ────────────────────────────────────────────
    @staticmethod
    def _apply_grade_cell(item: QTableWidgetItem, grade: str):
        """GRADE_STYLE 딕셔너리에서 color 를 파싱해 셀 전경색 적용"""
        style = GRADE_STYLE.get(grade, "")
        color = "#212529"
        for part in style.split(";"):
            part = part.strip()
            if part.startswith("color:"):
                color = part.split(":", 1)[1].strip()
                break
        item.setForeground(QColor(color))
        if "font-weight: bold" in style:
            font = QFont()
            font.setBold(True)
            item.setFont(font)
