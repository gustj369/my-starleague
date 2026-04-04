"""세이브 슬롯 선택 화면 — 5슬롯"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from database.slot_manager import SLOT_COUNT, get_slot_info, delete_slot


class SlotCard(QFrame):
    """단일 슬롯 카드 위젯"""
    sig_new_game = pyqtSignal(int)      # slot_idx
    sig_continue = pyqtSignal(int)      # slot_idx

    def __init__(self, slot_idx: int, parent=None):
        super().__init__(parent)
        self._slot_idx = slot_idx
        self.setMinimumWidth(170)
        self.setStyleSheet("""
            QFrame {
                background: #0d1525;
                border: 1px solid #1e3a5f;
                border-radius: 8px;
            }
        """)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(8)

        # 슬롯 번호
        self.lbl_slot = QLabel(f"SLOT  {self._slot_idx + 1}")
        self.lbl_slot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_slot.setStyleSheet(
            "color: #4fc3f7; font-size: 13px; font-weight: bold;"
            " background: transparent; letter-spacing: 2px;"
        )

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1e3a5f; background: transparent;")

        self.lbl_status = QLabel("빈 슬롯")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #7a9ab8; font-size: 12px; background: transparent;")

        self.lbl_gold = QLabel("")
        self.lbl_gold.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gold.setStyleSheet("color: #ffd700; font-size: 12px; background: transparent;")

        self.lbl_achievement = QLabel("")
        self.lbl_achievement.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_achievement.setWordWrap(True)
        self.lbl_achievement.setStyleSheet("color: #c8d8e8; font-size: 11px; background: transparent;")

        self.btn_new = QPushButton("▶  새 게임")
        self.btn_new.setMinimumHeight(36)
        self.btn_new.setStyleSheet("""
            QPushButton {
                background: #1a3a6a; color: #c8d8e8;
                border: 1px solid #1e3a5f; border-radius: 4px; font-size: 12px;
            }
            QPushButton:hover { background: #1e4a8a; border-color: #4fc3f7; color: #ffd700; }
        """)
        self.btn_new.clicked.connect(self._on_new_game)

        self.btn_continue = QPushButton("◈  이어하기")
        self.btn_continue.setMinimumHeight(36)
        self.btn_continue.setProperty("class", "primary")
        self.btn_continue.hide()
        self.btn_continue.clicked.connect(self._on_continue)

        self.btn_reset = QPushButton("✕  초기화")
        self.btn_reset.setMinimumHeight(30)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background: transparent; color: #EF9A9A;
                border: 1px solid #4a1a1a; border-radius: 3px; font-size: 11px;
            }
            QPushButton:hover { background: #2a0a0a; border-color: #EF9A9A; }
        """)
        self.btn_reset.hide()
        self.btn_reset.clicked.connect(self._on_reset)

        lay.addWidget(self.lbl_slot)
        lay.addWidget(sep)
        lay.addStretch()
        lay.addWidget(self.lbl_status)
        lay.addWidget(self.lbl_gold)
        lay.addWidget(self.lbl_achievement)
        lay.addStretch()
        lay.addWidget(self.btn_continue)
        lay.addWidget(self.btn_new)
        lay.addWidget(self.btn_reset)

    def refresh(self):
        info = get_slot_info(self._slot_idx)
        if info["empty"]:
            self.lbl_status.setText("빈 슬롯")
            self.lbl_gold.setText("")
            self.lbl_achievement.setText("")
            self.btn_continue.hide()
            self.btn_new.setText("▶  새 게임")
            self.btn_reset.hide()
            self.setStyleSheet("""
                QFrame { background: #0d1525; border: 1px solid #1e3a5f; border-radius: 8px; }
            """)
        else:
            self.lbl_status.setText(info["status_text"])
            self.lbl_gold.setText(f"💰 {info['gold']:,} G")
            achv = info["last_achievement"]
            self.lbl_achievement.setText(f"최근: {achv}" if achv else "")
            self.btn_continue.show()
            self.btn_new.setText("▶  새 게임 (초기화)")
            self.btn_new.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #7a9ab8;
                    border: 1px solid #1e3a5f; border-radius: 4px; font-size: 11px;
                }
                QPushButton:hover { border-color: #EF9A9A; color: #EF9A9A; }
            """)
            self.btn_reset.hide()  # 새 게임(초기화) 버튼에 통합
            self.setStyleSheet("""
                QFrame { background: #0a1a30; border: 1px solid #1e4a8a; border-radius: 8px; }
            """)

    def _on_new_game(self):
        info = get_slot_info(self._slot_idx)
        if not info["empty"]:
            reply = QMessageBox.question(
                self,
                "슬롯 초기화",
                f"슬롯 {self._slot_idx + 1}의 데이터를 삭제하고 새 게임을 시작합니다.\n"
                "저장된 골드와 기록이 모두 사라집니다. 계속하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            delete_slot(self._slot_idx)
        self.sig_new_game.emit(self._slot_idx)

    def _on_continue(self):
        self.sig_continue.emit(self._slot_idx)

    def _on_reset(self):
        self._on_new_game()


class SlotSelectScreen(QWidget):
    sig_new_game = pyqtSignal(int)   # slot_idx — 새 게임 (슬롯 초기화 후)
    sig_continue = pyqtSignal(int)   # slot_idx — 이어하기

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(0)

        # 배경
        bg = QFrame()
        bg.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #050b18, stop:0.5 #0a1830, stop:1 #050b18
                );
                border-radius: 10px;
            }
        """)
        bg_lay = QVBoxLayout(bg)
        bg_lay.setContentsMargins(40, 36, 40, 36)
        bg_lay.setSpacing(28)

        # 타이틀
        title = QLabel("★  세이브 슬롯 선택  ★")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color: #ffd700; font-size: 22px; font-weight: bold; background: transparent;"
        )
        subtitle = QLabel("슬롯을 선택해 게임을 이어하거나 새로 시작하세요")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #7a9ab8; font-size: 12px; background: transparent;")

        # 슬롯 카드 5개
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)
        self._cards: list[SlotCard] = []

        for i in range(SLOT_COUNT):
            card = SlotCard(i)
            card.sig_new_game.connect(self.sig_new_game)
            card.sig_continue.connect(self.sig_continue)
            self._cards.append(card)
            cards_row.addWidget(card, 1)

        # 하단 안내
        hint = QLabel("새 게임을 시작하면 슬롯의 모든 데이터가 초기화됩니다  ·  각 슬롯은 독립적으로 저장됩니다")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #2a4060; font-size: 11px; background: transparent;")

        bg_lay.addWidget(title)
        bg_lay.addWidget(subtitle)
        bg_lay.addLayout(cards_row)
        bg_lay.addWidget(hint)

        root.addWidget(bg)

    def refresh(self):
        """모든 슬롯 카드 정보 갱신"""
        for card in self._cards:
            card.refresh()
