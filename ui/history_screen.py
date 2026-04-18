"""대결 기록 화면"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSplitter, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from database.db import get_connection
from ui.widgets import make_separator
from ui.styles import RACE_COLORS, RACE_DISPLAY

STAT_KEYS   = ["control", "attack", "defense", "supply", "strategy", "sense"]
STAT_LABELS = ["컨트롤", "공격력", "수비력", "물량", "전략", "센스"]


def _load_history() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT mr.*,
                   pa.name  AS a_name,  pa.race AS a_race,
                   pb.name  AS b_name,  pb.race AS b_race,
                   pw.name  AS w_name,
                   m.name   AS map_name
            FROM match_results mr
            JOIN players pa ON pa.id = mr.player_a_id
            JOIN players pb ON pb.id = mr.player_b_id
            JOIN players pw ON pw.id = mr.winner_id
            JOIN maps    m  ON m.id  = mr.map_id
            ORDER BY mr.match_id DESC
        """).fetchall()
    return [dict(r) for r in rows]


def _load_player_records() -> list[dict]:
    """선수별 승/패 집계"""
    with get_connection() as conn:
        players = [dict(r) for r in conn.execute(
            "SELECT id, name, race, grade, overall FROM players ORDER BY overall DESC"
        ).fetchall()]
        for p in players:
            wins = conn.execute(
                "SELECT COUNT(*) FROM match_results WHERE winner_id=?", (p["id"],)
            ).fetchone()[0]
            total = conn.execute(
                "SELECT COUNT(*) FROM match_results WHERE player_a_id=? OR player_b_id=?",
                (p["id"], p["id"])
            ).fetchone()[0]
            p["wins"]   = wins
            p["losses"] = total - wins
            p["total"]  = total
    return players


class HistoryScreen(QWidget):
    sig_back = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # 헤더
        hdr = QHBoxLayout()
        title = QLabel("대결 기록")
        title.setStyleSheet("color: #212529; font-size: 22px; font-weight: bold; background: transparent;")
        self.btn_back = QPushButton("← 돌아가기")
        self.btn_back.clicked.connect(self.sig_back)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.btn_back)

        # 탭 구조 직접 구현 (두 섹션)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 상단: 전체 대결 히스토리
        hist_widget = QWidget()
        hist_lay = QVBoxLayout(hist_widget)
        hist_lay.setContentsMargins(0, 0, 0, 0)
        hist_lay.setSpacing(6)

        hist_title = QLabel("전체 매치 히스토리")
        hist_title.setStyleSheet("color: #5B6CF6; font-weight: bold; font-size: 14px; background: transparent;")

        self.hist_table = QTableWidget()
        self.hist_table.setColumnCount(7)
        self.hist_table.setHorizontalHeaderLabels(
            ["#", "맵", "선수 A", "선수 B", "승자", "이변", "시각"]
        )
        self.hist_table.horizontalHeader().setStretchLastSection(True)
        self.hist_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.hist_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.hist_table.verticalHeader().setVisible(False)
        self.hist_table.setAlternatingRowColors(True)
        self.hist_table.setColumnWidth(0, 40)
        self.hist_table.setColumnWidth(1, 130)
        self.hist_table.setColumnWidth(2, 100)
        self.hist_table.setColumnWidth(3, 100)
        self.hist_table.setColumnWidth(4, 100)
        self.hist_table.setColumnWidth(5, 130)

        # 클릭 시 스탯 변화 상세 패널
        self.detail_frame = QFrame()
        self.detail_frame.setStyleSheet(
            "QFrame { background: #F8F9FA; border: 1px solid #E9ECEF; border-radius: 6px; }"
        )
        detail_lay = QHBoxLayout(self.detail_frame)
        detail_lay.setContentsMargins(12, 8, 12, 8)
        detail_lay.setSpacing(20)
        self.lbl_detail_a = QLabel("행을 클릭하면 스탯 변화를 확인할 수 있습니다.")
        self.lbl_detail_a.setStyleSheet("color: #868E96; font-size: 11px; background: transparent;")
        self.lbl_detail_a.setWordWrap(True)
        self.lbl_detail_b = QLabel("")
        self.lbl_detail_b.setStyleSheet("color: #868E96; font-size: 11px; background: transparent;")
        self.lbl_detail_b.setWordWrap(True)
        detail_lay.addWidget(self.lbl_detail_a, 1)
        detail_lay.addWidget(self.lbl_detail_b, 1)

        # currentCellChanged: (currentRow, currentColumn, previousRow, previousColumn)
        self.hist_table.currentCellChanged.connect(
            lambda curr_row, _cc, _pr, _pc: self._on_history_row_changed(curr_row)
        )

        hist_lay.addWidget(hist_title)
        hist_lay.addWidget(self.hist_table)
        hist_lay.addWidget(self.detail_frame)
        splitter.addWidget(hist_widget)

        # 하단: 선수별 전적
        record_widget = QWidget()
        record_lay = QVBoxLayout(record_widget)
        record_lay.setContentsMargins(0, 0, 0, 0)
        record_lay.setSpacing(6)

        rec_title = QLabel("선수별 전적")
        rec_title.setStyleSheet("color: #5B6CF6; font-weight: bold; font-size: 14px; background: transparent;")

        self.rec_table = QTableWidget()
        self.rec_table.setColumnCount(7)
        self.rec_table.setHorizontalHeaderLabels(
            ["선수", "종족", "등급", "OVR", "승", "패", "승률"]
        )
        self.rec_table.horizontalHeader().setStretchLastSection(True)
        self.rec_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.rec_table.verticalHeader().setVisible(False)
        self.rec_table.setAlternatingRowColors(True)
        self.rec_table.setColumnWidth(0, 80)
        self.rec_table.setColumnWidth(1, 80)
        self.rec_table.setColumnWidth(2, 55)
        self.rec_table.setColumnWidth(3, 65)

        record_lay.addWidget(rec_title)
        record_lay.addWidget(self.rec_table)
        splitter.addWidget(record_widget)
        splitter.setSizes([300, 220])

        root.addLayout(hdr)
        root.addWidget(make_separator())
        root.addWidget(splitter, 1)

    # ──────────────────────────────────────────
    def refresh(self):
        self._history = _load_history()
        self._fill_history()
        self._fill_records()

    def _fill_history(self):
        self.hist_table.setRowCount(0)
        for r in self._history:
            row = self.hist_table.rowCount()
            self.hist_table.insertRow(row)
            upset_val = "⚡ 이변!" if r.get("is_upset") else "—"
            cols = [
                str(r["match_id"]),
                r["map_name"],
                f"{r['a_name']} ({RACE_DISPLAY.get(r['a_race'], r['a_race'])})",
                f"{r['b_name']} ({RACE_DISPLAY.get(r['b_race'], r['b_race'])})",
                r["w_name"],
                upset_val,
                r["timestamp"][:16],
            ]
            for ci, val in enumerate(cols):
                ti = QTableWidgetItem(val)
                ti.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if ci == 4:
                    ti.setForeground(QColor("#5B6CF6"))
                elif ci == 5 and r.get("is_upset"):
                    ti.setForeground(QColor("#FF6B6B"))
                self.hist_table.setItem(row, ci, ti)

    def _on_history_row_changed(self, row: int):
        """히스토리 행 선택 시 스탯 변화 상세 표시"""
        if row < 0 or row >= len(self._history):
            self.lbl_detail_a.setText("행을 클릭하면 스탯 변화를 확인할 수 있습니다.")
            self.lbl_detail_b.setText("")
            return
        r = self._history[row]

        def _delta_text(name: str, deltas: list[tuple[str, int]]) -> str:
            ups   = [f"{lbl} +{v}" for lbl, v in deltas if v > 0]
            downs = [f"{lbl} {v}" for lbl, v in deltas if v < 0]
            parts = []
            if ups:
                parts.append("↑ " + " · ".join(ups))
            if downs:
                parts.append("↓ " + " · ".join(downs))
            change = "  |  ".join(parts) if parts else "변화 없음"
            return f"[{name}]  {change}"

        prefix_map = {"a": "a", "b": "b"}
        result = {}
        for side, name_key in [("a", "a_name"), ("b", "b_name")]:
            deltas = [
                (lbl, r.get(f"{side}_{key}_delta", 0))
                for key, lbl in zip(STAT_KEYS, STAT_LABELS)
            ]
            result[side] = _delta_text(r[name_key], deltas)

        winner_mark = "🏆 " if r["w_name"] == r["a_name"] else ""
        loser_mark  = "🏆 " if r["w_name"] == r["b_name"] else ""
        map_info = f"맵: {r['map_name']}  |  "
        upset_info = "  ⚡ 이변!" if r.get("is_upset") else ""

        self.lbl_detail_a.setText(
            f"{map_info}{winner_mark}{result['a']}{upset_info}"
        )
        self.lbl_detail_b.setText(f"{loser_mark}{result['b']}")
        self.lbl_detail_a.setStyleSheet(
            "color: #212529; font-size: 11px; background: transparent;"
        )
        self.lbl_detail_b.setStyleSheet(
            "color: #212529; font-size: 11px; background: transparent;"
        )

    def _fill_records(self):
        records = _load_player_records()
        self.rec_table.setRowCount(0)
        for p in records:
            row = self.rec_table.rowCount()
            self.rec_table.insertRow(row)
            rate = f"{p['wins'] / p['total'] * 100:.0f}%" if p["total"] > 0 else "—"
            cols = [
                p["name"], RACE_DISPLAY.get(p["race"], p["race"]), p["grade"],
                f"{p['overall']:.1f}",
                str(p["wins"]), str(p["losses"]), rate
            ]
            for ci, val in enumerate(cols):
                ti = QTableWidgetItem(val)
                ti.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if ci == 2:
                    from core.grade import GRADE_COLORS
                    ti.setForeground(QColor(GRADE_COLORS.get(p["grade"], "#fff")))
                elif ci == 1:
                    ti.setForeground(QColor(RACE_COLORS.get(p["race"], "#fff")))
                elif ci == 4:
                    ti.setForeground(QColor("#51CF66"))
                elif ci == 5:
                    ti.setForeground(QColor("#FF6B6B"))
                self.rec_table.setItem(row, ci, ti)
