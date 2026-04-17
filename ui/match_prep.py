"""내 선수 경기 준비 화면 — 맵 선택 + 능력치 비교 + 컨디션/피로도"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFrame, QScrollArea, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal

from database.db import get_connection
from core.balance import (
    roll_condition, apply_condition_item,
    CONDITION_COLOR, get_locked_map_id, is_rival, get_h2h_record
)
from ui.widgets import StatBar, RadarChart, make_separator, make_player_avatar, get_player_image_path
from ui.styles import RACE_COLORS, RACE_DISPLAY, GRADE_STYLE
from core.player_data import get_pre_match_quote, get_style

STAT_KEYS   = ["control", "attack", "defense", "supply", "strategy", "sense"]
STAT_LABELS = ["컨트롤", "공격력", "수비력", "물량", "전략", "센스"]
RACE_BONUS  = {"테란": "terran_bonus", "저그": "zerg_bonus", "프로토스": "protoss_bonus"}


def _load_player(pid: int) -> dict:
    with get_connection() as conn:
        return dict(conn.execute("SELECT * FROM players WHERE id=?", (pid,)).fetchone())


def _load_maps() -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM maps ORDER BY id").fetchall()]


def _load_items(player_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT i.id, i.name, i.description, i.item_type,
                      i.condition_up, i.fatigue_recover
               FROM player_items pi
               JOIN items i ON i.id = pi.item_id
               WHERE pi.player_id=?""",
            (player_id,)
        ).fetchall()
    return [dict(r) for r in rows]


class MatchPrepScreen(QWidget):
    # my_id, opp_id, map_id, tm_id, my_condition
    sig_start = pyqtSignal(int, int, int, int, str)
    sig_back  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._my: dict | None = None
        self._opp: dict | None = None
        self._maps: list[dict] = []
        self._tm_id: int = 0
        self._my_condition: str = "보통"
        self._locked_map_id: int | None = None
        self._build_ui()

    # ──────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        # 헤더
        hdr = QHBoxLayout()
        title = QLabel("경기 준비")
        title.setStyleSheet(
            "color: #212529; font-size: 22px; font-weight: bold; background: transparent;"
        )
        btn_back = QPushButton("← 대진표로")
        btn_back.clicked.connect(self.sig_back)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(btn_back)

        # 라운드
        self.lbl_round = QLabel("")
        self.lbl_round.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_round.setStyleSheet(
            "color: #5B6CF6; font-size: 14px; font-weight: bold; background: transparent;"
        )

        # 라이벌 표시
        self.lbl_rival = QLabel("")
        self.lbl_rival.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_rival.setStyleSheet(
            "color: #FF6B6B; font-size: 13px; font-weight: bold; background: transparent;"
        )

        # 등급 차 경고 (4등급 이상)
        self.lbl_gap_warning = QLabel("")
        self.lbl_gap_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gap_warning.setWordWrap(True)
        self.lbl_gap_warning.setStyleSheet(
            "color: #FF6B6B; font-size: 11px; background: #FFF5F5; "
            "border: 1px solid #FF6B6B; border-radius: 4px; padding: 4px 10px;"
        )
        self.lbl_gap_warning.hide()

        # 경기 전 대사
        self.lbl_quote = QLabel("")
        self.lbl_quote.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_quote.setStyleSheet(
            "color: #212529; font-size: 13px; font-style: italic; background: transparent;"
        )

        # 컨디션 + 피로도 행
        status_row = QHBoxLayout()

        cond_frame = QFrame()
        cond_frame.setStyleSheet(
            "QFrame { background: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 5px; }"
        )
        cond_lay = QHBoxLayout(cond_frame)
        cond_lay.setContentsMargins(10, 6, 10, 6)
        cond_lay.setSpacing(8)
        cond_title = QLabel("컨디션:")
        cond_title.setStyleSheet("color: #868E96; font-size: 12px; background: transparent;")
        self.lbl_condition = QLabel("보통")
        self.lbl_condition.setStyleSheet(
            "color: #212529; font-size: 14px; font-weight: bold; background: transparent;"
        )
        self.btn_use_drink = QPushButton("⚡ 에너지드링크 사용")
        self.btn_use_drink.setFixedHeight(28)
        self.btn_use_drink.setStyleSheet("""
            QPushButton {
                background: #5B6CF6; color: #fff; border-radius: 3px;
                font-size: 11px; padding: 0 8px;
            }
            QPushButton:hover { background: #4A5CE0; }
            QPushButton:disabled { background: #333; color: #666; }
        """)
        self.btn_use_drink.clicked.connect(self._on_use_drink)
        cond_lay.addWidget(cond_title)
        cond_lay.addWidget(self.lbl_condition)
        cond_lay.addSpacing(8)
        cond_lay.addWidget(self.btn_use_drink)

        fat_frame = QFrame()
        fat_frame.setStyleSheet(
            "QFrame { background: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 5px; }"
        )
        fat_lay = QVBoxLayout(fat_frame)
        fat_lay.setContentsMargins(10, 6, 10, 6)
        fat_lay.setSpacing(3)
        fat_title_row = QHBoxLayout()
        fat_title = QLabel("피로도:")
        fat_title.setStyleSheet("color: #868E96; font-size: 12px; background: transparent;")
        self.lbl_fatigue_val = QLabel("0")
        self.lbl_fatigue_val.setStyleSheet(
            "color: #FF6B6B; font-size: 12px; background: transparent;"
        )
        fat_title_row.addWidget(fat_title)
        fat_title_row.addWidget(self.lbl_fatigue_val)
        fat_title_row.addStretch()
        self.bar_fatigue = QProgressBar()
        self.bar_fatigue.setRange(0, 100)
        self.bar_fatigue.setValue(0)
        self.bar_fatigue.setFixedHeight(10)
        self.bar_fatigue.setTextVisible(False)
        self.bar_fatigue.setStyleSheet("""
            QProgressBar { background: #E9ECEF; border-radius: 4px; }
            QProgressBar::chunk { background: #FF6B6B; border-radius: 4px; }
        """)
        fat_lay.addLayout(fat_title_row)
        fat_lay.addWidget(self.bar_fatigue)

        status_row.addWidget(cond_frame, 1)
        status_row.addSpacing(12)
        status_row.addWidget(fat_frame, 1)

        # 맵 선택
        map_row = QHBoxLayout()
        map_row.addWidget(QLabel("맵 선택:"))
        self.cmb_map = QComboBox()
        self.cmb_map.setMinimumWidth(180)
        self.cmb_map.currentIndexChanged.connect(self._on_map_changed)
        map_row.addWidget(self.cmb_map)
        self.lbl_bonus = QLabel("")
        self.lbl_bonus.setStyleSheet("color: #868E96; font-size: 11px; background: transparent;")
        map_row.addSpacing(12)
        map_row.addWidget(self.lbl_bonus)
        self.lbl_locked = QLabel("")
        self.lbl_locked.setStyleSheet(
            "color: #FF6B6B; font-size: 11px; background: transparent;"
        )
        map_row.addSpacing(8)
        map_row.addWidget(self.lbl_locked)
        map_row.addStretch()

        # 선수 비교 패널
        compare = QHBoxLayout()
        self.panel_my  = self._player_panel("MY")
        self.panel_opp = self._player_panel("OPP")
        vs = QLabel("VS")
        vs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs.setStyleSheet(
            "color: #F59E0B; font-size: 30px; font-weight: bold; background: transparent;"
        )
        vs.setFixedWidth(52)
        compare.addWidget(self.panel_my, 1)
        compare.addWidget(vs)
        compare.addWidget(self.panel_opp, 1)

        # 내 아이템
        self.lbl_items = QLabel("")
        self.lbl_items.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_items.setStyleSheet("color: #F59E0B; font-size: 12px; background: transparent;")

        # 시작 버튼
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("⚔  대결 시작!")
        self.btn_start.setProperty("class", "primary")
        self.btn_start.setMinimumHeight(50)
        self.btn_start.setMinimumWidth(200)
        self.btn_start.clicked.connect(self._on_start)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_start)
        btn_row.addStretch()

        root.addLayout(hdr)
        root.addWidget(make_separator())
        root.addWidget(self.lbl_round)
        root.addWidget(self.lbl_rival)
        root.addWidget(self.lbl_gap_warning)
        root.addWidget(self.lbl_quote)
        root.addLayout(status_row)
        root.addLayout(map_row)
        root.addWidget(make_separator())
        root.addLayout(compare, 1)
        root.addWidget(self.lbl_items)
        root.addWidget(make_separator())
        root.addLayout(btn_row)

    def _player_panel(self, slot: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName(f"panel_{slot}")
        frame.setStyleSheet(
            "QFrame { background: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 6px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        tag = "내 선수" if slot == "MY" else "상대 선수"
        tag_lbl = QLabel(f"[{tag}]")
        tag_lbl.setStyleSheet(
            ("color: #5B6CF6;" if slot == "MY" else "color: #868E96;") +
            " font-weight: bold; font-size: 12px; background: transparent;"
        )

        # 이미지 아바타
        avatar_placeholder = QLabel("?")
        avatar_placeholder.setObjectName(f"avatar_{slot}")
        avatar_placeholder.setFixedSize(80, 80)
        avatar_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_placeholder.setStyleSheet(
            "background: #EEF2FF; color: #5B6CF6; font-size: 24px; "
            "font-weight: bold; border-radius: 40px; border: 2px solid #C5D0E8;"
        )
        avatar_row = QHBoxLayout()
        avatar_row.addStretch()
        avatar_row.addWidget(avatar_placeholder)
        avatar_row.addStretch()

        name_lbl = QLabel("—")
        name_lbl.setObjectName(f"name_{slot}")
        name_lbl.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")

        grade_lbl = QLabel("")
        grade_lbl.setObjectName(f"grade_{slot}")
        grade_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        grade_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        race_lbl = QLabel("")
        race_lbl.setObjectName(f"race_{slot}")
        race_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        race_lbl.setStyleSheet("font-size: 12px; background: transparent;")

        radar = RadarChart([50] * 6)
        radar.setObjectName(f"radar_{slot}")

        stat_frame = QFrame()
        stat_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        sf_lay = QVBoxLayout(stat_frame)
        sf_lay.setContentsMargins(0, 0, 0, 0)
        sf_lay.setSpacing(3)
        for key, lbl in zip(STAT_KEYS, STAT_LABELS):
            bar = StatBar(lbl, 0)
            bar.setObjectName(f"bar_{slot}_{key}")
            sf_lay.addWidget(bar)

        bonus_lbl = QLabel("")
        bonus_lbl.setObjectName(f"mapbonus_{slot}")
        bonus_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bonus_lbl.setStyleSheet("font-size: 11px; background: transparent;")

        lay.addWidget(tag_lbl)
        lay.addLayout(avatar_row)
        lay.addWidget(name_lbl)
        lay.addWidget(grade_lbl)
        lay.addWidget(race_lbl)
        lay.addWidget(radar)
        lay.addWidget(make_separator())
        lay.addWidget(stat_frame)
        lay.addWidget(bonus_lbl)
        return frame

    # ──────────────────────────────────────────
    def load_match(self, my_id: int, opp_id: int, tm_id: int, round_name: str):
        self._my   = _load_player(my_id)
        self._opp  = _load_player(opp_id)
        self._tm_id = tm_id
        self._maps  = _load_maps()

        self.lbl_round.setText(f"[ {round_name} ]")

        # 라이벌 여부
        if is_rival(my_id, opp_id):
            # BUG-03 수정: stat_bonus는 PRD v10에서 의도적으로 제거됨(양방향 적용 시 상쇄).
            # extra_luck(변동성 확장)만 실제 적용되므로 UI 문구를 정확히 반영.
            h2h = get_h2h_record(my_id, opp_id)
            if h2h["total"] > 0:
                opp_name = self._opp["name"]
                h2h_text = f"통산 {h2h['a_wins']}승 {h2h['b_wins']}패 vs {opp_name}"
                self.lbl_rival.setText(f"🔥 라이벌 매치!  |  {h2h_text}  |  운 변동성 보너스 적용")
            else:
                self.lbl_rival.setText("🔥 라이벌 매치! 운 변동성 보너스 적용  |  첫 번째 맞대결!")
        else:
            self.lbl_rival.setText("")

        # 선수 대사
        quote = get_pre_match_quote(self._my["name"], self._opp["name"])
        if quote:
            self.lbl_quote.setText(f'"{quote}"')
        else:
            self.lbl_quote.setText("")

        # 컨디션 롤
        self._my_condition = roll_condition(self._my["grade"])
        self._update_condition_display()

        # 피로도 표시
        fat = self._my.get("fatigue", 0)
        self.lbl_fatigue_val.setText(f"{fat}/100")
        self.bar_fatigue.setValue(fat)

        # 에너지드링크 보유 여부 확인
        items = _load_items(my_id)
        has_drink = any(it.get("condition_up", 0) > 0 for it in items)
        self.btn_use_drink.setEnabled(has_drink and self._my_condition != "최상")
        self._drink_item = next(
            (it for it in items if it.get("condition_up", 0) > 0), None
        )

        # 등급 차 경고 (4등급 이상이면 전략/전술 선택이 거의 무의미함을 안내)
        from core.balance import GRADE_ORDER
        try:
            my_idx  = GRADE_ORDER.index(self._my["grade"])
            opp_idx = GRADE_ORDER.index(self._opp["grade"])
            gap = abs(my_idx - opp_idx)
            if gap >= 4:
                direction = "상대가 훨씬 강합니다" if opp_idx < my_idx else "상대가 훨씬 약합니다"
                self.lbl_gap_warning.setText(
                    f"⚠  등급 차 {gap}단계 — {direction}. "
                    f"이변 확률이 매우 낮아 전략·전술 선택이 결과에 거의 영향을 주지 않습니다."
                )
                self.lbl_gap_warning.show()
            else:
                self.lbl_gap_warning.hide()
        except ValueError:
            self.lbl_gap_warning.hide()

        # 맵 선택 (Super/SS 핸디캡: 최악 맵 강제 지정 → 진짜 불리한 환경)
        # BUG-10 수정: 내 선수뿐 아니라 AI 상대도 Super/SS면 핸디캡 적용.
        #   내 선수 잠금 우선 → 없으면 상대 잠금 적용.
        my_locked  = get_locked_map_id(self._my,  self._maps)
        opp_locked = get_locked_map_id(self._opp, self._maps)
        self._locked_map_id = my_locked if my_locked is not None else opp_locked

        # 잠금 라벨 결정
        if my_locked is not None:
            lock_label_text = "⚠ 핸디캡: 내 선수 최악 맵 강제 적용 (난이도 ↑)"
        elif opp_locked is not None:
            lock_label_text = "⚠ 핸디캡: 상대 선수 최악 맵 강제 적용"
        else:
            lock_label_text = ""

        self.cmb_map.blockSignals(True)
        self.cmb_map.clear()
        for m in self._maps:
            label = m["name"]
            if self._locked_map_id is not None and m["id"] == self._locked_map_id:
                label += "  🔒"
            self.cmb_map.addItem(label)
        self.cmb_map.blockSignals(False)

        if self._locked_map_id is not None:
            locked_idx = next(
                (i for i, m in enumerate(self._maps) if m["id"] == self._locked_map_id), 0
            )
            self.cmb_map.setCurrentIndex(locked_idx)
            # 다른 맵 비활성화
            for i in range(self.cmb_map.count()):
                if i != locked_idx:
                    self.cmb_map.model().item(i).setEnabled(False)
            self.lbl_locked.setText(lock_label_text)
        else:
            self.lbl_locked.setText("")
            for i in range(self.cmb_map.count()):
                self.cmb_map.model().item(i).setEnabled(True)
            self.cmb_map.setCurrentIndex(0)

        self._fill_panel("MY",  self._my)
        self._fill_panel("OPP", self._opp)
        self._on_map_changed(self.cmb_map.currentIndex())

        # 아이템 표시
        if items:
            parts = []
            for it in items:
                tag = ""
                if it.get("condition_up", 0):
                    tag = " [컨디션]"
                elif it.get("fatigue_recover", 0):
                    tag = " [피로회복]"
                parts.append(it["name"] + tag)
            self.lbl_items.setText("장착 아이템: " + "  |  ".join(parts))
        else:
            self.lbl_items.setText("장착 아이템 없음 (상점에서 구매 가능)")

    def _update_condition_display(self):
        color = CONDITION_COLOR.get(self._my_condition, "#212529")
        self.lbl_condition.setText(self._my_condition)
        self.lbl_condition.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: bold; background: transparent;"
        )

    def _on_use_drink(self):
        """에너지드링크 사용 — 컨디션 1단계 상승, 아이템 제거"""
        if self._drink_item is None or self._my is None:
            return
        self._my_condition = apply_condition_item(self._my_condition)
        self._update_condition_display()

        # 아이템 소진 (player_items에서 1개 삭제)
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM player_items WHERE player_id=? AND item_id=? LIMIT 1",
                (self._my["id"], self._drink_item["id"])
            ).fetchone()
            if row:
                conn.execute("DELETE FROM player_items WHERE id=?", (row["id"],))
                conn.commit()

        self.btn_use_drink.setEnabled(
            self._my_condition != "최상"
        )

    def _fill_panel(self, slot: str, player: dict):
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt as _Qt
        frame = self.panel_my if slot == "MY" else self.panel_opp

        # 이미지 업데이트
        avatar_lbl = frame.findChild(QLabel, f"avatar_{slot}")
        if avatar_lbl:
            img_path = get_player_image_path(player["name"])
            if img_path:
                px = QPixmap(img_path).scaled(
                    80, 80,
                    _Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    _Qt.TransformationMode.SmoothTransformation,
                )
                avatar_lbl.setPixmap(px)
                avatar_lbl.setStyleSheet(
                    "border-radius: 40px; background: #FFFFFF; border: 2px solid #E9ECEF;"
                )
            else:
                avatar_lbl.setText(player["name"][0])
                avatar_lbl.setStyleSheet(
                    "background: #EEF2FF; color: #5B6CF6; font-size: 24px; "
                    "font-weight: bold; border-radius: 40px; border: 2px solid #C5D0E8;"
                )

        frame.findChild(QLabel, f"name_{slot}").setText(player["name"])

        grade = player["grade"]
        gl = frame.findChild(QLabel, f"grade_{slot}")
        gl.setText(f"◆ {grade}")
        gl.setStyleSheet(GRADE_STYLE.get(grade, "") + " font-size: 20px; background: transparent;")

        race = player["race"]
        rl = frame.findChild(QLabel, f"race_{slot}")
        rl.setText(RACE_DISPLAY.get(race, race))   # 오리지널 표시명 사용
        rl.setStyleSheet(
            f"color: {RACE_COLORS.get(race, '#fff')}; font-size: 12px; background: transparent;"
        )

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
            f"기동대 {mp['terran_bonus']:+d}  |  "
            f"공세대 {mp['zerg_bonus']:+d}  |  "
            f"수호대 {mp['protoss_bonus']:+d}"
        )
        self.lbl_bonus.setText(f"보정:  {bonuses}")

        for slot, player in [("MY", self._my), ("OPP", self._opp)]:
            if player is None:
                continue
            frame = self.panel_my if slot == "MY" else self.panel_opp
            col = RACE_BONUS.get(player["race"], "terran_bonus")
            bv  = mp[col]
            lbl = frame.findChild(QLabel, f"mapbonus_{slot}")
            if bv > 0:
                lbl.setText(f"맵 보정: +{bv}")
                lbl.setStyleSheet("color: #51CF66; font-size: 11px; background: transparent;")
            elif bv < 0:
                lbl.setText(f"맵 보정: {bv}")
                lbl.setStyleSheet("color: #FF6B6B; font-size: 11px; background: transparent;")
            else:
                lbl.setText("맵 보정: ±0")
                lbl.setStyleSheet("color: #868E96; font-size: 11px; background: transparent;")

    def _on_start(self):
        if self._my and self._opp:
            idx = self.cmb_map.currentIndex()
            if 0 <= idx < len(self._maps):
                self.sig_start.emit(
                    self._my["id"],
                    self._opp["id"],
                    self._maps[idx]["id"],
                    self._tm_id,
                    self._my_condition,
                )
