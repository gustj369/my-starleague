from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpacerItem,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QLinearGradient

from database.db import get_game_summary, get_current_tournament_id


class AnimatedTitle(QLabel):
    """금색 글로우 효과를 가진 타이틀 레이블"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._glow = 0
        self._direction = 1
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont("맑은 고딕", 32, QFont.Weight.Bold)
        self.setFont(font)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)

    def _animate(self):
        self._glow += self._direction * 3
        if self._glow >= 60:
            self._direction = -1
        elif self._glow <= 0:
            self._direction = 1
        r = min(255, 200 + self._glow)
        g = min(255, 180 + self._glow // 2)
        self.setStyleSheet(f"color: rgb({r},{g},0); background: transparent;")


class MainMenuScreen(QWidget):
    sig_new_game   = pyqtSignal()
    sig_load_game  = pyqtSignal()
    sig_back       = pyqtSignal()   # 슬롯 선택 화면으로
    sig_exit       = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 배경 그라디언트 패널 ──
        bg = QFrame()
        bg.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #050b18,
                    stop:0.5 #0a1830,
                    stop:1 #050b18
                );
            }
        """)
        bg_layout = QVBoxLayout(bg)
        bg_layout.setContentsMargins(60, 60, 60, 60)
        bg_layout.setSpacing(0)

        # ── 타이틀 영역 ──
        title_area = QVBoxLayout()
        title_area.setSpacing(8)

        subtitle = QLabel("2012 SEASON")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #4fc3f7; font-size: 14px; letter-spacing: 6px; background: transparent;")

        title = AnimatedTitle("마이 스타리그")

        tagline = QLabel("MY STARLEAGUE")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet("color: #ffd700; font-size: 12px; letter-spacing: 8px; background: transparent;")

        title_area.addWidget(subtitle)
        title_area.addWidget(title)
        title_area.addWidget(tagline)

        # ── 구분선 ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1e3a5f;")

        # ── 버튼 영역 ──
        btn_area = QVBoxLayout()
        btn_area.setSpacing(14)
        btn_area.setContentsMargins(120, 0, 120, 0)

        self.btn_new  = self._make_menu_btn("▶  새 토너먼트",  primary=True)
        self.btn_load = self._make_menu_btn("◈  불러오기")
        self.btn_back = self._make_menu_btn("◀  슬롯 선택")
        self.btn_exit = self._make_menu_btn("✕  종료", danger=True)

        self.btn_new.clicked.connect(self.sig_new_game)
        self.btn_load.clicked.connect(self.sig_load_game)
        self.btn_back.clicked.connect(self.sig_back)
        self.btn_exit.clicked.connect(self.sig_exit)

        btn_area.addWidget(self.btn_new)
        btn_area.addWidget(self.btn_load)
        btn_area.addWidget(self.btn_back)
        btn_area.addWidget(self.btn_exit)

        # ── 세이브 요약 정보 ──
        self.lbl_summary = QLabel("")
        self.lbl_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_summary.setStyleSheet(
            "color: #4fc3f7; font-size: 12px; background: transparent;"
        )

        # ── 하단 크레딧 ──
        credit = QLabel("Powered by Claude Code  ·  2012 KeSPA Brood War")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit.setStyleSheet("color: #2a4060; font-size: 11px; background: transparent;")

        bg_layout.addStretch(2)
        bg_layout.addLayout(title_area)
        bg_layout.addSpacing(40)
        bg_layout.addWidget(sep)
        bg_layout.addSpacing(24)
        bg_layout.addLayout(btn_area)
        bg_layout.addSpacing(16)
        bg_layout.addWidget(self.lbl_summary)
        bg_layout.addStretch(2)
        bg_layout.addWidget(credit)

        root.addWidget(bg)

    def refresh(self):
        """세이브 상태에 따라 버튼 레이블과 요약 정보를 갱신"""
        tid = get_current_tournament_id()
        summary = get_game_summary()

        if tid:
            # 진행 중인 토너먼트
            self.btn_load.setText("◈  이어하기 (진행 중)")
            self.btn_load.setEnabled(True)
        elif summary["total_tournaments"] > 0:
            # 완료된 토너먼트만 있음
            self.btn_load.setText("◈  새 토너먼트 시작 (골드 유지)")
            self.btn_load.setEnabled(True)
        else:
            self.btn_load.setText("◈  불러오기 (저장 없음)")
            self.btn_load.setEnabled(False)

        # 요약 정보 표시
        if summary["total_tournaments"] > 0:
            achv = summary["last_achievement"] or "—"
            gold = summary["gold"]
            count = summary["total_tournaments"]
            self.lbl_summary.setText(
                f"마지막 성적: {achv}   |   보유 골드: {gold:,} G   |   토너먼트: {count}회"
            )
        else:
            self.lbl_summary.setText("")

    @staticmethod
    def _make_menu_btn(text: str, primary=False, danger=False) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumHeight(48)
        if primary:
            btn.setProperty("class", "primary")
        elif danger:
            btn.setProperty("class", "danger")
        btn.setStyleSheet(btn.styleSheet())   # 프로퍼티 반영 강제
        return btn
