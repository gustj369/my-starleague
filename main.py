"""마이 스타리그 — 앱 진입점 (PRD v9)"""
import json
import sys
import os
from enum import IntEnum

APP_VERSION = "v1.0.0"
TOURNAMENT_START_SNAPSHOT_KEY = "tournament_start_player_snapshot"
TOURNAMENT_START_GOLD_KEY = "tournament_start_gold"
TOURNAMENT_HAD_UPSET_KEY = "tournament_had_upset"

if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect,
    QMessageBox
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve

from database.db import (
    get_gold, get_connection, set_active_slot,
    get_current_tournament_id, set_current_tournament_id,
    get_game_summary, save_tournament_result,
    migrate_db, set_gold, add_gold,
    check_and_earn_achievements, check_sponsor_mission, generate_sponsor_mission,
    get_sponsor_mission,
)
from database.slot_manager import delete_slot
from core.tournament import (
    create_tournament, get_tournament, get_my_pending_match,
    complete_my_match, is_round_complete, advance_round,
    is_my_player_alive, get_elimination_round,
    get_latest_completed_tournament, ROUNDS, ROUND_REWARDS
)

from core.season_events import generate_events, apply_gold_events, store_fatigue_events, apply_pending_fatigue_events
from core.growth_events import generate_growth_event, apply_growth_event
from ui.season_news_dialog import SeasonNewsDialog
from ui.styles import MAIN_QSS
from ui.font_loader import load_fonts
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
from ui.ranking_screen import RankingScreen
from ui.onboarding_dialog import OnboardingDialog
from ui.settings_screen import SettingsScreen
from ui.achievements_screen import AchievementsScreen
from ui.splash_screen import show_splash

# 화면 인덱스 (IntEnum: 정수 연산·비교 완전 호환, 오타/순서 오류 방지)
class Screen(IntEnum):
    SLOT         = 0   # 슬롯 선택 (시작 화면)
    MENU         = 1
    SELECT       = 2
    BRACKET      = 3
    PREP         = 4
    SIMULATION   = 5
    RESULT       = 6
    FINAL        = 7
    PLAYERS      = 8
    SHOP         = 9
    HISTORY      = 10
    RANKING      = 11
    SETTINGS     = 12
    ACHIEVEMENTS = 13


class NavBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(
            "QWidget { background-color: #FFFFFF; border-bottom: 1px solid #E9ECEF; }"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        logo = QLabel("★ LEGEND LEAGUE")
        logo.setStyleSheet(
            "color: #5B6CF6; font-weight: bold; font-size: 13px; background: transparent;"
        )
        lay.addWidget(logo)
        lay.addStretch()

        self.lbl_gold = QLabel("💰 0 G")
        self.lbl_gold.setStyleSheet(
            "color: #F59E0B; font-size: 12px; background: transparent;"
        )
        lay.addWidget(self.lbl_gold)
        lay.addSpacing(20)

        self._nav_cb = None
        for label, idx in [
            ("선수 관리", Screen.PLAYERS),
            ("아이템 상점", Screen.SHOP),
            ("대결 기록", Screen.HISTORY),
            ("선수 랭킹", Screen.RANKING),
            ("🏆 도전과제", Screen.ACHIEVEMENTS),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setProperty("_idx", idx)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #212529;
                    border: 1px solid #E9ECEF; border-radius: 8px;
                    padding: 0 10px; font-size: 12px;
                }
                QPushButton:hover { color: #5B6CF6; border-color: #5B6CF6; background: #EEF2FF; }
            """)
            btn.clicked.connect(lambda _, i=idx: self._nav_cb and self._nav_cb(i))
            lay.addWidget(btn)

        lay.addSpacing(4)
        # 설정 버튼
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setFixedSize(30, 30)
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background: transparent; color: #868E96;
                border: 1px solid #E9ECEF; border-radius: 8px;
                font-size: 14px; padding: 0;
            }
            QPushButton:hover { color: #5B6CF6; border-color: #5B6CF6; background: #EEF2FF; }
        """)
        self.btn_settings.clicked.connect(
            lambda: self._nav_cb and self._nav_cb(Screen.SETTINGS)
        )
        lay.addWidget(self.btn_settings)

        # 도움말 버튼
        self.btn_help = QPushButton("?")
        self.btn_help.setFixedSize(30, 30)
        self.btn_help.setStyleSheet("""
            QPushButton {
                background: transparent; color: #868E96;
                border: 1px solid #E9ECEF; border-radius: 8px;
                font-size: 14px; font-weight: bold; padding: 0;
            }
            QPushButton:hover { color: #5B6CF6; border-color: #5B6CF6; background: #EEF2FF; }
        """)
        self._help_cb = None
        self.btn_help.clicked.connect(lambda: self._help_cb and self._help_cb())
        lay.addWidget(self.btn_help)

    def set_nav_callback(self, cb):
        self._nav_cb = cb

    def set_help_callback(self, cb):
        self._help_cb = cb

    def update_gold(self):
        self.lbl_gold.setText(f"💰 {get_gold():,} G")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("레전드 리그  —  2026 시즌")
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
        self.s_players      = PlayerManagerScreen()
        self.s_shop         = ShopScreen()
        self.s_history      = HistoryScreen()
        self.s_ranking      = RankingScreen()
        self.s_settings     = SettingsScreen()
        self.s_achievements = AchievementsScreen()

        for s in [self.s_slot, self.s_menu, self.s_select, self.s_bracket,
                  self.s_prep, self.s_simulation, self.s_result, self.s_final,
                  self.s_players, self.s_shop, self.s_history, self.s_ranking,
                  self.s_settings, self.s_achievements]:
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
        self.s_select.sig_back.connect(lambda: self._go(Screen.MENU))

        self.s_bracket.sig_prep_match.connect(self._on_prep_match)
        self.s_bracket.sig_back.connect(lambda: self._go(Screen.MENU))

        self.s_prep.sig_start.connect(self._on_match_start)
        self.s_prep.sig_back.connect(lambda: self._go(Screen.BRACKET))

        self.s_simulation.sig_match_done.connect(self._on_simulation_done)

        self.s_result.sig_continue.connect(self._on_result_continue)

        self.s_final.sig_restart.connect(self._restart)
        self.s_final.sig_exit.connect(self.close)

        self.s_players.sig_back.connect(self._sub_back)
        self.s_shop.sig_back.connect(self._sub_back)
        self.s_history.sig_back.connect(self._sub_back)
        self.s_ranking.sig_back.connect(self._sub_back)
        self.s_settings.sig_back.connect(self._sub_back)
        self.s_achievements.sig_back.connect(self._sub_back)

        # 내부 상태
        self._tid: int | None = None
        self._my_id: int | None = None
        self._snap_a: dict | None = None
        self._snap_b: dict | None = None
        self._gold_at_start: int = 0
        self._player_snap_start: dict | None = None
        self._pre_nav_idx: int = Screen.BRACKET
        self._pending_tm_id: int = 0
        self._pending_round: str = ""
        self._had_upset_this_tournament: bool = False
        self._final_a_wins: int = 0
        self._final_b_wins: int = 0

        # ── 화면 전환 fade 애니메이션 ─────────────────────────
        self._opacity_effect = QGraphicsOpacityEffect(self.stack)
        self.stack.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(1.0)
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(180)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._pending_go_idx: int | None = None
        self._fade_anim.finished.connect(self._on_fade_done)

        self.navbar.setVisible(False)
        self.navbar.set_help_callback(self._show_help)
        self.stack.setCurrentIndex(Screen.SLOT)  # 첫 화면은 직접 세팅 (fade 없음)

    # ── 화면 전환 ──────────────────────────────────────────────
    def _go(self, idx: int):
        if self.stack.currentIndex() == idx:
            return
        # 페이드 아웃 → 전환 → 페이드 인
        self._pending_go_idx = idx
        self._fade_anim.stop()
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()
        if idx not in (Screen.SLOT,):
            self.navbar.update_gold()

    def _on_fade_done(self):
        if self._pending_go_idx is None:
            return
        idx = self._pending_go_idx
        self._pending_go_idx = None
        if self._fade_anim.startValue() == 1.0:
            # 페이드 아웃 완료 → 화면 전환 후 페이드 인
            self.stack.setCurrentIndex(idx)
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.start()

    # 내비게이션 서브 화면 인덱스 집합 (이 화면에서 누르면 _pre_nav_idx 갱신 X)
    _NAV_SCREENS = frozenset({
        Screen.PLAYERS, Screen.SHOP, Screen.HISTORY, Screen.RANKING,
        Screen.SETTINGS, Screen.ACHIEVEMENTS,
    })

    def _nav_to(self, idx: int):
        current = self.stack.currentIndex()
        # 게임 화면(브라켓 등)일 때만 저장 — 이미 서브 화면이면 덮어쓰지 않음
        if current not in self._NAV_SCREENS:
            self._pre_nav_idx = current
        if idx == Screen.PLAYERS:
            self.s_players.refresh()
        elif idx == Screen.SHOP:
            self.s_shop.refresh()
        elif idx == Screen.HISTORY:
            self.s_history.refresh()
        elif idx == Screen.RANKING:
            self.s_ranking.refresh()
        elif idx == Screen.SETTINGS:
            self.s_settings.refresh()
        elif idx == Screen.ACHIEVEMENTS:
            self.s_achievements.refresh()
        self._go(idx)

    def _sub_back(self):
        self._go(self._pre_nav_idx)
        self.navbar.update_gold()

    def _show_help(self):
        dlg = OnboardingDialog(self)
        dlg.exec()

    def _to_slot_select(self):
        self.navbar.setVisible(False)
        self.s_slot.refresh()
        self._go(Screen.SLOT)

    # ── 슬롯 선택 ────────────────────────────────────────────
    def _on_slot_new_game(self, slot_idx: int):
        """슬롯 초기화 + 새 게임 시작 → 온보딩 → 선수 선택"""
        from database.seed_data import seed
        delete_slot(slot_idx)
        set_active_slot(slot_idx)
        migrate_db()
        seed()         # 새 슬롯: gold=500, 선수 초기화
        self.navbar.setVisible(True)
        # 첫 플레이 온보딩 안내
        dlg = OnboardingDialog(self)
        dlg.exec()
        self.s_select.refresh()
        self._go(Screen.SELECT)

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
                self._restore_active_tournament_context(tid, t['my_player_id'])
                if not is_my_player_alive(self._tid) or is_round_complete(self._tid):
                    self._on_result_continue()
                else:
                    self.s_bracket.load_tournament(self._tid, self._my_id)
                    self._go(Screen.BRACKET)
                return

        # 진행 중 토너먼트 없음 → 메인 메뉴로
        self.s_menu.refresh()
        self._go(Screen.MENU)

    # ── 메인 메뉴 ──────────────────────────────────────────────
    def _new_tournament(self):
        """메인 메뉴 '새 토너먼트' — 골드 유지, 시즌 뉴스 표시 후 선수 선택"""
        events = generate_events(2)
        apply_gold_events(events)
        store_fatigue_events(events)
        dlg = SeasonNewsDialog(events, self)
        dlg.exec()
        self.s_select.refresh()
        self._go(Screen.SELECT)

    def _load_game(self):
        tid = get_current_tournament_id()
        if tid:
            t = get_tournament(tid)
            if t and t['status'] == '진행중':
                self._restore_active_tournament_context(tid, t['my_player_id'])
                if not is_my_player_alive(self._tid) or is_round_complete(self._tid):
                    self._on_result_continue()
                else:
                    self.s_bracket.load_tournament(self._tid, self._my_id)
                    self._go(Screen.BRACKET)
                return
        # 진행 중 토너먼트 없음 → 선수 선택
        self.s_select.refresh()
        self._go(Screen.SELECT)

    # ── 선수 선택 → 토너먼트 생성 ─────────────────────────────
    def _restore_active_tournament_context(self, tid: int, my_player_id: int):
        self._tid = tid
        self._my_id = my_player_id
        data, fallback_snap, final, had_upset = self._load_tournament_restore_data(
            tid, my_player_id
        )

        self._player_snap_start = self._restore_player_start_snapshot(
            data, fallback_snap
        )
        self._gold_at_start = self._restore_tournament_start_gold(data)
        self._had_upset_this_tournament = self._restore_tournament_had_upset(
            data, had_upset
        )
        self._restore_final_score(final, my_player_id)

    def _load_tournament_restore_data(self, tid: int, my_player_id: int):
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT key, value FROM game_state WHERE key IN (?,?,?)",
                (
                    TOURNAMENT_START_SNAPSHOT_KEY,
                    TOURNAMENT_START_GOLD_KEY,
                    TOURNAMENT_HAD_UPSET_KEY,
                ),
            ).fetchall()
            data = {row["key"]: row["value"] for row in rows}
            row = conn.execute(
                "SELECT * FROM players WHERE id=?", (my_player_id,)
            ).fetchone()
            fallback_snap = dict(row) if row else {}
            final = conn.execute(
                """SELECT player_a_id, player_b_id, a_wins, b_wins
                   FROM tournament_matches
                   WHERE tournament_id=? AND round=? AND is_my_match=1
                     AND status='completed'
                   ORDER BY id DESC LIMIT 1""",
                (tid, ROUNDS[-1]),
            ).fetchone()
            had_upset = conn.execute(
                """SELECT 1 FROM tournament_matches
                   WHERE tournament_id=? AND is_my_match=1
                     AND status='completed' AND is_upset=1
                   LIMIT 1""",
                (tid,),
            ).fetchone()
        return data, fallback_snap, final, had_upset

    def _restore_player_start_snapshot(self, data: dict, fallback_snap: dict) -> dict:
        try:
            snap = json.loads(data.get(TOURNAMENT_START_SNAPSHOT_KEY, ""))
        except (TypeError, ValueError, json.JSONDecodeError):
            return fallback_snap
        return snap if isinstance(snap, dict) else fallback_snap

    def _restore_tournament_start_gold(self, data: dict) -> int:
        try:
            return int(data.get(TOURNAMENT_START_GOLD_KEY, get_gold()))
        except (TypeError, ValueError):
            return get_gold()

    def _restore_tournament_had_upset(self, data: dict, had_upset) -> bool:
        value = str(data.get(TOURNAMENT_HAD_UPSET_KEY, "")).strip().lower()
        return value in ("1", "true", "yes") or had_upset is not None

    def _restore_final_score(self, final, my_player_id: int):
        self._final_a_wins = 0
        self._final_b_wins = 0
        if final:
            if final["player_a_id"] == my_player_id:
                self._final_a_wins = final["a_wins"]
                self._final_b_wins = final["b_wins"]
            else:
                self._final_a_wins = final["b_wins"]
                self._final_b_wins = final["a_wins"]

    def _save_tournament_start_context(self):
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
                (TOURNAMENT_START_SNAPSHOT_KEY, json.dumps(self._player_snap_start)),
            )
            conn.execute(
                "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
                (TOURNAMENT_START_GOLD_KEY, str(self._gold_at_start)),
            )
            conn.execute(
                "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, '0')",
                (TOURNAMENT_HAD_UPSET_KEY,),
            )
            conn.commit()

    def _save_tournament_upset_state(self):
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO game_state (key, value) VALUES (?, ?)",
                (TOURNAMENT_HAD_UPSET_KEY, "1" if self._had_upset_this_tournament else "0"),
            )
            conn.commit()

    def _on_player_selected(self, my_id: int):
        self._my_id = my_id
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM players WHERE id=?", (my_id,)).fetchone()
            self._player_snap_start = dict(row) if row else {}
        self._gold_at_start = get_gold()
        self._had_upset_this_tournament = False
        self._final_a_wins = 0
        self._final_b_wins = 0
        self._save_tournament_start_context()
        self._tid = create_tournament(my_id)
        apply_pending_fatigue_events()

        # 스폰서 미션 생성 + 안내
        generate_sponsor_mission()
        mission = get_sponsor_mission()
        if mission:
            QMessageBox.information(
                self, "📋 스폰서 미션",
                f"미션: {mission['desc']}\n보상: +{mission['reward']} G\n\n토너먼트에서 목표를 달성하세요!"
            )

        self.s_bracket.load_tournament(self._tid, self._my_id)
        self._go(Screen.BRACKET)

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
        self._go(Screen.PREP)

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
        self._go(Screen.SIMULATION)

    # ── simulation → result ───────────────────────────────────
    def _on_simulation_done(self, outcome):
        my_id = self._my_id
        tm_id = self.s_simulation.tm_id
        round_name = self.s_simulation.round_name

        complete_my_match(
            tm_id, outcome.winner_id,
            self.s_simulation.map_id,
            round_name=round_name,
            my_player_id=my_id,
            a_wins=outcome.a_wins,
            b_wins=outcome.b_wins,
            is_upset=outcome.is_upset,
        )

        # 이변 발생 여부 추적
        if outcome.is_upset:
            self._had_upset_this_tournament = True
            self._save_tournament_upset_state()

        # 결승전 스코어 기록 (완벽한 결승 업적용)
        is_my_win = (outcome.winner_id == my_id)
        if round_name == "결승":
            if is_my_win:
                self._final_a_wins = outcome.a_wins
                self._final_b_wins = outcome.b_wins
            else:
                self._final_a_wins = outcome.b_wins
                self._final_b_wins = outcome.a_wins

        self.s_result.set_button_label(
            "▶  계속하기 (대진표)" if is_my_win else "▶  리그 종료"
        )
        self.s_result.show_result(outcome, self._snap_a, self._snap_b)
        self.navbar.update_gold()
        self._go(Screen.RESULT)

    # ── 결과 → 다음 단계 ──────────────────────────────────────
    def _on_result_continue(self):
        if self._tid is None:
            self._go(Screen.BRACKET)
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
        self._go(Screen.BRACKET)

    # ── 최종 결과 ─────────────────────────────────────────────
    def _show_final(self):
        achievement = get_elimination_round(self._tid)

        # 스폰서 미션 결과 처리
        sponsor_reward = check_sponsor_mission(
            achievement, had_upset=self._had_upset_this_tournament
        )
        if sponsor_reward > 0:
            add_gold(sponsor_reward)
            QMessageBox.information(
                self, "📋 스폰서 미션 달성!",
                f"미션을 성공했습니다!\n보상 +{sponsor_reward} G 획득!"
            )
            self.navbar.update_gold()

        growth = []
        if self._my_id:
            growth = generate_growth_event(self._my_id, achievement)
            apply_growth_event(self._my_id, growth)

        gold_earned = get_gold() - self._gold_at_start
        self.s_final.show_result(
            achievement, self._my_id, self._player_snap_start, gold_earned,
            tournament_id=self._tid
        )
        self.s_final.show_growth(growth)
        save_tournament_result(achievement, gold_earned)

        # 도전과제 확인
        if self._my_id:
            grade_before = (self._player_snap_start or {}).get("grade", "")
            newly_earned = check_and_earn_achievements(
                self._my_id,
                achievement,
                player_grade_before=grade_before,
                final_score=(self._final_a_wins, self._final_b_wins),
                had_upset_in_tournament=self._had_upset_this_tournament,
            )
            if newly_earned:
                icons = {"첫 우승": "🏆", "베테랑": "🎖", "레전드": "👑"}
                msg = "\n".join(f"  {a}" for a in newly_earned)
                QMessageBox.information(
                    self, "🏆 도전과제 달성!",
                    f"새로운 도전과제를 달성했습니다!\n\n{msg}"
                )

        set_current_tournament_id(None)
        self.s_menu.refresh()
        self.navbar.update_gold()  # 스폰서 보상·성장 이벤트 후 최종 골드 갱신 보장
        self._go(Screen.FINAL)

    # ── 다시 시작 ─────────────────────────────────────────────
    def _restart(self):
        self._tid   = None
        self._my_id = None
        self.s_menu.refresh()
        self._go(Screen.MENU)

    # ── 종료 확인 다이얼로그 ──────────────────────────────────
    def closeEvent(self, event):
        """경기 진행 중일 때 종료 전 확인 다이얼로그 표시."""
        current_idx = self.stack.currentIndex()
        # 슬롯 선택·메인 메뉴·최종 결과·설정·업적 화면은 즉시 종료 허용
        if current_idx in (Screen.SLOT, Screen.MENU, Screen.FINAL, Screen.SETTINGS, Screen.ACHIEVEMENTS):
            event.accept()
            return
        reply = QMessageBox.question(
            self,
            "게임 종료",
            "게임을 종료하시겠습니까?\n진행 중인 데이터는 자동 저장됩니다.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


def _write_error_log(text: str):
    """EXE·개발 양쪽 환경에서 에러를 파일에 기록."""
    try:
        import pathlib, datetime
        if getattr(sys, 'frozen', False):
            log_dir = pathlib.Path(os.getenv('APPDATA', '')) / '마이스타리그'
        else:
            log_dir = pathlib.Path(__file__).parent / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / 'error.log'
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n[{datetime.datetime.now()}]\n")
            f.write(text)
            f.write("\n")
    except Exception:
        pass


def _excepthook(exc_type, exc_value, exc_tb):
    """전역 예외 핸들러 — 모든 미처리 예외를 파일에 기록."""
    import traceback
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _write_error_log(text)
    # 원래 핸들러 호출 (콘솔에도 출력)
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def main():
    # 전역 예외 핸들러 등록
    sys.excepthook = _excepthook

    import traceback
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("레전드 리그")
        app.setApplicationVersion(APP_VERSION)
        load_fonts()   # Press Start 2P, Orbitron 등록
        app.setStyleSheet(MAIN_QSS)

        # 스플래시 화면 표시 (APP_VERSION 전달 — splash_screen.py 에 중복 정의 없음)
        splash = show_splash(app, version=APP_VERSION)

        win = MainWindow()
        win.show()

        # 스플래시 종료 (메인 윈도우 표시 후)
        splash.finish(win)

        sys.exit(app.exec())
    except Exception as exc:
        import traceback
        text = traceback.format_exc()
        _write_error_log(text)
        raise


if __name__ == "__main__":
    main()
