"""마이 스타리그 — 앱 진입점 (PRD v8 5슬롯 세이브)"""
import sys
import os

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt

from database.db import (
    get_gold, get_connection, set_active_slot,
    get_current_tournament_id, set_current_tournament_id,
    get_game_summary, save_tournament_result,
    migrate_db, set_gold
)
from database.slot_manager import delete_slot
from core.tournament import (
    create_tournament, get_tournament, get_my_pending_match,
    complete_my_match, is_round_complete, advance_round,
    is_my_player_alive, get_elimination_round,
    get_latest_completed_tournament, ROUNDS, ROUND_REWARDS
)

from ui.styles import MAIN_QSS
from ui.slot_select_screen import SlotSelectScreen
from ui.main_menu import MainMenuScreen
from ui.player_select import PlayerSelectScreen
from ui.bracket_screen import BracketScreen
from ui.match_prep import MatchPrepScreen
from ui.simulation_screen import SimulationScreen
from ui.result_screen import ResultScreen
from ui.final_result import FinalResultScreen
from ui.player_manager import PlayerManagerScreen
from ui.shop_screen import ShopScreen
from ui.history_screen import HistoryScreen

# 화면 인덱스
IDX_SLOT       = 0   # 슬롯 선택 (시작 화면)
IDX_MENU       = 1
IDX_SELECT     = 2
IDX_BRACKET    = 3
IDX_PREP       = 4
IDX_SIMULATION = 5
IDX_RESULT     = 6
IDX_FINAL      = 7
IDX_PLAYERS    = 8
IDX_SHOP       = 9
IDX_HISTORY    = 10


class NavBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(
            "QWidget { background-color: #060c18; border-bottom: 1px solid #1e3a5f; }"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        logo = QLabel("★ MY STARLEAGUE")
        logo.setStyleSheet(
            "color: #ffd700; font-weight: bold; font-size: 13px; background: transparent;"
        )
        lay.addWidget(logo)
        lay.addStretch()

        self.lbl_gold = QLabel("Gold: 0 G")
        self.lbl_gold.setStyleSheet(
            "color: #ffd700; font-size: 12px; background: transparent;"
        )
        lay.addWidget(self.lbl_gold)
        lay.addSpacing(20)

        self._nav_cb = None
        for label, idx in [
            ("선수 관리", IDX_PLAYERS),
            ("아이템 상점", IDX_SHOP),
            ("대결 기록", IDX_HISTORY),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setProperty("_idx", idx)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #7a9ab8;
                    border: 1px solid #1e3a5f; border-radius: 3px;
                    padding: 0 10px; font-size: 12px;
                }
                QPushButton:hover { color: #4fc3f7; border-color: #4fc3f7; background: #0d1525; }
            """)
            btn.clicked.connect(lambda _, i=idx: self._nav_cb and self._nav_cb(i))
            lay.addWidget(btn)

    def set_nav_callback(self, cb):
        self._nav_cb = cb

    def update_gold(self):
        self.lbl_gold.setText(f"Gold: {get_gold()} G")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("마이 스타리그  —  2012 시즌")
        self.setMinimumSize(1100, 760)
        self.resize(1240, 840)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.navbar = NavBar()
        self.navbar.set_nav_callback(self._nav_to)
        root.addWidget(self.navbar)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # 화면 생성 (인덱스 순서대로 addWidget)
        self.s_slot       = SlotSelectScreen()
        self.s_menu       = MainMenuScreen()
        self.s_select     = PlayerSelectScreen()
        self.s_bracket    = BracketScreen()
        self.s_prep       = MatchPrepScreen()
        self.s_simulation = SimulationScreen()
        self.s_result     = ResultScreen()
        self.s_final      = FinalResultScreen()
        self.s_players    = PlayerManagerScreen()
        self.s_shop       = ShopScreen()
        self.s_history    = HistoryScreen()

        for s in [self.s_slot, self.s_menu, self.s_select, self.s_bracket,
                  self.s_prep, self.s_simulation, self.s_result, self.s_final,
                  self.s_players, self.s_shop, self.s_history]:
            self.stack.addWidget(s)

        # ── 시그널 연결 ────────────────────────────────────────
        # 슬롯 선택
        self.s_slot.sig_new_game.connect(self._on_slot_new_game)
        self.s_slot.sig_continue.connect(self._on_slot_continue)

        # 메인 메뉴
        self.s_menu.sig_new_game.connect(self._new_tournament)
        self.s_menu.sig_load_game.connect(self._load_game)
        self.s_menu.sig_back.connect(self._to_slot_select)
        self.s_menu.sig_exit.connect(self.close)

        self.s_select.sig_confirm.connect(self._on_player_selected)
        self.s_select.sig_back.connect(lambda: self._go(IDX_MENU))

        self.s_bracket.sig_prep_match.connect(self._on_prep_match)
        self.s_bracket.sig_back.connect(lambda: self._go(IDX_MENU))

        self.s_prep.sig_start.connect(self._on_match_start)
        self.s_prep.sig_back.connect(lambda: self._go(IDX_BRACKET))

        self.s_simulation.sig_match_done.connect(self._on_simulation_done)

        self.s_result.sig_continue.connect(self._on_result_continue)

        self.s_final.sig_restart.connect(self._restart)
        self.s_final.sig_exit.connect(self.close)

        self.s_players.sig_back.connect(self._sub_back)
        self.s_shop.sig_back.connect(self._sub_back)
        self.s_history.sig_back.connect(self._sub_back)

        # 내부 상태
        self._tid: int | None = None
        self._my_id: int | None = None
        self._snap_a: dict | None = None
        self._snap_b: dict | None = None
        self._gold_at_start: int = 0
        self._player_snap_start: dict | None = None
        self._pre_nav_idx: int = IDX_BRACKET
        self._pending_tm_id: int = 0
        self._pending_round: str = ""

        self.navbar.setVisible(False)
        self._go(IDX_SLOT)

    # ── 화면 전환 ──────────────────────────────────────────────
    def _go(self, idx: int):
        self.stack.setCurrentIndex(idx)
        if idx not in (IDX_SLOT,):
            self.navbar.update_gold()

    def _nav_to(self, idx: int):
        self._pre_nav_idx = self.stack.currentIndex()
        if idx == IDX_PLAYERS:
            self.s_players.refresh()
        elif idx == IDX_SHOP:
            self.s_shop.refresh()
        elif idx == IDX_HISTORY:
            self.s_history.refresh()
        self._go(idx)

    def _sub_back(self):
        self._go(self._pre_nav_idx)
        self.navbar.update_gold()

    def _to_slot_select(self):
        self.navbar.setVisible(False)
        self.s_slot.refresh()
        self._go(IDX_SLOT)

    # ── 슬롯 선택 ────────────────────────────────────────────
    def _on_slot_new_game(self, slot_idx: int):
        """슬롯 초기화 + 새 게임 시작 → 선수 선택으로 직행"""
        from database.seed_data import seed
        delete_slot(slot_idx)
        set_active_slot(slot_idx)
        migrate_db()
        seed()         # 새 슬롯: gold=500, 선수 초기화
        self.navbar.setVisible(True)
        self.s_select.refresh()
        self._go(IDX_SELECT)

    def _on_slot_continue(self, slot_idx: int):
        """기존 슬롯 불러오기 → 진행 중이면 대진표, 아니면 메인 메뉴"""
        from database.seed_data import seed
        set_active_slot(slot_idx)
        migrate_db()
        seed()         # 버전 확인만, 데이터 유지
        self.navbar.setVisible(True)

        tid = get_current_tournament_id()
        if tid:
            t = get_tournament(tid)
            if t and t['status'] == '진행중':
                self._tid   = tid
                self._my_id = t['my_player_id']
                self.s_bracket.load_tournament(self._tid, self._my_id)
                self._go(IDX_BRACKET)
                return

        # 진행 중 토너먼트 없음 → 메인 메뉴로
        self.s_menu.refresh()
        self._go(IDX_MENU)

    # ── 메인 메뉴 ──────────────────────────────────────────────
    def _new_tournament(self):
        """메인 메뉴 '새 토너먼트' — 골드 유지, 선수 선택으로"""
        self.s_select.refresh()
        self._go(IDX_SELECT)

    def _load_game(self):
        tid = get_current_tournament_id()
        if tid:
            t = get_tournament(tid)
            if t and t['status'] == '진행중':
                self._tid   = tid
                self._my_id = t['my_player_id']
                self.s_bracket.load_tournament(self._tid, self._my_id)
                self._go(IDX_BRACKET)
                return
        # 진행 중 토너먼트 없음 → 선수 선택
        self.s_select.refresh()
        self._go(IDX_SELECT)

    # ── 선수 선택 → 토너먼트 생성 ─────────────────────────────
    def _on_player_selected(self, my_id: int):
        self._my_id = my_id
        with get_connection() as conn:
            self._player_snap_start = dict(
                conn.execute("SELECT * FROM players WHERE id=?", (my_id,)).fetchone()
            )
        self._gold_at_start = get_gold()
        self._tid = create_tournament(my_id)
        self.s_bracket.load_tournament(self._tid, self._my_id)
        self._go(IDX_BRACKET)

    # ── 경기 준비 ──────────────────────────────────────────────
    def _on_prep_match(self):
        m = get_my_pending_match(self._tid)
        if not m:
            return
        t = get_tournament(self._tid)
        opp_id = m['player_b_id'] if m['player_a_id'] == self._my_id else m['player_a_id']
        self._pending_tm_id = m['id']
        self._pending_round = t['current_round']
        self.s_prep.load_match(self._my_id, opp_id, m['id'], t['current_round'])
        self._go(IDX_PREP)

    # ── match_prep → simulation ───────────────────────────────
    def _on_match_start(self, my_id: int, opp_id: int, map_id: int,
                        tm_id: int, my_condition: str = "보통"):
        with get_connection() as conn:
            self._snap_a = dict(conn.execute(
                "SELECT * FROM players WHERE id=?", (my_id,)).fetchone())
            self._snap_b = dict(conn.execute(
                "SELECT * FROM players WHERE id=?", (opp_id,)).fetchone())

        t = get_tournament(self._tid)
        round_name = t['current_round'] if t else self._pending_round

        self.s_simulation.load_match(
            my_id, opp_id, map_id, my_condition, tm_id, round_name
        )
        self._go(IDX_SIMULATION)

    # ── simulation → result ───────────────────────────────────
    def _on_simulation_done(self, outcome):
        my_id = self._my_id
        tm_id = self.s_simulation._tm_id
        round_name = self.s_simulation._round_name

        complete_my_match(
            tm_id, outcome.winner_id,
            self.s_simulation._map_id,
            round_name=round_name,
            my_player_id=my_id,
            a_wins=outcome.a_wins,
            b_wins=outcome.b_wins,
        )

        is_my_win = (outcome.winner_id == my_id)
        self.s_result.set_button_label(
            "▶  계속하기 (대진표)" if is_my_win else "▶  리그 종료"
        )
        self.s_result.show_result(outcome, self._snap_a, self._snap_b)
        self.navbar.update_gold()
        self._go(IDX_RESULT)

    # ── 결과 → 다음 단계 ──────────────────────────────────────
    def _on_result_continue(self):
        if self._tid is None:
            self._go(IDX_BRACKET)
            return

        if not is_my_player_alive(self._tid):
            self._show_final()
            return

        if is_round_complete(self._tid):
            new_round = advance_round(self._tid)
            if new_round is None:
                self._show_final()
                return

        self.s_bracket.load_tournament(self._tid, self._my_id)
        self.navbar.update_gold()
        self._go(IDX_BRACKET)

    # ── 최종 결과 ─────────────────────────────────────────────
    def _show_final(self):
        achievement = get_elimination_round(self._tid)
        gold_earned = get_gold() - self._gold_at_start
        self.s_final.show_result(
            achievement, self._my_id, self._player_snap_start, gold_earned
        )
        save_tournament_result(achievement, gold_earned)
        set_current_tournament_id(None)
        self.s_menu.refresh()
        self._go(IDX_FINAL)

    # ── 다시 시작 ─────────────────────────────────────────────
    def _restart(self):
        self._tid   = None
        self._my_id = None
        self.s_menu.refresh()
        self._go(IDX_MENU)


def main():
    # DB 초기화는 슬롯 선택 후에 수행 (슬롯 선택 전엔 DB 경로 미확정)
    app = QApplication(sys.argv)
    app.setApplicationName("마이 스타리그")
    app.setStyleSheet(MAIN_QSS)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
