"""시즌 시작 뉴스 다이얼로그"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt

from core.season_events import get_effect_summary


class SeasonNewsDialog(QDialog):
    def __init__(self, events: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("시즌 뉴스")
        self.setMinimumWidth(460)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self._build_ui(events)

    def _build_ui(self, events: list[dict]):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # 헤더
        title = QLabel("📰  이번 시즌 뉴스")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color: #212529; font-size: 20px; font-weight: bold; background: transparent;"
        )
        subtitle = QLabel("토너먼트 시작 전 발생한 이벤트를 확인하세요.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #868E96; font-size: 12px; background: transparent;")

        root.addWidget(title)
        root.addWidget(subtitle)

        # 이벤트 카드들
        for ev in events:
            card = self._make_card(ev)
            root.addWidget(card)

        # 시작 버튼
        btn = QPushButton("✔  확인하고 시즌 시작!")
        btn.setMinimumHeight(44)
        btn.setProperty("class", "primary")
        btn.clicked.connect(self.accept)
        root.addWidget(btn)

    def _make_card(self, ev: dict) -> QFrame:
        frame = QFrame()
        effect = ev["effect"]
        if effect == "gold":
            border_color = "#F59E0B" if ev["value"] > 0 else "#FF6B6B"
            bg = "#FFFBEB" if ev["value"] > 0 else "#FFF5F5"
        elif effect == "fatigue":
            border_color = "#FF6B6B"
            bg = "#FFF5F5"
        else:
            border_color = "#C5C8FF"
            bg = "#F5F6FF"

        frame.setStyleSheet(
            f"QFrame {{ background: {bg}; border: 1px solid {border_color}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        # 제목 행
        title_row = QHBoxLayout()
        icon_lbl = QLabel(ev["icon"])
        icon_lbl.setStyleSheet("font-size: 18px; background: transparent;")
        icon_lbl.setFixedWidth(28)
        title_lbl = QLabel(ev["title"])
        title_lbl.setStyleSheet(
            "color: #212529; font-size: 13px; font-weight: bold; background: transparent;"
        )
        effect_lbl = QLabel(get_effect_summary(ev))
        effect_col = "#F59E0B" if effect == "gold" and ev["value"] > 0 else "#FF6B6B" if effect in ("gold", "fatigue") else "#5B6CF6"
        effect_lbl.setStyleSheet(
            f"color: {effect_col}; font-size: 12px; font-weight: bold; background: transparent;"
        )
        effect_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl, 1)
        title_row.addWidget(effect_lbl)

        desc_lbl = QLabel(ev["desc"])
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #868E96; font-size: 12px; background: transparent;")

        lay.addLayout(title_row)
        lay.addWidget(desc_lbl)
        return frame
