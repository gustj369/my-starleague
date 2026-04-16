"""경기 시뮬레이션 화면 — PRD v7 빌드 선택 + 3페이즈 중계"""
import random as _random

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QDialog, QListWidget,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from database.db import get_connection
from core.match import simulate_set, finalize_match, SETS_TO_WIN, SetResult, MatchOutcome
from core.balance import (
    roll_condition, apply_condition_item, CONDITION_COLOR,
    fatigue_mult, add_fatigue, GRADE_ORDER,
)
from core.commentary import get_set_commentary
from core.builds import get_build_name, calc_build_result, BUILD_TYPES
from ui.styles import GRADE_STYLE, RACE_COLORS
from ui.widgets import make_separator, get_player_image_path
from core.player_data import PLAYER_DATA

COMMENTARY_DELAY_MS = 900    # 중계 한 줄 표시 간격
SET_RESULT_DELAY_MS = 500    # 세트 결과 표시까지 딜레이
BUILD_REVEAL_DELAY_MS = 1400  # 빌드 선택 후 시뮬레이션 진행까지 대기


def _load_player(pid: int) -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM players WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else {}


def _load_emergency_items(player_id: int) -> list[dict]:
    """컨디션/피로회복 아이템만 반환"""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT pi.id as pi_id, i.id, i.name, i.item_type,
                      i.condition_up, i.fatigue_recover
               FROM player_items pi
               JOIN items i ON i.id = pi.item_id
               WHERE pi.player_id = ?
                 AND (i.condition_up > 0 OR i.fatigue_recover > 0)""",
            (player_id,)
        ).fetchall()
    return [dict(r) for r in rows]


class EmergencyItemDialog(QDialog):
    """세트 패배 후 긴급 아이템 선택 다이얼로그"""
    def __init__(self, items: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("긴급 아이템 사용")
        self.setMinimumWidth(360)
        self._selected_item: dict | None = None

        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        lbl = QLabel("사용할 아이템을 선택하세요:")
        lbl.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: bold;")
        lay.addWidget(lbl)

        self.lst = QListWidget()
        self.lst.setStyleSheet("""
            QListWidget { background: #FFFFFF; border: 1px solid #E9ECEF; border-radius:4px; }
            QListWidget::item { padding: 6px 10px; color: #212529; }
            QListWidget::item:selected { background: #EEF2FF; color: #F59E0B; }
        """)
        for it in items:
            if it.get("condition_up", 0):
                desc = f"컨디션 한 단계 상승"
            else:
                desc = f"피로도 -{it['fatigue_recover']}"
            self.lst.addItem(f"{it['name']}  ({desc})")
        self.lst.setCurrentRow(0)
        lay.addWidget(self.lst)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self._items = items

    def selected_index(self) -> int:
        return self.lst.currentRow()


class SimulationScreen(QWidget):
    sig_match_done = pyqtSignal(object)  # MatchOutcome

    def __init__(self, parent=None):
        super().__init__(parent)
        self._reset_state()
        self._build_ui()

    # ── 내부 상태 ────────────────────────────────────────────
    def _reset_state(self):
        self._my_id: int = 0
        self._opp_id: int = 0
        self._map_id: int = 0
        self._tm_id: int = 0
        self._round_name: str = ""
        self._sets_to_win: int = 2
        self._my_condition: str = "보통"
        self._opp_condition: str = "보통"
        self._my_fatigue: int = 0
        self._my_race: str = "테란"
        self._opp_race: str = "테란"
        self._a_wins: int = 0
        self._b_wins: int = 0
        self._all_sets: list[SetResult] = []
        self._commentary_queue: list[str] = []
        self._timer: QTimer | None = None
        self._match_over: bool = False
        self._pending_my_build: str = "수비"
        self._pending_ai_build: str = "수비"
        self._pending_set_result: SetResult | None = None
        self._my_build_history: list[str] = []
        self._pending_strategy: str = "균형"

    # ── UI 빌드 ──────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(10)

        # ── 헤더 ──
        hdr = QHBoxLayout()
        self.lbl_round_set = QLabel("16강 — 1세트")
        self.lbl_round_set.setStyleSheet(
            "color: #5B6CF6; font-size: 16px; font-weight: bold; background: transparent;"
        )
        self.lbl_rival_badge = QLabel("")
        self.lbl_rival_badge.setStyleSheet(
            "color: #FF6B6B; font-size: 13px; font-weight: bold; background: transparent;"
        )
        hdr.addWidget(self.lbl_round_set)
        hdr.addStretch()
        hdr.addWidget(self.lbl_rival_badge)

        # ── 선수 VS 패널 ──
        vs_row = QHBoxLayout()
        self.panel_a = self._make_player_panel("a")
        vs_lbl = QLabel("VS")
        vs_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs_lbl.setStyleSheet(
            "color: #F59E0B; font-size: 28px; font-weight: bold; background: transparent;"
        )
        vs_lbl.setFixedWidth(48)
        self.panel_b = self._make_player_panel("b")
        vs_row.addWidget(self.panel_a, 1)
        vs_row.addWidget(vs_lbl)
        vs_row.addWidget(self.panel_b, 1)

        # ── 스코어 ──
        self.lbl_score = QLabel("0  —  0")
        self.lbl_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_score.setStyleSheet(
            "color: #F59E0B; font-size: 26px; font-weight: bold; background: transparent;"
        )

        # ── 빌드 선택 프레임 / 중계 프레임 (스택) ──
        self.mid_stack = QStackedWidget()

        # idx 0: 빌드 선택 화면
        self.build_frame = self._make_build_frame()
        self.mid_stack.addWidget(self.build_frame)

        # idx 1: 중계 텍스트 화면
        self.commentary_frame = self._make_commentary_frame()
        self.mid_stack.addWidget(self.commentary_frame)

        # idx 2: 라이벌 인트로 화면
        self.rival_intro_frame = self._make_rival_intro_frame()
        self.mid_stack.addWidget(self.rival_intro_frame)

        self.mid_stack.setCurrentIndex(0)

        # ── 세트 결과 배너 ──
        self.lbl_set_result = QLabel("")
        self.lbl_set_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_set_result.setStyleSheet(
            "color: #F59E0B; font-size: 18px; font-weight: bold; background: transparent;"
        )

        # ── 페이즈 결과 미니 표시 ──
        self.lbl_phase_scores = QLabel("")
        self.lbl_phase_scores.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_phase_scores.setStyleSheet(
            "color: #5B6CF6; font-size: 12px; background: transparent;"
        )

        # ── 하단 버튼 ──
        btn_row = QHBoxLayout()
        self.btn_item = QPushButton("⚡ 긴급 아이템 사용")
        self.btn_item.setFixedHeight(38)
        self.btn_item.setStyleSheet("""
            QPushButton { background:#5B6CF6; color:#fff; border-radius:4px;
                          font-size:12px; border:1px solid #4A5CE0; padding:0 14px; }
            QPushButton:hover { background:#4A5CE0; }
            QPushButton:disabled { background:#FFFFFF; color:#ADB5BD; border-color:#E9ECEF; }
        """)
        self.btn_item.setEnabled(False)
        self.btn_item.clicked.connect(self._on_use_item)

        self.btn_next = QPushButton("▶  다음 세트")
        self.btn_next.setProperty("class", "primary")
        self.btn_next.setMinimumHeight(44)
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self._on_next)

        btn_row.addWidget(self.btn_item)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_next)

        root.addLayout(hdr)
        root.addWidget(make_separator())
        root.addLayout(vs_row)
        root.addWidget(self.lbl_score)
        root.addWidget(make_separator())
        root.addWidget(self.mid_stack, 1)
        root.addWidget(self.lbl_set_result)
        root.addWidget(self.lbl_phase_scores)
        root.addWidget(make_separator())
        root.addLayout(btn_row)

    def _make_player_panel(self, slot: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 6px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        tag_color = "#5B6CF6" if slot == "a" else "#868E96"
        tag = QLabel("내 선수" if slot == "a" else "상대")
        tag.setStyleSheet(f"color:{tag_color}; font-size:11px; font-weight:bold; background:transparent;")

        # 선수 이미지 아바타
        avatar = QLabel("?")
        avatar.setObjectName(f"avatar_{slot}")
        avatar.setFixedSize(64, 64)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            "background: #EEF2FF; color: #5B6CF6; font-size: 20px; "
            "font-weight: bold; border-radius: 32px; border: 2px solid #C5D0E8;"
        )
        avatar_row = QHBoxLayout()
        avatar_row.addStretch()
        avatar_row.addWidget(avatar)
        avatar_row.addStretch()

        name = QLabel("—")
        name.setObjectName(f"name_{slot}")
        name.setStyleSheet("font-size:18px; font-weight:bold; background:transparent;")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        grade = QLabel("")
        grade.setObjectName(f"grade_{slot}")
        grade.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cond = QLabel("")
        cond.setObjectName(f"cond_{slot}")
        cond.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cond.setStyleSheet("font-size:12px; background:transparent;")

        fatigue = QLabel("")
        fatigue.setObjectName(f"fat_{slot}")
        fatigue.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fatigue.setStyleSheet("color:#FF6B6B; font-size:11px; background:transparent;")

        lay.addWidget(tag)
        lay.addLayout(avatar_row)
        lay.addWidget(name)
        lay.addWidget(grade)
        lay.addWidget(cond)
        lay.addWidget(fatigue)
        return frame

    def _make_build_frame(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 6px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(20, 12, 20, 12)
        lay.setSpacing(10)

        # ── 전략 선택 섹션 ──
        strat_title = QLabel("① 전략 선택")
        strat_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        strat_title.setStyleSheet(
            "color: #F59E0B; font-size: 13px; font-weight: bold; background: transparent;"
        )

        strat_row = QHBoxLayout()
        strat_row.setSpacing(8)
        self.strategy_btns: list[QPushButton] = []
        STRAT_INFO = [
            ("초반집중", "초반 +20\n후반 −10"),
            ("균형",     "균형 운영\n변동 없음"),
            ("후반체력전", "초반 −10\n후반 +20"),
        ]
        for sname, sdesc in STRAT_INFO:
            btn = QPushButton(f"{sname}\n{sdesc}")
            btn.setProperty("_stype", sname)
            btn.setMinimumHeight(60)
            btn.setStyleSheet("""
                QPushButton {
                    background: #FFFFFF; color: #495057;
                    border: 1px solid #DEE2E6; border-radius: 10px;
                    font-size: 11px; padding: 4px 6px;
                }
                QPushButton:hover { border-color: #5B6CF6; color: #5B6CF6; background: #EEF2FF; }
                QPushButton:disabled { color: #ADB5BD; border-color: #E9ECEF; background: #F8F9FA; }
            """)
            btn.clicked.connect(lambda _, s=sname: self._on_strategy_picked(s))
            self.strategy_btns.append(btn)
            strat_row.addWidget(btn)

        self.lbl_strategy_picked = QLabel("")
        self.lbl_strategy_picked.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_strategy_picked.setStyleSheet(
            "color: #5B6CF6; font-size: 12px; background: transparent;"
        )

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #E9ECEF;")

        # ── 전술 선택 섹션 (PRD v11: 빌드→전술 삼각체계) ──────
        tactic_title = QLabel("② 전술 선택")
        tactic_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tactic_title.setStyleSheet(
            "color: #868E96; font-size: 13px; font-weight: bold; background: transparent;"
        )
        tactic_title.setObjectName("build_title_lbl")

        rps_hint = QLabel("공세  ▶  수비  ▶  기동  ▶  공세  (앞이 뒤를 이김)")
        rps_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rps_hint.setStyleSheet("color: #ADB5BD; font-size: 11px; background: transparent;")

        from core.builds import TACTIC_DESC
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.build_btns: list[QPushButton] = []
        for btype in BUILD_TYPES:
            desc = TACTIC_DESC.get(btype, "")
            # 전술 설명 두 줄로 표시
            short_desc = desc.split(".")[0] if desc else ""
            btn = QPushButton(f"{btype}\n{short_desc}")
            btn.setProperty("_btype", btype)
            btn.setMinimumHeight(60)
            btn.setEnabled(False)   # 전략 선택 후 활성화
            btn.setStyleSheet("""
                QPushButton {
                    background: #FFFFFF; color: #495057;
                    border: 1px solid #DEE2E6; border-radius: 10px;
                    font-size: 11px; padding: 4px 10px;
                }
                QPushButton:hover { border-color: #5B6CF6; color: #5B6CF6; background: #EEF2FF; }
                QPushButton:disabled { color: #ADB5BD; border-color: #E9ECEF; background: #F8F9FA; }
            """)
            btn.clicked.connect(lambda _, b=btype: self._on_build_picked(b))
            self.build_btns.append(btn)
            btn_row.addWidget(btn)

        self.lbl_build_reveal = QLabel("")
        self.lbl_build_reveal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_build_reveal.setWordWrap(True)
        self.lbl_build_reveal.setStyleSheet(
            "color: #212529; font-size: 13px; background: transparent; line-height: 1.5;"
        )

        self.lbl_build_result = QLabel("")
        self.lbl_build_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_build_result.setStyleSheet(
            "color: #F59E0B; font-size: 14px; font-weight: bold; background: transparent;"
        )

        lay.addWidget(strat_title)
        lay.addLayout(strat_row)
        lay.addWidget(self.lbl_strategy_picked)
        lay.addWidget(sep)
        lay.addWidget(tactic_title)
        lay.addWidget(rps_hint)
        lay.addLayout(btn_row)
        lay.addWidget(self.lbl_build_reveal)
        lay.addWidget(self.lbl_build_result)

        return frame

    def _make_commentary_frame(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 6px; }"
        )
        cf_lay = QVBoxLayout(frame)
        cf_lay.setContentsMargins(16, 12, 16, 12)
        cf_lay.setSpacing(6)

        self.lbl_c1 = self._commentary_label()
        self.lbl_c2 = self._commentary_label()
        self.lbl_c3 = self._commentary_label()
        cf_lay.addWidget(self.lbl_c1)
        cf_lay.addWidget(self.lbl_c2)
        cf_lay.addWidget(self.lbl_c3)

        return frame

    def _make_rival_intro_frame(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #FFF5F5; border: 2px solid #FF6B6B; border-radius: 12px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(30, 20, 30, 20)
        lay.setSpacing(16)

        banner = QLabel("🔥 라이벌 매치!")
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner.setStyleSheet(
            "color: #FF6B6B; font-size: 22px; font-weight: bold; background: transparent;"
        )

        self.lbl_rival_quote_a = QLabel("")
        self.lbl_rival_quote_a.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_rival_quote_a.setWordWrap(True)
        self.lbl_rival_quote_a.setStyleSheet(
            "color: #F59E0B; font-size: 15px; font-style: italic; background: transparent;"
        )

        vs_sep = QLabel("— VS —")
        vs_sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs_sep.setStyleSheet("color: #ADB5BD; font-size: 13px; background: transparent;")

        self.lbl_rival_quote_b = QLabel("")
        self.lbl_rival_quote_b.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_rival_quote_b.setWordWrap(True)
        self.lbl_rival_quote_b.setStyleSheet(
            "color: #5B6CF6; font-size: 15px; font-style: italic; background: transparent;"
        )

        h2h_lbl = QLabel("")
        h2h_lbl.setObjectName("lbl_h2h")
        h2h_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h2h_lbl.setStyleSheet(
            "color: #868E96; font-size: 12px; background: transparent;"
        )

        lay.addStretch()
        lay.addWidget(banner)
        lay.addWidget(h2h_lbl)
        lay.addSpacing(10)
        lay.addWidget(self.lbl_rival_quote_a)
        lay.addWidget(vs_sep)
        lay.addWidget(self.lbl_rival_quote_b)
        lay.addStretch()

        return frame

    @staticmethod
    def _commentary_label() -> QLabel:
        lbl = QLabel("")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            "color: #212529; font-size: 13px; background: transparent; padding: 3px 0;"
        )
        return lbl

    # ── 외부에서 호출: 경기 로드 ─────────────────────────────
    def load_match(self, my_id: int, opp_id: int, map_id: int,
                   my_condition: str, tm_id: int, round_name: str):
        self._reset_state()
        self._my_id = my_id
        self._opp_id = opp_id
        self._map_id = map_id
        self._tm_id = tm_id
        self._round_name = round_name
        self._sets_to_win = SETS_TO_WIN.get(round_name, 2)
        self._my_condition = my_condition

        pa = _load_player(my_id)
        pb = _load_player(opp_id)
        self._my_race = pa.get("race", "테란")
        self._opp_race = pb.get("race", "테란")
        self._opp_condition = roll_condition(pb.get("grade", "C"))
        self._my_fatigue = pa.get("fatigue", 0)

        # 라이벌 여부
        from core.balance import is_rival
        if is_rival(my_id, opp_id):
            self.lbl_rival_badge.setText("🔥 라이벌 매치!")
        else:
            self.lbl_rival_badge.setText("")

        self._fill_panel("a", pa, self._my_condition, self._my_fatigue)
        self._fill_panel("b", pb, self._opp_condition, pb.get("fatigue", 0))

        total = self._sets_to_win * 2 - 1
        self.lbl_round_set.setText(f"{round_name}  —  1세트 / {total}세트")
        # 결승전 특별 스타일
        if round_name == "결승":
            self.lbl_round_set.setStyleSheet(
                "color: #F59E0B; font-size: 18px; font-weight: bold; background: transparent;"
                " border: 2px solid #F59E0B; border-radius: 8px; padding: 2px 10px; background: #FFFBEB;"
            )
            self.lbl_rival_badge.setText(
                (self.lbl_rival_badge.text() + "  " if self.lbl_rival_badge.text() else "") + "★ 결승전 ★"
            )
        else:
            self.lbl_round_set.setStyleSheet(
                "color: #5B6CF6; font-size: 16px; font-weight: bold; background: transparent;"
            )
        self._update_score()
        self._clear_commentary()
        self.lbl_set_result.setText("")
        self.btn_next.setEnabled(False)
        self.btn_item.setEnabled(False)

        # 첫 세트: 라이벌이면 인트로, 아니면 바로 빌드 선택
        from core.balance import is_rival as _is_rival
        if _is_rival(self._my_id, self._opp_id):
            QTimer.singleShot(300, self._show_rival_intro)
        else:
            QTimer.singleShot(300, self._show_build_select)

    # ── 패널 채우기 ──────────────────────────────────────────
    def _fill_panel(self, slot: str, player: dict, condition: str, fatigue: int):
        from PyQt6.QtGui import QPixmap
        panel = self.panel_a if slot == "a" else self.panel_b

        # 아바타 이미지
        avatar_lbl = panel.findChild(QLabel, f"avatar_{slot}")
        if avatar_lbl:
            img_path = get_player_image_path(player.get("name", ""))
            if img_path:
                px = QPixmap(img_path).scaled(
                    64, 64,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                avatar_lbl.setPixmap(px)
                avatar_lbl.setStyleSheet(
                    "border-radius: 32px; background: #FFFFFF; border: 2px solid #E9ECEF;"
                )
            else:
                avatar_lbl.setText(player.get("name", "?")[:1])
                avatar_lbl.setStyleSheet(
                    "background: #EEF2FF; color: #5B6CF6; font-size: 20px; "
                    "font-weight: bold; border-radius: 32px; border: 2px solid #C5D0E8;"
                )

        panel.findChild(QLabel, f"name_{slot}").setText(player.get("name", "?"))

        grade = player.get("grade", "C")
        gl = panel.findChild(QLabel, f"grade_{slot}")
        gl.setText(f"◆ {grade}")
        gl.setStyleSheet(
            GRADE_STYLE.get(grade, "") + " font-size:17px; background:transparent;"
        )

        cond_color = CONDITION_COLOR.get(condition, "#212529")
        cl = panel.findChild(QLabel, f"cond_{slot}")
        cl.setText(f"컨디션: {condition}")
        cl.setStyleSheet(
            f"color:{cond_color}; font-size:12px; background:transparent;"
        )

        fl = panel.findChild(QLabel, f"fat_{slot}")
        fl.setText(f"피로도: {fatigue}/100")

    def _set_panel_glow(self, winner_slot: str):
        """세트 결과에 따라 패널 테두리 색 변경 (승리=금색, 패배=빨간색)"""
        loser_slot = "b" if winner_slot == "a" else "a"
        winner_panel = self.panel_a if winner_slot == "a" else self.panel_b
        loser_panel  = self.panel_a if loser_slot  == "a" else self.panel_b
        winner_panel.setStyleSheet(
            "QFrame { background: #F0FFF4; border: 2px solid #51CF66; border-radius: 6px; }"
        )
        loser_panel.setStyleSheet(
            "QFrame { background: #FFF5F5; border: 2px solid #FF6B6B; border-radius: 6px; }"
        )

    def _reset_panel_glow(self):
        """패널 테두리를 기본값으로 복원"""
        for panel in [self.panel_a, self.panel_b]:
            panel.setStyleSheet(
                "QFrame { background: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 6px; }"
            )

    # ── 스코어 표시 ──────────────────────────────────────────
    def _update_score(self):
        self.lbl_score.setText(f"{self._a_wins}  —  {self._b_wins}")

    # ── 중계 초기화 ──────────────────────────────────────────
    def _clear_commentary(self):
        for lbl in [self.lbl_c1, self.lbl_c2, self.lbl_c3]:
            lbl.setText("")

    # ── 라이벌 인트로 ────────────────────────────────────────
    def _show_rival_intro(self):
        """라이벌 매치 시작 시 양측 대사를 순차 표시"""
        from core.balance import get_h2h_record
        pa = _load_player(self._my_id)
        pb = _load_player(self._opp_id)
        pd_a = PLAYER_DATA.get(pa.get("name", ""), {})
        pd_b = PLAYER_DATA.get(pb.get("name", ""), {})

        rival_q_a = pd_a.get("rival_quote", "") or (pd_a.get("pre_match", [""])[0])
        rival_q_b = pd_b.get("rival_quote", "") or (pd_b.get("pre_match", [""])[0])

        # H2H 전적
        h2h = get_h2h_record(self._my_id, self._opp_id)
        if h2h["total"] > 0:
            h2h_str = f"통산 전적: {pa['name']} {h2h['a_wins']}승 {h2h['b_wins']}패"
        else:
            h2h_str = "첫 번째 라이벌 맞대결"
        # H2H 레이블 업데이트 (rival_intro_frame 안에)
        h2h_lbl = self.rival_intro_frame.findChild(QLabel, "lbl_h2h")
        if h2h_lbl:
            h2h_lbl.setText(h2h_str)

        self.lbl_rival_quote_a.setText(f'"{pa["name"]}: {rival_q_a}"' if rival_q_a else "")
        self.lbl_rival_quote_b.setText("")  # 처음에는 숨김

        self.mid_stack.setCurrentIndex(2)

        # 2.2초 후 상대 대사 표시
        QTimer.singleShot(2200, lambda: self.lbl_rival_quote_b.setText(
            f'"{pb["name"]}: {rival_q_b}"' if rival_q_b else ""
        ))
        # 4.5초 후 빌드 선택으로 이동
        QTimer.singleShot(4500, self._show_build_select)

    # ── 빌드 선택 화면 표시 ──────────────────────────────────
    def _show_build_select(self):
        set_num = len(self._all_sets) + 1
        total = self._sets_to_win * 2 - 1
        self._reset_panel_glow()
        self.lbl_round_set.setText(
            f"{self._round_name}  —  {set_num}세트 / {total}세트"
        )
        if self._round_name == "결승":
            self.lbl_round_set.setStyleSheet(
                "color: #F59E0B; font-size: 18px; font-weight: bold; background: transparent;"
                " border: 2px solid #F59E0B; border-radius: 8px; padding: 2px 10px; background: #FFFBEB;"
            )
        else:
            self.lbl_round_set.setStyleSheet(
                "color: #5B6CF6; font-size: 16px; font-weight: bold; background: transparent;"
            )
        self._clear_commentary()
        self.lbl_set_result.setText("")
        self.btn_next.setEnabled(False)
        self.btn_item.setEnabled(False)

        # 전략 버튼 초기화
        for btn in self.strategy_btns:
            btn.setEnabled(True)
            btn.setStyleSheet("""
                QPushButton {
                    background: #FFFFFF; color: #495057;
                    border: 1px solid #DEE2E6; border-radius: 10px;
                    font-size: 11px; padding: 4px 6px;
                }
                QPushButton:hover { border-color: #5B6CF6; color: #5B6CF6; background: #EEF2FF; }
                QPushButton:disabled { color: #ADB5BD; border-color: #E9ECEF; background: #F8F9FA; }
            """)
        self.lbl_strategy_picked.setText("")
        # 빌드 버튼 비활성화 (전략 먼저 골라야)
        for btn in self.build_btns:
            btn.setEnabled(False)
        build_title = self.build_frame.findChild(QLabel, "build_title_lbl")
        if build_title:
            build_title.setStyleSheet(
                "color: #868E96; font-size: 13px; font-weight: bold; background: transparent;"
            )
        self._pending_strategy = "균형"

        # 전술 버튼 이름 업데이트 (전술 삼각체계)
        from core.builds import TACTIC_NAMES, TACTIC_DESC
        for btn in self.build_btns:
            btype = btn.property("_btype")
            bname = TACTIC_NAMES.get(btype, btype)
            short = TACTIC_DESC.get(btype, "").split(".")[0]
            btn.setText(f"{bname}  [{btype}]\n{short}")

        self.lbl_build_reveal.setText("")
        self.lbl_build_result.setText("")
        self.lbl_phase_scores.setText("")
        self.mid_stack.setCurrentIndex(0)

    # ── 전략 선택 처리 ───────────────────────────────────────
    def _on_strategy_picked(self, strategy: str):
        self._pending_strategy = strategy
        # 전략 버튼 비활성화 + 선택된 것 강조
        for btn in self.strategy_btns:
            stype = btn.property("_stype")
            if stype == strategy:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #EEF2FF; color: #5B6CF6;
                        border: 2px solid #5B6CF6; border-radius: 10px;
                        font-size: 11px; padding: 4px 6px; font-weight: bold;
                    }
                """)
            else:
                btn.setEnabled(False)
                btn.setStyleSheet("""
                    QPushButton {
                        color: #ADB5BD; border-color: #E9ECEF;
                        background: #F8F9FA; border-radius: 10px;
                        font-size: 11px; padding: 4px 6px;
                    }
                """)

        strat_desc = {"초반집중": "초반에 모든 것을 쏟는다", "균형": "균형 잡힌 운영", "후반체력전": "후반까지 아껴둔다"}
        self.lbl_strategy_picked.setText(f"✔ {strategy} — {strat_desc.get(strategy, '')}")

        # 빌드 버튼 활성화 + 제목 강조
        for btn in self.build_btns:
            btn.setEnabled(True)
        build_title = self.build_frame.findChild(QLabel, "build_title_lbl")
        if build_title:
            build_title.setStyleSheet(
                "color: #F59E0B; font-size: 13px; font-weight: bold; background: transparent;"
            )

    # ── 빌드 선택 처리 ───────────────────────────────────────
    def _on_build_picked(self, build: str):
        # 버튼 비활성화
        for btn in self.build_btns:
            btn.setEnabled(False)

        self._pending_my_build = build
        self._my_build_history.append(build)
        ai_build = self._pick_ai_build()
        self._pending_ai_build = ai_build

        # 전술 이름
        from core.builds import TACTIC_NAMES
        my_bname = TACTIC_NAMES.get(build, build)
        ai_bname = TACTIC_NAMES.get(ai_build, ai_build)

        # 전술 공개
        self.lbl_build_reveal.setText(
            f"내 선수  :  {my_bname}  ({build})\n"
            f"상  대   :  {ai_bname}  ({ai_build})"
        )

        # 결과 뱃지
        br = calc_build_result(build, ai_build)
        if br > 0:
            self.lbl_build_result.setText("✔ 전술 우위 — 초반 유리!")
            self.lbl_build_result.setStyleSheet(
                "color: #5B6CF6; font-size: 14px; font-weight: bold; background: transparent;"
            )
        elif br < 0:
            self.lbl_build_result.setText("✘ 전술 열세 — 초반 불리...")
            self.lbl_build_result.setStyleSheet(
                "color: #FF6B6B; font-size: 14px; font-weight: bold; background: transparent;"
            )
        else:
            self.lbl_build_result.setText("▶ 전술 동등 — 순수 실력 대결!")
            self.lbl_build_result.setStyleSheet(
                "color: #F59E0B; font-size: 14px; font-weight: bold; background: transparent;"
            )

        # BUILD_REVEAL_DELAY_MS 후 시뮬레이션 진행
        QTimer.singleShot(BUILD_REVEAL_DELAY_MS, self._run_set_after_build)

    def _pick_ai_build(self) -> str:
        """AI 전술 선택. 직전 세트에서 플레이어가 이겼으면 40% 확률로 카운터 전술."""
        from core.builds import TACTIC_WINS
        if self._all_sets and self._my_build_history:
            last_set = self._all_sets[-1]
            last_my_build = self._my_build_history[-1]
            if last_set.winner_id == self._my_id:
                # 플레이어가 직전 세트 승리 → AI가 카운터 전술로 맞대응
                # 카운터 = 내 전술을 이기는 전술 (역관계 반전)
                counter = {v: k for k, v in TACTIC_WINS.items()}.get(last_my_build)
                if counter and _random.random() < 0.40:
                    return counter
        return _random.choice(BUILD_TYPES)

    # ── 빌드 확정 후 세트 시뮬레이션 ────────────────────────
    def _run_set_after_build(self):
        # 중계 화면으로 전환
        self.mid_stack.setCurrentIndex(1)
        self._clear_commentary()

        set_num = len(self._all_sets) + 1

        result = simulate_set(
            self._my_id, self._opp_id, self._map_id,
            self._my_condition, self._opp_condition,
            a_fatigue_override=self._my_fatigue,
            set_number=set_num,
            series_score=(self._a_wins, self._b_wins),
            build_a=self._pending_my_build,
            build_b=self._pending_ai_build,
            strategy_a=self._pending_strategy,
        )
        self._all_sets.append(result)

        if result.winner_id == self._my_id:
            self._a_wins += 1
        else:
            self._b_wins += 1

        # 중계 문구 생성 (페이즈 정보 포함)
        pa = _load_player(self._my_id)
        pb = _load_player(self._opp_id)
        lines = get_set_commentary(
            pa.get("name", "A"), pb.get("name", "B"),
            result.a_power, result.b_power,
            result.winner_id, self._my_id,
            phases=result.phases,
        )
        self._commentary_queue = lines[:]
        self._comment_labels = [self.lbl_c1, self.lbl_c2, self.lbl_c3]
        self._comment_idx = 0
        self._pending_set_result = result

        # 타이머로 순차 표시
        if self._timer:
            self._timer.stop()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._show_next_commentary)
        self._timer.start(COMMENTARY_DELAY_MS)

    # ── 중계 순차 표시 ───────────────────────────────────────
    def _show_next_commentary(self):
        if self._comment_idx < len(self._commentary_queue):
            self._comment_labels[self._comment_idx].setText(
                f"▸ {self._commentary_queue[self._comment_idx]}"
            )
            self._comment_idx += 1
        else:
            self._timer.stop()
            QTimer.singleShot(SET_RESULT_DELAY_MS, self._show_set_result)

    # ── 세트 결과 표시 ───────────────────────────────────────
    def _show_set_result(self):
        result = self._pending_set_result
        pa = _load_player(self._my_id)
        pb = _load_player(self._opp_id)
        w_name = pa.get("name") if result.winner_id == self._my_id else pb.get("name")
        set_num = result.set_number

        # 이변/모멘텀 배지
        badge = ""
        a_grade = pa.get("grade", "C")
        b_grade = pb.get("grade", "C")
        try:
            a_idx = GRADE_ORDER.index(a_grade)
            b_idx = GRADE_ORDER.index(b_grade)
        except ValueError:
            a_idx = b_idx = 4

        winner_is_a = (result.winner_id == self._my_id)
        grade_diff = abs(a_idx - b_idx)
        underdog_won = (winner_is_a and a_idx > b_idx) or (not winner_is_a and b_idx > a_idx)

        a_before = self._a_wins - (1 if winner_is_a else 0)
        b_before = self._b_wins - (1 if not winner_is_a else 0)
        comeback = (winner_is_a and b_before > a_before) or (not winner_is_a and a_before > b_before)

        if underdog_won and grade_diff >= 2:
            badge = "  ⚡ 이변 예감!"
        elif underdog_won and grade_diff == 1:
            badge = "  🔥 분위기 전환!"
        elif comeback:
            badge = "  🔥 분위기 전환!"

        self.lbl_set_result.setText(
            f"★  {set_num}세트: {w_name} 승!   ( {self._a_wins} - {self._b_wins} ){badge}"
        )
        self._update_score()
        winner_slot = "a" if result.winner_id == self._my_id else "b"
        self._set_panel_glow(winner_slot)

        # 페이즈 결과 표시
        if result.phases:
            parts = []
            for ph in result.phases:
                ph_winner_name = pa.get("name") if ph.winner_id == self._my_id else pb.get("name")
                parts.append(f"【{ph.phase_name}】{ph_winner_name} ✓")
            self.lbl_phase_scores.setText("  |  ".join(parts))
        else:
            self.lbl_phase_scores.setText("")

        # 승부 결정 여부
        if self._a_wins >= self._sets_to_win or self._b_wins >= self._sets_to_win:
            self._match_over = True
            self.btn_next.setText("▶  결과 보기")
            self.btn_next.setEnabled(True)
            self.btn_item.setEnabled(False)
        else:
            my_lost_set = (result.winner_id != self._my_id)
            emergency_items = _load_emergency_items(self._my_id)
            self.btn_item.setEnabled(my_lost_set and len(emergency_items) > 0)
            self.btn_next.setText(f"▶  {set_num + 1}세트 빌드 선택")
            self.btn_next.setEnabled(True)

    # ── 긴급 아이템 사용 ─────────────────────────────────────
    def _on_use_item(self):
        items = _load_emergency_items(self._my_id)
        if not items:
            return

        dlg = EmergencyItemDialog(items, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        idx = dlg.selected_index()
        if idx < 0 or idx >= len(items):
            return
        it = items[idx]

        if it.get("condition_up", 0):
            self._my_condition = apply_condition_item(self._my_condition)
            pa = _load_player(self._my_id)
            self._fill_panel("a", pa, self._my_condition, self._my_fatigue)

        if it.get("fatigue_recover", 0):
            self._my_fatigue = max(0, self._my_fatigue - it["fatigue_recover"])
            with get_connection() as conn:
                conn.execute(
                    "UPDATE players SET fatigue = MAX(0, fatigue - ?) WHERE id = ?",
                    (it["fatigue_recover"], self._my_id)
                )
                conn.commit()
            pa = _load_player(self._my_id)
            self._fill_panel("a", pa, self._my_condition, self._my_fatigue)

        with get_connection() as conn:
            conn.execute("DELETE FROM player_items WHERE id = ?", (it["pi_id"],))
            conn.commit()

        self.btn_item.setEnabled(False)

    # ── 다음 버튼 ────────────────────────────────────────────
    def _on_next(self):
        if self._match_over:
            self._finalize()
        else:
            self._show_build_select()

    # ── 경기 종료 처리 ───────────────────────────────────────
    def _finalize(self):
        outcome = finalize_match(
            self._my_id, self._opp_id,
            self._all_sets, self._map_id,
            self._my_condition, self._opp_condition,
            award_gold=True,
        )
        self.sig_match_done.emit(outcome)
