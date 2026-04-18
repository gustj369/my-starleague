"""도전과제 화면 — 11개 업적 달성 현황"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from database.db import get_achievements
from ui.widgets import make_separator


class AchievementsScreen(QWidget):
    sig_back = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 헤더 (고정) ──
        hdr_widget = QWidget()
        hdr_widget.setStyleSheet("background: #FFFFFF; border-bottom: 1px solid #E9ECEF;")
        hdr_lay = QHBoxLayout(hdr_widget)
        hdr_lay.setContentsMargins(24, 12, 24, 12)

        btn_back = QPushButton("◀  뒤로")
        btn_back.setFixedHeight(34)
        btn_back.setStyleSheet("""
            QPushButton {
                background: transparent; color: #5B6CF6;
                border: 1px solid #C5C8FF; border-radius: 8px;
                padding: 0 14px; font-size: 12px;
            }
            QPushButton:hover { background: #EEF2FF; }
        """)
        btn_back.clicked.connect(self.sig_back)

        title_lbl = QLabel("🏆  도전과제")
        title_lbl.setStyleSheet(
            "color: #212529; font-size: 22px; font-weight: bold; background: transparent;"
        )

        self.lbl_progress = QLabel("")
        self.lbl_progress.setStyleSheet(
            "color: #868E96; font-size: 13px; background: transparent;"
        )

        hdr_lay.addWidget(btn_back)
        hdr_lay.addSpacing(16)
        hdr_lay.addWidget(title_lbl)
        hdr_lay.addStretch()
        hdr_lay.addWidget(self.lbl_progress)
        root.addWidget(hdr_widget)

        # ── 스크롤 영역 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #F8F9FA; }")

        self._content = QWidget()
        self._content.setStyleSheet("background: #F8F9FA;")
        self._grid = QGridLayout(self._content)
        self._grid.setContentsMargins(32, 24, 32, 24)
        self._grid.setSpacing(16)

        scroll.setWidget(self._content)
        root.addWidget(scroll, 1)

    # ── 카드 생성 ──────────────────────────────────────────────
    @staticmethod
    def _make_card(ach: dict) -> QFrame:
        earned = bool(ach.get("earned"))
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #FFFFFF; border: 2px solid #51CF66; border-radius: 14px; }"
            if earned else
            "QFrame { background: #F8F9FA; border: 1px solid #E9ECEF; border-radius: 14px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(6)

        # 아이콘 + 이름
        top_row = QHBoxLayout()
        icon_lbl = QLabel(ach.get("icon", "🏆"))
        icon_lbl.setStyleSheet(
            "font-size: 28px; background: transparent;"
        )
        icon_lbl.setFixedWidth(40)

        name_lbl = QLabel(ach.get("name", ""))
        name_lbl.setStyleSheet(
            f"color: {'#212529' if earned else '#ADB5BD'}; "
            f"font-size: 15px; font-weight: bold; background: transparent;"
        )
        name_lbl.setWordWrap(True)

        top_row.addWidget(icon_lbl)
        top_row.addWidget(name_lbl, 1)
        lay.addLayout(top_row)

        # 설명
        desc_lbl = QLabel(ach.get("desc", ""))
        desc_lbl.setStyleSheet(
            f"color: {'#495057' if earned else '#CED4DA'}; "
            "font-size: 12px; background: transparent;"
        )
        desc_lbl.setWordWrap(True)
        lay.addWidget(desc_lbl)

        # 달성 상태 / 날짜
        if earned:
            date_str = ach.get("earned_at", "")
            if date_str:
                date_str = date_str[:16]   # datetime 앞 16자리
            status_lbl = QLabel(f"✔ 달성 완료   {date_str}")
            status_lbl.setStyleSheet(
                "color: #51CF66; font-size: 11px; font-weight: bold; background: transparent;"
            )
        else:
            status_lbl = QLabel("🔒 미달성")
            status_lbl.setStyleSheet(
                "color: #ADB5BD; font-size: 11px; background: transparent;"
            )
        lay.addWidget(status_lbl)

        return frame

    # ── 새로고침 ────────────────────────────────────────────────
    def refresh(self):
        # 기존 위젯 제거
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        achievements = get_achievements()
        earned_count = sum(1 for a in achievements if a.get("earned"))
        total = len(achievements)
        self.lbl_progress.setText(f"달성: {earned_count} / {total}")

        # 2열 그리드로 배치
        for i, ach in enumerate(achievements):
            row, col = divmod(i, 2)
            card = self._make_card(ach)
            self._grid.addWidget(card, row, col)

        # 홀수 개면 마지막 열에 빈 공간
        if total % 2 == 1:
            self._grid.setColumnStretch(0, 1)
            self._grid.setColumnStretch(1, 1)
