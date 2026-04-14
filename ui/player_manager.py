"""선수 관리 화면 — 전체 능력치 조회 + 아이템 현황"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSplitter, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from database.db import get_connection
from ui.widgets import RadarChart, StatBar, make_separator
from ui.styles import GRADE_STYLE, RACE_COLORS
from ui.player_profile_dialog import PlayerProfileDialog

STAT_KEYS   = ["control", "attack", "defense", "supply", "strategy", "sense"]
STAT_LABELS = ["컨트롤", "공격력", "수비력", "물량", "전략", "센스"]


def _load_players() -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM players ORDER BY overall DESC"
        ).fetchall()]


def _load_player_items(player_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT i.* FROM player_items pi
               JOIN items i ON i.id = pi.item_id
               WHERE pi.player_id = ?""",
            (player_id,)
        ).fetchall()
    return [dict(r) for r in rows]


class PlayerManagerScreen(QWidget):
    sig_back = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._players: list[dict] = []
        self._selected_id: int | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # 헤더
        hdr = QHBoxLayout()
        title = QLabel("선수 관리")
        title.setStyleSheet("color: #212529; font-size: 22px; font-weight: bold; background: transparent;")
        self.btn_back = QPushButton("← 돌아가기")
        self.btn_back.clicked.connect(self.sig_back)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.btn_back)

        # 좌우 스플리터
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 왼쪽: 선수 테이블
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ["이름", "종족", "등급", "OVR", "컨트롤", "공격력", "수비력", "물량", "전략", "센스"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.clicked.connect(self._on_row_click)
        self.table.doubleClicked.connect(self._on_row_double_click)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 50)
        self.table.setColumnWidth(3, 55)

        left_lay.addWidget(self.table)
        splitter.addWidget(left)

        # 오른쪽: 상세 패널
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setStyleSheet("QScrollArea { border: none; }")

        self.detail = QWidget()
        detail_lay = QVBoxLayout(self.detail)
        detail_lay.setContentsMargins(12, 0, 0, 0)
        detail_lay.setSpacing(10)

        self.lbl_detail_name = QLabel("선수를 선택하세요")
        self.lbl_detail_name.setStyleSheet(
            "font-size: 18px; font-weight: bold; background: transparent;"
        )
        self.lbl_detail_grade = QLabel("")
        self.lbl_detail_grade.setStyleSheet("font-size: 22px; background: transparent;")
        self.lbl_detail_grade.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.radar = RadarChart([50] * 6)

        stat_area = QFrame()
        stat_area.setStyleSheet("QFrame { background: transparent; border: none; }")
        stat_lay = QVBoxLayout(stat_area)
        stat_lay.setContentsMargins(0, 0, 0, 0)
        stat_lay.setSpacing(4)
        self._stat_bars: dict[str, StatBar] = {}
        for key, label in zip(STAT_KEYS, STAT_LABELS):
            bar = StatBar(label, 0)
            self._stat_bars[key] = bar
            stat_lay.addWidget(bar)

        self.lbl_items_title = QLabel("보유 아이템")
        self.lbl_items_title.setStyleSheet(
            "color: #5B6CF6; font-weight: bold; font-size: 13px; background: transparent;"
        )
        self.lbl_items = QLabel("없음")
        self.lbl_items.setStyleSheet("color: #868E96; font-size: 12px; background: transparent;")
        self.lbl_items.setWordWrap(True)

        self.btn_profile = QPushButton("📋  선수 프로필 보기")
        self.btn_profile.setEnabled(False)
        self.btn_profile.setMinimumHeight(34)
        self.btn_profile.clicked.connect(self._on_show_profile)

        detail_lay.addWidget(self.lbl_detail_name)
        detail_lay.addWidget(self.lbl_detail_grade)
        detail_lay.addWidget(self.radar)
        detail_lay.addWidget(make_separator())
        detail_lay.addWidget(stat_area)
        detail_lay.addWidget(make_separator())
        detail_lay.addWidget(self.lbl_items_title)
        detail_lay.addWidget(self.lbl_items)
        detail_lay.addSpacing(8)
        detail_lay.addWidget(self.btn_profile)
        detail_lay.addStretch()

        right_scroll.setWidget(self.detail)
        splitter.addWidget(right_scroll)
        splitter.setSizes([500, 320])

        root.addLayout(hdr)
        root.addWidget(make_separator())
        root.addWidget(splitter, 1)

    # ──────────────────────────────────────────
    def refresh(self):
        self._players = _load_players()
        self.table.setRowCount(0)
        for p in self._players:
            row = self.table.rowCount()
            self.table.insertRow(row)
            cols = [
                p["name"], p["race"], p["grade"], f"{p['overall']:.1f}",
                p["control"], p["attack"], p["defense"],
                p["supply"], p["strategy"], p["sense"]
            ]
            for col_idx, val in enumerate(cols):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col_idx == 2:   # 등급 색상
                    from core.grade import GRADE_COLORS
                    item.setForeground(QColor(GRADE_COLORS.get(p["grade"], "#ffffff")))
                elif col_idx == 1: # 종족 색상
                    item.setForeground(QColor(RACE_COLORS.get(p["race"], "#ffffff")))
                elif col_idx == 3:   # OVR
                    item.setForeground(QColor("#5B6CF6"))
                self.table.setItem(row, col_idx, item)

        if self._selected_id:
            self._show_detail(self._selected_id)

    def _on_row_click(self, index):
        row = index.row()
        if 0 <= row < len(self._players):
            player = self._players[row]
            self._selected_id = player["id"]
            self._show_detail(player["id"])

    def _on_show_profile(self):
        if self._selected_id is None:
            return
        player = next((p for p in self._players if p["id"] == self._selected_id), None)
        if player:
            dlg = PlayerProfileDialog(player, self)
            dlg.exec()

    def _on_row_double_click(self, index):
        row = index.row()
        if 0 <= row < len(self._players):
            player = self._players[row]
            self._selected_id = player["id"]
            dlg = PlayerProfileDialog(player, self)
            dlg.exec()

    def _show_detail(self, player_id: int):
        player = next((p for p in self._players if p["id"] == player_id), None)
        if not player:
            return

        self.lbl_detail_name.setText(f"{player['name']}  ({player['race']})")
        race_color = RACE_COLORS.get(player["race"], "#fff")
        self.lbl_detail_name.setStyleSheet(
            f"color: {race_color}; font-size: 18px; font-weight: bold; background: transparent;"
        )
        grade = player["grade"]
        self.lbl_detail_grade.setText(f"◆ {grade}  ({player['overall']:.1f})")
        self.lbl_detail_grade.setStyleSheet(
            GRADE_STYLE.get(grade, "") + " font-size: 20px; background: transparent;"
        )

        vals = [player[k] for k in STAT_KEYS]
        self.radar.set_values(vals)
        self.radar._color = QColor(RACE_COLORS.get(player["race"], "#5B6CF6"))
        self.radar.update()

        for key in STAT_KEYS:
            self._stat_bars[key].set_value(player[key])

        items = _load_player_items(player_id)
        if items:
            text = "\n".join(f"• {it['name']}  —  {it['description']}" for it in items)
        else:
            text = "없음"
        self.lbl_items.setText(text)
        self.btn_profile.setEnabled(True)
