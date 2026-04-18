"""대결 결과 화면"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from database.db import get_connection, get_gold
from core.match import MatchOutcome
from core.balance import CONDITION_COLOR
from ui.widgets import StatBar, make_separator
from ui.styles import RACE_COLORS, GRADE_STYLE
from core.player_data import get_win_quote, get_loss_quote

STAT_KEYS   = ["control", "attack", "defense", "supply", "strategy", "sense"]
STAT_LABELS = ["컨트롤", "공격력", "수비력", "물량", "전략", "센스"]


def _load_player(player_id: int) -> dict:
    with get_connection() as conn:
        return dict(conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone())


class ResultScreen(QWidget):
    sig_continue = pyqtSignal()   # 팀 편성으로 돌아가기

    def __init__(self, parent=None):
        super().__init__(parent)
        self._outcome: MatchOutcome | None = None
        self._build_ui()

    # ──────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.setSpacing(16)

        # 승패 발표 배너
        self.lbl_result = QLabel("결과 발표")
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_result.setStyleSheet(
            "color: #F59E0B; font-size: 30px; font-weight: bold; background: transparent;"
        )

        # 승자 이름
        self.lbl_winner = QLabel("")
        self.lbl_winner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_winner.setStyleSheet(
            "color: #212529; font-size: 22px; font-weight: bold; background: transparent;"
        )

        # 전투력 표시
        self.lbl_power = QLabel("")
        self.lbl_power.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_power.setStyleSheet("color: #868E96; font-size: 12px; background: transparent;")

        # 두 선수 능력치 변동 패널
        panels_row = QHBoxLayout()
        self.panel_a = self._delta_panel("A")
        self.panel_b = self._delta_panel("B")
        panels_row.addWidget(self.panel_a, 1)
        panels_row.addSpacing(20)
        panels_row.addWidget(self.panel_b, 1)

        # 이변 발생 배너 (기본 hidden)
        self.lbl_upset = QLabel("⚡  이변 발생!")
        self.lbl_upset.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_upset.setStyleSheet(
            "color: #F59E0B; font-size: 22px; font-weight: bold; background: transparent;"
        )
        self.lbl_upset.setVisible(False)

        # 컨디션 / 피로도 정보
        self.lbl_cond_info = QLabel("")
        self.lbl_cond_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cond_info.setStyleSheet("color: #868E96; font-size: 12px; background: transparent;")

        # 골드
        self.lbl_gold = QLabel("")
        self.lbl_gold.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gold.setProperty("class", "gold")
        self.lbl_gold.setStyleSheet("color: #F59E0B; font-size: 14px; font-weight: bold; background: transparent;")

        # 계속 버튼
        btn_row = QHBoxLayout()
        self.btn_continue = QPushButton("▶  계속하기")
        self.btn_continue.setProperty("class", "primary")
        self.btn_continue.setMinimumHeight(48)
        self.btn_continue.clicked.connect(self.sig_continue)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_continue)
        btn_row.addStretch()

        root.addWidget(self.lbl_result)
        root.addWidget(self.lbl_winner)
        root.addWidget(self.lbl_upset)
        root.addWidget(self.lbl_power)
        root.addWidget(self.lbl_cond_info)
        root.addWidget(make_separator())
        root.addLayout(panels_row, 1)
        root.addWidget(make_separator())
        root.addWidget(self.lbl_gold)
        root.addLayout(btn_row)

    def _delta_panel(self, slot: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName(f"panel_{slot}")
        frame.setStyleSheet("QFrame { background: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 8px; }")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(6)

        slot_lbl = QLabel(f"[선수 {slot}]")
        slot_lbl.setStyleSheet("color: #5B6CF6; font-weight: bold; background: transparent;")

        name_lbl = QLabel("—")
        name_lbl.setObjectName(f"name_{slot}")
        name_lbl.setStyleSheet("font-size: 16px; font-weight: bold; background: transparent;")

        grade_row = QHBoxLayout()
        old_grade = QLabel("")
        old_grade.setObjectName(f"old_grade_{slot}")
        old_grade.setStyleSheet("font-size: 16px; background: transparent;")
        arr = QLabel(" → ")
        arr.setStyleSheet("color: #868E96; background: transparent;")
        new_grade = QLabel("")
        new_grade.setObjectName(f"new_grade_{slot}")
        new_grade.setStyleSheet("font-size: 16px; background: transparent;")
        grade_row.addWidget(old_grade)
        grade_row.addWidget(arr)
        grade_row.addWidget(new_grade)
        grade_row.addStretch()

        result_lbl = QLabel("")
        result_lbl.setObjectName(f"result_{slot}")
        result_lbl.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        growth_lbl = QLabel("")
        growth_lbl.setObjectName(f"growth_{slot}")
        growth_lbl.setWordWrap(True)
        growth_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        growth_lbl.setStyleSheet(
            "font-size: 11px; background: #F0FDF4; border: 1px solid #BBF7D0; "
            "border-radius: 4px; padding: 3px 8px; color: #15803D;"
        )
        growth_lbl.hide()

        lay.addWidget(slot_lbl)
        lay.addWidget(name_lbl)
        lay.addWidget(result_lbl)
        lay.addLayout(grade_row)
        lay.addWidget(growth_lbl)
        lay.addWidget(make_separator())

        for key, label in zip(STAT_KEYS, STAT_LABELS):
            bar = StatBar(label, 0)
            bar.setObjectName(f"bar_{slot}_{key}")
            lay.addWidget(bar)

        quote_lbl = QLabel("")
        quote_lbl.setObjectName(f"quote_{slot}")
        quote_lbl.setWordWrap(True)
        quote_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        quote_lbl.setStyleSheet(
            "color: #868E96; font-size: 12px; font-style: italic; background: transparent;"
        )
        lay.addWidget(quote_lbl)

        return frame

    # ──────────────────────────────────────────
    def set_button_label(self, text: str):
        self.btn_continue.setText(text)

    def show_result(self, outcome: MatchOutcome, old_a: dict, old_b: dict):
        """대결 결과 표시. old_a/old_b는 대결 전 능력치 스냅샷"""
        self._outcome = outcome

        new_a = _load_player(old_a["id"])
        new_b = _load_player(old_b["id"])

        winner = new_a if outcome.winner_id == new_a["id"] else new_b
        loser  = new_b if outcome.winner_id == new_a["id"] else new_a

        self.lbl_result.setText("🏆  승자 결정!")
        score_txt = ""
        if hasattr(outcome, 'a_wins') and (outcome.a_wins + outcome.b_wins) > 1:
            score_txt = f"  ({outcome.a_wins} - {outcome.b_wins})"
        self.lbl_winner.setText(f"{winner['name']}  승리!{score_txt}")
        race_color = RACE_COLORS.get(winner["race"], "#ffffff")
        self.lbl_winner.setStyleSheet(
            f"color: {race_color}; font-size: 24px; font-weight: bold; background: transparent;"
        )
        self.lbl_power.setText(
            f"전투력  {winner['name']}: {outcome.a_power:.1f}  vs  "
            f"{loser['name']}: {outcome.b_power:.1f}"
        )

        self._fill_panel("A", old_a, new_a, outcome.player_a_delta, outcome.winner_id == old_a["id"])
        self._fill_panel("B", old_b, new_b, outcome.player_b_delta, outcome.winner_id == old_b["id"])

        # 이변 배너
        if outcome.is_upset:
            self.lbl_upset.setVisible(True)
            upset_parts = [f"⚡  이변 발생!  +{outcome.upset_gold}G 보너스"]
            if outcome.is_rival_match:
                upset_parts.append("🔥 라이벌전 포함")
            self.lbl_upset.setText("  ".join(upset_parts))
        else:
            self.lbl_upset.setVisible(False)

        # 라이벌전 표시 (이변 아닐 때도)
        if outcome.is_rival_match and not outcome.is_upset:
            self.lbl_upset.setText("🔥 라이벌 매치!")
            self.lbl_upset.setStyleSheet(
                "color: #F59E0B; font-size: 16px; font-weight: bold; background: transparent;"
            )
            self.lbl_upset.setVisible(True)

        # 컨디션 / 피로도 정보
        cond_a_color = CONDITION_COLOR.get(outcome.a_condition, "#212529")
        cond_b_color = CONDITION_COLOR.get(outcome.b_condition, "#212529")
        self.lbl_cond_info.setText(
            f"{new_a['name']} 컨디션: "
            f"<span style='color:{cond_a_color}'>{outcome.a_condition}</span>  "
            f"피로도: {outcome.a_fatigue}   |   "
            f"{new_b['name']} 컨디션: "
            f"<span style='color:{cond_b_color}'>{outcome.b_condition}</span>  "
            f"피로도: {outcome.b_fatigue}"
        )
        self.lbl_cond_info.setTextFormat(Qt.TextFormat.RichText)

        gold_text = f"보유 골드: {get_gold()} G  (대결 +50G, 승자 +30G"
        if outcome.upset_gold:
            gold_text += f", 이변 +{outcome.upset_gold}G"
        gold_text += ")"
        self.lbl_gold.setText(gold_text)

        # 글로우 애니메이션 (타이머)
        self._flash = 0
        self._flash_dir = 1
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._flash_winner)
        self._timer.start(80)
        duration = 4000 if outcome.is_upset else 3000
        QTimer.singleShot(duration, self._timer.stop)

        # 이변 발생 시 upset 레이블도 깜빡임
        if outcome.is_upset:
            self._upset_flash = 0
            self._upset_fd = 1
            self._upset_timer = QTimer(self)
            self._upset_timer.timeout.connect(self._flash_upset)
            self._upset_timer.start(100)
            QTimer.singleShot(4000, self._upset_timer.stop)

    def _fill_panel(self, slot: str, old: dict, new: dict,
                    delta: dict, is_winner: bool):
        frame = self.panel_a if slot == "A" else self.panel_b

        frame.findChild(QLabel, f"name_{slot}").setText(new["name"])

        win_text = "🏆  승리" if is_winner else "💀  패배"
        win_style = (
            "color: #F59E0B; font-size: 18px; font-weight: bold; background: transparent;"
            if is_winner else
            "color: #FF6B6B; font-size: 18px; font-weight: bold; background: transparent;"
        )
        frame.findChild(QLabel, f"result_{slot}").setText(win_text)
        frame.findChild(QLabel, f"result_{slot}").setStyleSheet(win_style)

        og = old["grade"]
        ng = new["grade"]
        old_g_lbl = frame.findChild(QLabel, f"old_grade_{slot}")
        new_g_lbl = frame.findChild(QLabel, f"new_grade_{slot}")
        old_g_lbl.setText(f"◆ {og}")
        old_g_lbl.setStyleSheet(GRADE_STYLE.get(og, "") + " font-size: 16px; background: transparent;")
        new_g_lbl.setText(f"◆ {ng}")
        new_g_lbl.setStyleSheet(GRADE_STYLE.get(ng, "") + " font-size: 16px; background: transparent;")

        for key in STAT_KEYS:
            bar = frame.findChild(StatBar, f"bar_{slot}_{key}")
            if bar:
                bar.set_value(new[key], delta.get(key, 0))

        # 성장 하이라이트 요약
        growth_lbl = frame.findChild(QLabel, f"growth_{slot}")
        if growth_lbl:
            ups   = [STAT_LABELS[i] for i, k in enumerate(STAT_KEYS) if delta.get(k, 0) > 0]
            downs = [STAT_LABELS[i] for i, k in enumerate(STAT_KEYS) if delta.get(k, 0) < 0]
            parts = []
            if ups:
                parts.append("↑ " + "·".join(
                    f"{STAT_LABELS[STAT_KEYS.index(k)]} +{delta[k]}"
                    for k in STAT_KEYS if delta.get(k, 0) > 0
                ))
            if downs:
                parts.append("↓ " + "·".join(
                    f"{STAT_LABELS[STAT_KEYS.index(k)]} {delta[k]}"
                    for k in STAT_KEYS if delta.get(k, 0) < 0
                ))
            if parts:
                if downs and not ups:
                    growth_lbl.setStyleSheet(
                        "font-size: 11px; background: #FFF5F5; border: 1px solid #FECACA; "
                        "border-radius: 4px; padding: 3px 8px; color: #DC2626;"
                    )
                else:
                    growth_lbl.setStyleSheet(
                        "font-size: 11px; background: #F0FDF4; border: 1px solid #BBF7D0; "
                        "border-radius: 4px; padding: 3px 8px; color: #15803D;"
                    )
                growth_lbl.setText("  |  ".join(parts))
                growth_lbl.show()
            else:
                growth_lbl.hide()

        quote_lbl = frame.findChild(QLabel, f"quote_{slot}")
        if quote_lbl:
            if is_winner:
                q = get_win_quote(new["name"])
                quote_lbl.setStyleSheet(
                    "color: #F59E0B; font-size: 12px; font-style: italic; background: transparent;"
                )
            else:
                q = get_loss_quote(new["name"])
                quote_lbl.setStyleSheet(
                    "color: #868E96; font-size: 12px; font-style: italic; background: transparent;"
                )
            quote_lbl.setText(f'"{q}"' if q else "")

    def _flash_winner(self):
        self._flash += self._flash_dir * 10
        if self._flash >= 60:
            self._flash_dir = -1
        elif self._flash <= 0:
            self._flash_dir = 1
        r = min(255, 200 + self._flash)
        g = min(255, 130 + self._flash // 2)
        self.lbl_result.setStyleSheet(
            f"color: rgb({r},{g},0); font-size: 30px; font-weight: bold; background: transparent;"
        )

    def _flash_upset(self):
        self._upset_flash += self._upset_fd * 12
        if self._upset_flash >= 60:
            self._upset_fd = -1
        elif self._upset_flash <= 0:
            self._upset_fd = 1
        r = min(255, 200 + self._upset_flash)
        g = min(255, 80 + self._upset_flash // 3)
        self.lbl_upset.setStyleSheet(
            f"color: rgb({r},{g},0); font-size: 22px; font-weight: bold; background: transparent;"
        )
