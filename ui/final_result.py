"""최종 결과 화면 — 리그 종료 후 요약"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from database.db import get_connection, get_gold
from ui.widgets import make_separator
from ui.styles import GRADE_STYLE, RACE_COLORS, RACE_DISPLAY

STAT_KEYS   = ["control", "attack", "defense", "supply", "strategy", "sense"]
STAT_LABELS = ["컨트롤", "공격력", "수비력", "물량", "전략", "센스"]

ACHIEVEMENT_COLOR = {
    "우승":     "#F59E0B",
    "준우승":   "#868E96",
    "4강 탈락": "#5B6CF6",
    "8강 탈락": "#51CF66",
    "16강 탈락":"#FF6B6B",
}


class FinalResultScreen(QWidget):
    sig_restart = pyqtSignal()
    sig_exit    = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._snap: dict | None = None   # 토너먼트 시작 전 스냅샷
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 30)
        root.setSpacing(16)

        # 달성 표시
        self.lbl_achieve = QLabel("")
        self.lbl_achieve.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_achieve.setStyleSheet(
            "color: #F59E0B; font-size: 36px; font-weight: bold; background: transparent;"
        )

        self.lbl_player = QLabel("")
        self.lbl_player.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_player.setStyleSheet(
            "color: #868E96; font-size: 18px; background: transparent;"
        )

        # 능력치 비교 테이블
        tbl_label = QLabel("능력치 변동 (토너먼트 전 → 후)")
        tbl_label.setStyleSheet(
            "color: #5B6CF6; font-weight: bold; font-size: 13px; background: transparent;"
        )

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["능력치", "시작", "현재", "변동"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setMaximumHeight(260)
        for c in range(3):
            self.table.setColumnWidth(c, 80)

        # 등급 변동
        self.lbl_grade = QLabel("")
        self.lbl_grade.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_grade.setStyleSheet("font-size: 20px; background: transparent;")

        # 골드
        self.lbl_gold = QLabel("")
        self.lbl_gold.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gold.setStyleSheet(
            "color: #F59E0B; font-weight: bold; font-size: 15px; background: transparent;"
        )

        # 버튼
        btn_row = QHBoxLayout()
        self.btn_restart = QPushButton("▶  다시 시작")
        self.btn_restart.setProperty("class", "primary")
        self.btn_restart.setMinimumHeight(46)
        self.btn_restart.clicked.connect(self.sig_restart)

        self.btn_exit = QPushButton("종료")
        self.btn_exit.setProperty("class", "danger")
        self.btn_exit.setMinimumHeight(46)
        self.btn_exit.clicked.connect(self.sig_exit)

        btn_row.addStretch()
        btn_row.addWidget(self.btn_restart)
        btn_row.addSpacing(20)
        btn_row.addWidget(self.btn_exit)
        btn_row.addStretch()

        # 토너먼트 경로 섹션
        path_lbl_title = QLabel("토너먼트 경로")
        path_lbl_title.setStyleSheet(
            "color: #5B6CF6; font-weight: bold; font-size: 13px; background: transparent;"
        )
        self.lbl_path = QLabel("—")
        self.lbl_path.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_path.setWordWrap(True)
        self.lbl_path.setStyleSheet(
            "color: #868E96; font-size: 13px; background: transparent;"
        )

        # 성장 이벤트 표시 라벨
        self.lbl_growth = QLabel("")
        self.lbl_growth.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_growth.setWordWrap(True)
        self.lbl_growth.setStyleSheet(
            "color: #5B6CF6; font-size: 13px; font-weight: bold; background: #EEF2FF; "
            "border: 1px solid #C5C8FF; border-radius: 6px; padding: 8px;"
        )
        self.lbl_growth.setVisible(False)

        root.addWidget(self.lbl_achieve)
        root.addWidget(self.lbl_player)
        root.addWidget(make_separator())
        root.addWidget(path_lbl_title)
        root.addWidget(self.lbl_path)
        root.addWidget(make_separator())
        root.addWidget(tbl_label)
        root.addWidget(self.table)
        root.addWidget(self.lbl_grade)
        root.addWidget(make_separator())
        root.addWidget(self.lbl_gold)
        root.addWidget(self.lbl_growth)
        root.addLayout(btn_row)

    # ──────────────────────────────────────────
    def show_result(self, achievement: str, my_player_id: int,
                    snap_before: dict, gold_earned: int,
                    tournament_id: int | None = None):
        """
        achievement: '우승', '준우승', '4강 탈락' 등
        snap_before: 토너먼트 시작 직전 선수 스냅샷
        """
        self._snap = snap_before

        color = ACHIEVEMENT_COLOR.get(achievement, "#868E96")
        # 우승 시 더 강렬한 축하 연출
        if achievement == "우승":
            self.lbl_achieve.setText("🏆  우승!  🏆")
            self.lbl_achieve.setStyleSheet(
                f"color: {color}; font-size: 42px; font-weight: bold; "
                "background: #FFFBEB; border: 3px solid #F59E0B; "
                "border-radius: 14px; padding: 10px 28px;"
            )
        elif achievement == "준우승":
            self.lbl_achieve.setText("🥈  준우승")
            self.lbl_achieve.setStyleSheet(
                f"color: {color}; font-size: 36px; font-weight: bold; "
                "background: #F8F8F8; border: 2px solid #868E96; "
                "border-radius: 12px; padding: 8px 20px;"
            )
        else:
            self.lbl_achieve.setText(achievement)
            self.lbl_achieve.setStyleSheet(
                f"color: {color}; font-size: 36px; font-weight: bold; background: transparent;"
            )

        with get_connection() as conn:
            now = dict(conn.execute(
                "SELECT * FROM players WHERE id=?", (my_player_id,)
            ).fetchone())

        race_color = RACE_COLORS.get(now["race"], "#fff")
        self.lbl_player.setText(
            f"{now['name']}  ({RACE_DISPLAY.get(now['race'], now['race'])})  —  토너먼트 여정 종료"
        )
        self.lbl_player.setStyleSheet(
            f"color: {race_color}; font-size: 18px; background: transparent;"
        )

        # 능력치 비교 테이블
        self.table.setRowCount(len(STAT_KEYS) + 2)
        for i, (key, lbl) in enumerate(zip(STAT_KEYS, STAT_LABELS)):
            before = snap_before.get(key, 0)
            after  = now[key]
            delta  = after - before

            items = [lbl, str(before), str(after),
                     f"+{delta}" if delta >= 0 else str(delta)]
            for ci, val in enumerate(items):
                ti = QTableWidgetItem(val)
                ti.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if ci == 3:
                    if delta > 0:
                        ti.setForeground(QColor("#51CF66"))
                    elif delta < 0:
                        ti.setForeground(QColor("#FF6B6B"))
                self.table.setItem(i, ci, ti)

        # OVR 행
        bov = snap_before.get("overall", 0)
        aov = now["overall"]
        dov = round(aov - bov, 2)
        for ci, val in enumerate(
            ["OVR", f"{bov:.1f}", f"{aov:.1f}",
             f"+{dov:.1f}" if dov >= 0 else f"{dov:.1f}"]
        ):
            ti = QTableWidgetItem(val)
            ti.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if ci == 3:
                ti.setForeground(QColor("#51CF66" if dov >= 0 else "#FF6B6B"))
            self.table.setItem(len(STAT_KEYS), ci, ti)

        # 등급 행 (빈 행으로 처리)
        self.table.setItem(len(STAT_KEYS) + 1, 0, QTableWidgetItem(""))

        # 등급 변동
        og = snap_before.get("grade", "?")
        ng = now["grade"]
        old_style = GRADE_STYLE.get(og, "")
        new_style = GRADE_STYLE.get(ng, "")
        self.lbl_grade.setText(
            f"등급 변동:  ◆ {og}  →  ◆ {ng}"
        )
        # 단순 색상 처리
        self.lbl_grade.setStyleSheet(
            new_style + " font-size: 20px; background: transparent;"
        )

        # 골드
        self.lbl_gold.setText(
            f"토너먼트 획득 골드: +{gold_earned} G    |    최종 보유: {get_gold()} G"
        )

        # 토너먼트 경로
        if tournament_id:
            self._fill_path(tournament_id, my_player_id)
        else:
            self.lbl_path.setText("—")

        # 성장 이벤트 초기화
        self.lbl_growth.setVisible(False)
        self.lbl_growth.setText("")

        # 우승 시 반짝임 애니메이션
        if achievement == "우승":
            self._flash = 0
            self._fd = 1
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._flash_fn)
            self._timer.start(80)
            QTimer.singleShot(4000, self._timer.stop)

    def _flash_fn(self):
        self._flash += self._fd * 8
        if self._flash >= 60:
            self._fd = -1
        elif self._flash <= 0:
            self._fd = 1
        r = min(255, 200 + self._flash)
        g = min(255, 130 + self._flash // 2)
        border_r = min(255, 240 + self._flash // 4)
        self.lbl_achieve.setStyleSheet(
            f"color: rgb({r},{g},0); font-size: 42px; font-weight: bold; "
            f"background: #FFFBEB; border: 3px solid rgb({border_r},{g//2},0); "
            "border-radius: 14px; padding: 10px 28px;"
        )

    def show_growth(self, events: list):
        """성장 이벤트 결과를 화면에 표시"""
        if not events:
            return
        parts = [f"{ev['stat_label']} +{ev['delta']}" for ev in events]
        text = "🌱  성장 이벤트:  " + "  |  ".join(parts)
        self.lbl_growth.setText(text)
        self.lbl_growth.setVisible(True)

    def _fill_path(self, tournament_id: int, my_player_id: int):
        """토너먼트에서 내 경기 경로를 조회해 표시."""
        with get_connection() as conn:
            matches = conn.execute(
                """SELECT tm.round, tm.player_a_id, tm.player_b_id,
                          tm.winner_id, tm.a_wins, tm.b_wins,
                          pa.name AS a_name, pb.name AS b_name
                   FROM tournament_matches tm
                   JOIN players pa ON pa.id = tm.player_a_id
                   JOIN players pb ON pb.id = tm.player_b_id
                   WHERE tm.tournament_id = ?
                     AND tm.is_my_match = 1
                     AND tm.status = 'completed'
                   ORDER BY tm.id ASC""",
                (tournament_id,)
            ).fetchall()

        if not matches:
            self.lbl_path.setText("경기 기록 없음")
            return

        parts = []
        for m in matches:
            opp_name = m["b_name"] if m["player_a_id"] == my_player_id else m["a_name"]
            won = (m["winner_id"] == my_player_id)
            score = f"{m['a_wins']}-{m['b_wins']}" if m["player_a_id"] == my_player_id else f"{m['b_wins']}-{m['a_wins']}"
            icon = "★" if won else "✗"
            step_color = "#15803D" if won else "#DC2626"
            parts.append(
                f'<span style="color:{step_color}; font-weight:bold;">'
                f'{m["round"]} {icon}</span>'
                f'<span style="color:#868E96;"> vs {opp_name} ({score})</span>'
            )

        arrow = '<span style="color:#ADB5BD;">  →  </span>'
        self.lbl_path.setText(arrow.join(parts))
        self.lbl_path.setTextFormat(Qt.TextFormat.RichText)
