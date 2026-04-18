"""메인 메뉴 화면 — 라이트 테마"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from database.db import get_game_summary, get_current_tournament_id


class MainMenuScreen(QWidget):
    sig_new_game   = pyqtSignal()
    sig_load_game  = pyqtSignal()
    sig_back       = pyqtSignal()
    sig_exit       = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 배경 패널
        bg = QFrame()
        bg.setStyleSheet("QFrame { background: #F8F9FA; }")
        bg_layout = QVBoxLayout(bg)
        bg_layout.setContentsMargins(80, 80, 80, 80)
        bg_layout.setSpacing(0)

        # 타이틀 영역
        title_area = QVBoxLayout()
        title_area.setSpacing(10)

        subtitle_lbl = QLabel("LEGEND LEAGUE")
        subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_lbl.setStyleSheet(
            "color: #5B6CF6; font-size: 13px; letter-spacing: 8px; font-weight: bold; background: transparent;"
        )

        title_lbl = QLabel("레전드 리그")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_lbl.setStyleSheet(
            "color: #212529; font-size: 40px; font-weight: bold; background: transparent;"
        )

        season_lbl = QLabel("2026 SEASON")
        season_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        season_lbl.setStyleSheet(
            "color: #ADB5BD; font-size: 13px; letter-spacing: 4px; background: transparent;"
        )

        title_area.addWidget(subtitle_lbl)
        title_area.addWidget(title_lbl)
        title_area.addWidget(season_lbl)

        # 구분선
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #E9ECEF; margin: 0 60px;")

        # 버튼 영역
        btn_area = QVBoxLayout()
        btn_area.setSpacing(12)
        btn_area.setContentsMargins(140, 0, 140, 0)

        self.btn_new  = self._make_btn("▶  새 토너먼트", primary=True)
        self.btn_load = self._make_btn("◈  이어하기")
        self.btn_back = self._make_btn("◀  슬롯 선택")
        self.btn_exit = self._make_btn("✕  종료", danger=True)

        self.btn_new.clicked.connect(self.sig_new_game)
        self.btn_load.clicked.connect(self.sig_load_game)
        self.btn_back.clicked.connect(self.sig_back)
        self.btn_exit.clicked.connect(self.sig_exit)

        btn_area.addWidget(self.btn_new)
        btn_area.addWidget(self.btn_load)
        btn_area.addWidget(self.btn_back)
        btn_area.addWidget(self.btn_exit)

        # 세이브 요약 카드 (테두리 포함)
        self.lbl_summary = QLabel("")
        self.lbl_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_summary.setStyleSheet(
            "color: #868E96; font-size: 12px; background: transparent;"
        )

        # 크레딧
        credit = QLabel("Powered by Claude Code  ·  2026 Legend League Season")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credit.setStyleSheet("color: #CED4DA; font-size: 11px; background: transparent;")

        bg_layout.addStretch(2)
        bg_layout.addLayout(title_area)
        bg_layout.addSpacing(36)
        bg_layout.addWidget(sep)
        bg_layout.addSpacing(28)
        bg_layout.addLayout(btn_area)
        bg_layout.addSpacing(16)
        bg_layout.addWidget(self.lbl_summary)
        bg_layout.addStretch(2)
        bg_layout.addWidget(credit)

        root.addWidget(bg)

    def refresh(self):
        tid = get_current_tournament_id()
        summary = get_game_summary()

        if tid:
            self.btn_load.setText("◈  이어하기 (진행 중)")
            self.btn_load.setEnabled(True)
        elif summary["total_tournaments"] > 0:
            self.btn_load.setText("◈  새 토너먼트 시작 (골드 유지)")
            self.btn_load.setEnabled(True)
        else:
            self.btn_load.setText("◈  불러오기 (저장 없음)")
            self.btn_load.setEnabled(False)

        if summary["total_tournaments"] > 0:
            achv  = summary["last_achievement"] or "—"
            best  = summary.get("best_achievement", "")
            gold  = summary["gold"]
            count = summary["total_tournaments"]
            parts = [f"마지막 성적: {achv}"]
            # 최고 성적이 마지막 성적과 다를 때만 추가 표시
            if best and best != achv:
                parts.append(f"🏆 최고: {best}")
            parts.append(f"보유 골드: {gold:,} G")
            parts.append(f"토너먼트: {count}회")
            self.lbl_summary.setText("   |   ".join(parts))
            # 카드 스타일 적용 (데이터 있을 때)
            self.lbl_summary.setStyleSheet(
                "color: #5B6CF6; font-size: 12px; font-weight: bold; "
                "background: #EEF2FF; border: 1px solid #C5C8FF; "
                "border-radius: 8px; padding: 8px 20px;"
            )
        else:
            self.lbl_summary.setText("")
            self.lbl_summary.setStyleSheet(
                "color: #868E96; font-size: 12px; background: transparent;"
            )

    @staticmethod
    def _make_btn(text: str, primary=False, danger=False) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumHeight(48)
        if primary:
            btn.setProperty("class", "primary")
        elif danger:
            btn.setProperty("class", "danger")
        return btn
