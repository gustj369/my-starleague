"""대결 설정 화면 — 맵 선택 + 선수 능력치 비교"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from database.db import get_connection
from ui.widgets import StatBar, RadarChart, make_separator
from ui.styles import RACE_COLORS, RACE_DISPLAY, GRADE_STYLE
from core.grade import GRADE_COLORS


def _load_player(player_id: int) -> dict:
    with get_connection() as conn:
        return dict(conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone())


def _load_maps() -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM maps ORDER BY id").fetchall()]


STAT_KEYS   = ["control", "attack", "defense", "supply", "strategy", "sense"]
STAT_LABELS = ["컨트롤", "공격력", "수비력", "물량", "전략", "센스"]
RACE_BONUS_COL = {"테란": "terran_bonus", "저그": "zerg_bonus", "프로토스": "protoss_bonus"}


class MatchScreen(QWidget):
    sig_start  = pyqtSignal(int, int, int)   # a_id, b_id, map_id
    sig_back   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player_a: dict | None = None
        self._player_b: dict | None = None
        self._maps: list[dict] = []
        self._build_ui()

    # ──────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # 헤더
        hdr = QHBoxLayout()
        title = QLabel("대결 설정")
        title.setStyleSheet("color: #212529; font-size: 22px; font-weight: bold; background: transparent;")
        self.btn_back = QPushButton("← 선수 선택")
        self.btn_back.clicked.connect(self.sig_back)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.btn_back)

        # 맵 선택
        map_row = QHBoxLayout()
        map_row.addWidget(QLabel("맵 선택:"))
        self.cmb_map = QComboBox()
        self.cmb_map.setMinimumWidth(200)
        self.cmb_map.currentIndexChanged.connect(self._on_map_changed)
        map_row.addWidget(self.cmb_map)

        self.lbl_map_bonus = QLabel("")
        self.lbl_map_bonus.setStyleSheet("color: #868E96; font-size: 11px; background: transparent;")
        map_row.addSpacing(20)
        map_row.addWidget(self.lbl_map_bonus)
        map_row.addStretch()

        # 선수 비교
        compare = QHBoxLayout()
        self.frame_a = self._player_panel("A")
        self.frame_b = self._player_panel("B")
        vs = QLabel("VS")
        vs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs.setStyleSheet("color: #5B6CF6; font-size: 28px; font-weight: bold; background: transparent;")
        vs.setFixedWidth(50)

        compare.addWidget(self.frame_a, 1)
        compare.addWidget(vs)
        compare.addWidget(self.frame_b, 1)

        # 시작 버튼
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("⚔  대결 시작!")
        self.btn_start.setProperty("class", "primary")
        self.btn_start.setMinimumHeight(52)
        self.btn_start.setMinimumWidth(200)
        self.btn_start.clicked.connect(self._on_start)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_start)
        btn_row.addStretch()

        root.addLayout(hdr)
        root.addWidget(make_separator())
        root.addLayout(map_row)
        root.addWidget(make_separator())
        root.addLayout(compare, 1)
        root.addWidget(make_separator())
        root.addLayout(btn_row)

    def _player_panel(self, slot: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 8px; }")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(8)

        slot_lbl = QLabel(f"[선수 {slot}]")
        slot_lbl.setStyleSheet("color: #5B6CF6; font-weight: bold; font-size: 13px; background: transparent;")

        name_lbl = QLabel("—")
        name_lbl.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        name_lbl.setObjectName(f"name_{slot}")

        grade_lbl = QLabel("")
        grade_lbl.setStyleSheet("font-size: 22px; background: transparent;")
        grade_lbl.setObjectName(f"grade_{slot}")
        grade_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        race_lbl = QLabel("")
        race_lbl.setStyleSheet("font-size: 12px; background: transparent;")
        race_lbl.setObjectName(f"race_{slot}")
        race_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        radar = RadarChart([50]*6)
        radar.setObjectName(f"radar_{slot}")

        # 능력치 바
        stat_frame = QFrame()
        stat_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        stat_lay = QVBoxLayout(stat_frame)
        stat_lay.setContentsMargins(0, 0, 0, 0)
        stat_lay.setSpacing(3)
        for key, label in zip(STAT_KEYS, STAT_LABELS):
            bar = StatBar(label, 0)
            bar.setObjectName(f"bar_{slot}_{key}")
            stat_lay.addWidget(bar)

        bonus_lbl = QLabel("")
        bonus_lbl.setObjectName(f"bonus_{slot}")
        bonus_lbl.setStyleSheet("color: #5B6CF6; font-size: 11px; background: transparent;")
        bonus_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay.addWidget(slot_lbl)
        lay.addWidget(name_lbl)
        lay.addWidget(grade_lbl)
        lay.addWidget(race_lbl)
        lay.addWidget(radar)
        lay.addWidget(make_separator())
        lay.addWidget(stat_frame)
        lay.addWidget(bonus_lbl)

        return frame

    # ──────────────────────────────────────────
    def load_players(self, player_a_id: int, player_b_id: int):
        self._player_a = _load_player(player_a_id)
        self._player_b = _load_player(player_b_id)
        self._maps = _load_maps()

        self.cmb_map.clear()
        for m in self._maps:
            self.cmb_map.addItem(m["name"])

        self._update_panels()
        self._on_map_changed(0)

    def _update_panels(self):
        for slot, player in [("A", self._player_a), ("B", self._player_b)]:
            if player is None:
                continue
            frame = self.frame_a if slot == "A" else self.frame_b

            frame.findChild(QLabel, f"name_{slot}").setText(player["name"])

            grade = player["grade"]
            gl = frame.findChild(QLabel, f"grade_{slot}")
            gl.setText(f"◆ {grade}")
            gl.setStyleSheet(GRADE_STYLE.get(grade, "") + " font-size: 22px; background: transparent;")

            race = player["race"]
            rl = frame.findChild(QLabel, f"race_{slot}")
            rl.setText(RACE_DISPLAY.get(race, race))   # 오리지널 표시명
            rl.setStyleSheet(f"color: {RACE_COLORS.get(race, '#fff')}; font-size: 12px; background: transparent;")

            vals = [player[k] for k in STAT_KEYS]
            frame.findChild(RadarChart, f"radar_{slot}").set_values(vals)

            for key in STAT_KEYS:
                bar = frame.findChild(StatBar, f"bar_{slot}_{key}")
                if bar:
                    bar.set_value(player[key])

    def _on_map_changed(self, idx: int):
        if not self._maps or idx < 0 or idx >= len(self._maps):
            return
        mp = self._maps[idx]
        bonuses = (
            f"{RACE_DISPLAY['테란']} {mp['terran_bonus']:+d}  |  "
            f"{RACE_DISPLAY['저그']} {mp['zerg_bonus']:+d}  |  "
            f"{RACE_DISPLAY['프로토스']} {mp['protoss_bonus']:+d}"
        )
        self.lbl_map_bonus.setText(f"종족 보정:  {bonuses}")

        # 각 선수 패널에 맵 보정 표시
        for slot, player in [("A", self._player_a), ("B", self._player_b)]:
            if player is None:
                continue
            frame = self.frame_a if slot == "A" else self.frame_b
            col = RACE_BONUS_COL.get(player["race"], "terran_bonus")
            bonus_val = mp[col]
            lbl = frame.findChild(QLabel, f"bonus_{slot}")
            if bonus_val > 0:
                lbl.setText(f"맵 보정: +{bonus_val}")
                lbl.setStyleSheet("color: #51CF66; font-size: 11px; background: transparent;")
            elif bonus_val < 0:
                lbl.setText(f"맵 보정: {bonus_val}")
                lbl.setStyleSheet("color: #FF6B6B; font-size: 11px; background: transparent;")
            else:
                lbl.setText("맵 보정: ±0")
                lbl.setStyleSheet("color: #868E96; font-size: 11px; background: transparent;")

    def _on_start(self):
        idx = self.cmb_map.currentIndex()
        if self._player_a and self._player_b and 0 <= idx < len(self._maps):
            self.sig_start.emit(
                self._player_a["id"],
                self._player_b["id"],
                self._maps[idx]["id"]
            )
