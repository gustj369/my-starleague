"""경기 시뮬레이션 화면 — 세트별 중계 텍스트 + 다전제 진행"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QDialog, QListWidget, QListWidgetItem,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from database.db import get_connection
from core.match import simulate_set, finalize_match, SETS_TO_WIN, SetResult, MatchOutcome
from core.balance import (
    roll_condition, apply_condition_item, CONDITION_COLOR,
    fatigue_mult, add_fatigue
)
from core.commentary import get_set_commentary
from ui.styles import GRADE_STYLE, RACE_COLORS
from ui.widgets import make_separator

COMMENTARY_DELAY_MS = 900    # 중계 한 줄 표시 간격
SET_RESULT_DELAY_MS = 500    # 세트 결과 표시까지 딜레이


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
        lbl.setStyleSheet("color: #ffd700; font-size: 13px; font-weight: bold;")
        lay.addWidget(lbl)

        self.lst = QListWidget()
        self.lst.setStyleSheet("""
            QListWidget { background: #0d1525; border: 1px solid #1e3a5f; border-radius:4px; }
            QListWidget::item { padding: 6px 10px; color: #c8d8e8; }
            QListWidget::item:selected { background: #1a3a6a; color: #ffd700; }
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
        self._my_fatigue: int = 0       # in-memory (수정 가능)
        self._a_wins: int = 0
        self._b_wins: int = 0
        self._all_sets: list[SetResult] = []
        self._commentary_queue: list[str] = []
        self._timer: QTimer | None = None
        self._match_over: bool = False

    # ── UI 빌드 ──────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(10)

        # ── 헤더 ──
        hdr = QHBoxLayout()
        self.lbl_round_set = QLabel("16강 — 1세트")
        self.lbl_round_set.setStyleSheet(
            "color: #4fc3f7; font-size: 16px; font-weight: bold; background: transparent;"
        )
        self.lbl_rival_badge = QLabel("")
        self.lbl_rival_badge.setStyleSheet(
            "color: #FF6F00; font-size: 13px; font-weight: bold; background: transparent;"
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
            "color: #ffd700; font-size: 28px; font-weight: bold; background: transparent;"
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
            "color: #ffd700; font-size: 26px; font-weight: bold; background: transparent;"
        )

        # ── 중계 텍스트 영역 ──
        self.commentary_frame = QFrame()
        self.commentary_frame.setStyleSheet(
            "QFrame { background: #0d1525; border: 1px solid #1e3a5f; border-radius: 6px; }"
        )
        cf_lay = QVBoxLayout(self.commentary_frame)
        cf_lay.setContentsMargins(16, 12, 16, 12)
        cf_lay.setSpacing(6)

        self.lbl_c1 = self._commentary_label()
        self.lbl_c2 = self._commentary_label()
        self.lbl_c3 = self._commentary_label()
        cf_lay.addWidget(self.lbl_c1)
        cf_lay.addWidget(self.lbl_c2)
        cf_lay.addWidget(self.lbl_c3)

        # ── 세트 결과 배너 ──
        self.lbl_set_result = QLabel("")
        self.lbl_set_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_set_result.setStyleSheet(
            "color: #ffd700; font-size: 18px; font-weight: bold; background: transparent;"
        )

        # ── 하단 버튼 ──
        btn_row = QHBoxLayout()
        self.btn_item = QPushButton("⚡ 긴급 아이템 사용")
        self.btn_item.setFixedHeight(38)
        self.btn_item.setStyleSheet("""
            QPushButton { background:#1565C0; color:#fff; border-radius:4px;
                          font-size:12px; border:1px solid #1976D2; padding:0 14px; }
            QPushButton:hover { background:#1976D2; }
            QPushButton:disabled { background:#0d1525; color:#334455; border-color:#1e3a5f; }
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
        root.addWidget(self.commentary_frame, 1)
        root.addWidget(self.lbl_set_result)
        root.addWidget(make_separator())
        root.addLayout(btn_row)

    def _make_player_panel(self, slot: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #0d1525; border: 1px solid #1e3a5f; border-radius: 6px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        tag_color = "#ffd700" if slot == "a" else "#4fc3f7"
        tag = QLabel("내 선수" if slot == "a" else "상대")
        tag.setStyleSheet(f"color:{tag_color}; font-size:11px; font-weight:bold; background:transparent;")

        name = QLabel("—")
        name.setObjectName(f"name_{slot}")
        name.setStyleSheet("font-size:18px; font-weight:bold; background:transparent;")

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
        fatigue.setStyleSheet("color:#EF9A9A; font-size:11px; background:transparent;")

        lay.addWidget(tag)
        lay.addWidget(name)
        lay.addWidget(grade)
        lay.addWidget(cond)
        lay.addWidget(fatigue)
        return frame

    @staticmethod
    def _commentary_label() -> QLabel:
        lbl = QLabel("")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            "color: #c8d8e8; font-size: 13px; background: transparent; "
            "padding: 3px 0;"
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
        self._update_score()
        self._clear_commentary()
        self.lbl_set_result.setText("")
        self.btn_next.setEnabled(False)
        self.btn_item.setEnabled(False)

        # 첫 세트 시작
        QTimer.singleShot(300, self._start_next_set)

    # ── 패널 채우기 ──────────────────────────────────────────
    def _fill_panel(self, slot: str, player: dict, condition: str, fatigue: int):
        panel = self.panel_a if slot == "a" else self.panel_b

        panel.findChild(QLabel, f"name_{slot}").setText(player.get("name", "?"))

        grade = player.get("grade", "C")
        gl = panel.findChild(QLabel, f"grade_{slot}")
        gl.setText(f"◆ {grade}")
        gl.setStyleSheet(
            GRADE_STYLE.get(grade, "") + " font-size:17px; background:transparent;"
        )

        cond_color = CONDITION_COLOR.get(condition, "#c8d8e8")
        cl = panel.findChild(QLabel, f"cond_{slot}")
        cl.setText(f"컨디션: {condition}")
        cl.setStyleSheet(
            f"color:{cond_color}; font-size:12px; background:transparent;"
        )

        fl = panel.findChild(QLabel, f"fat_{slot}")
        fl.setText(f"피로도: {fatigue}/100")

    # ── 스코어 표시 ──────────────────────────────────────────
    def _update_score(self):
        self.lbl_score.setText(f"{self._a_wins}  —  {self._b_wins}")

    # ── 중계 초기화 ──────────────────────────────────────────
    def _clear_commentary(self):
        for lbl in [self.lbl_c1, self.lbl_c2, self.lbl_c3]:
            lbl.setText("")

    # ── 세트 시작 ────────────────────────────────────────────
    def _start_next_set(self):
        set_num = len(self._all_sets) + 1
        total = self._sets_to_win * 2 - 1
        self.lbl_round_set.setText(
            f"{self._round_name}  —  {set_num}세트 / {total}세트"
        )
        self._clear_commentary()
        self.lbl_set_result.setText("")
        self.btn_next.setEnabled(False)
        self.btn_item.setEnabled(False)

        # 세트 시뮬레이션
        result = simulate_set(
            self._my_id, self._opp_id, self._map_id,
            self._my_condition, self._opp_condition,
            a_fatigue_override=self._my_fatigue,
            set_number=set_num,
        )
        self._all_sets.append(result)

        # 스코어 업데이트
        if result.winner_id == self._my_id:
            self._a_wins += 1
        else:
            self._b_wins += 1

        # 중계 문구 생성
        pa = _load_player(self._my_id)
        pb = _load_player(self._opp_id)
        lines = get_set_commentary(
            pa.get("name", "A"), pb.get("name", "B"),
            result.a_power, result.b_power,
            result.winner_id, self._my_id,
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
            # 모든 문구 표시 완료 → 세트 결과 표시
            self._timer.stop()
            QTimer.singleShot(SET_RESULT_DELAY_MS, self._show_set_result)

    # ── 세트 결과 표시 ───────────────────────────────────────
    def _show_set_result(self):
        result = self._pending_set_result
        pa = _load_player(self._my_id)
        pb = _load_player(self._opp_id)
        w_name = pa.get("name") if result.winner_id == self._my_id else pb.get("name")
        set_num = result.set_number

        self.lbl_set_result.setText(
            f"★  {set_num}세트: {w_name} 승!   ( {self._a_wins} - {self._b_wins} )"
        )
        self._update_score()

        # 승부 결정 여부
        if self._a_wins >= self._sets_to_win or self._b_wins >= self._sets_to_win:
            self._match_over = True
            self.btn_next.setText("▶  결과 보기")
            self.btn_next.setEnabled(True)
            self.btn_item.setEnabled(False)
        else:
            # 내 선수가 이 세트를 졌고 긴급 아이템이 있으면 버튼 활성화
            my_lost_set = (result.winner_id != self._my_id)
            emergency_items = _load_emergency_items(self._my_id)
            self.btn_item.setEnabled(my_lost_set and len(emergency_items) > 0)
            self.btn_next.setText(f"▶  {set_num + 1}세트 시작")
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

        # 아이템 효과 적용 (in-memory)
        if it.get("condition_up", 0):
            self._my_condition = apply_condition_item(self._my_condition)
            # 패널 업데이트
            pa = _load_player(self._my_id)
            self._fill_panel("a", pa, self._my_condition, self._my_fatigue)

        if it.get("fatigue_recover", 0):
            self._my_fatigue = max(0, self._my_fatigue - it["fatigue_recover"])
            # DB 피로도 감소
            with get_connection() as conn:
                conn.execute(
                    "UPDATE players SET fatigue = MAX(0, fatigue - ?) WHERE id = ?",
                    (it["fatigue_recover"], self._my_id)
                )
                conn.commit()
            pa = _load_player(self._my_id)
            self._fill_panel("a", pa, self._my_condition, self._my_fatigue)

        # 아이템 소진 (player_items 1개 삭제)
        with get_connection() as conn:
            conn.execute("DELETE FROM player_items WHERE id = ?", (it["pi_id"],))
            conn.commit()

        self.btn_item.setEnabled(False)

    # ── 다음 버튼 ────────────────────────────────────────────
    def _on_next(self):
        if self._match_over:
            self._finalize()
        else:
            self._start_next_set()

    # ── 경기 종료 처리 ───────────────────────────────────────
    def _finalize(self):
        outcome = finalize_match(
            self._my_id, self._opp_id,
            self._all_sets, self._map_id,
            self._my_condition, self._opp_condition,
            award_gold=True,
        )
        self.sig_match_done.emit(outcome)
