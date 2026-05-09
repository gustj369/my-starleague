"""세이브 슬롯 선택 화면 — 라이트 테마"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from database.slot_manager import SLOT_COUNT, get_slot_info, delete_slot


class SlotCard(QFrame):
    sig_new_game = pyqtSignal(int)
    sig_continue = pyqtSignal(int)

    def __init__(self, slot_idx: int, parent=None):
        super().__init__(parent)
        self._slot_idx = slot_idx
        self.setMinimumWidth(190)
        self.setMinimumHeight(280)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(16, 16, 16, 16)
        self._lay.setSpacing(8)

        # 슬롯 번호
        self.lbl_slot = QLabel(f"SLOT  {self._slot_idx + 1}")
        self.lbl_slot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_slot.setStyleSheet(
            "color: #868E96; font-size: 11px; font-weight: bold; letter-spacing: 2px; background: transparent;"
        )

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #E9ECEF;")

        self.lbl_status = QLabel("빈 슬롯")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #ADB5BD; font-size: 12px; background: transparent;")

        self.lbl_gold = QLabel("")
        self.lbl_gold.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gold.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: bold; background: transparent;")

        self.lbl_achievement = QLabel("")
        self.lbl_achievement.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_achievement.setWordWrap(True)
        self.lbl_achievement.setStyleSheet("color: #868E96; font-size: 11px; background: transparent;")

        self.btn_continue = QPushButton("▶  이어하기")
        self.btn_continue.setMinimumHeight(38)
        self.btn_continue.setProperty("class", "primary")
        self.btn_continue.hide()
        self.btn_continue.clicked.connect(self._on_continue)

        self.btn_new = QPushButton("+ 새 게임")
        self.btn_new.setMinimumHeight(38)
        self.btn_new.setStyleSheet("""
            QPushButton {
                background: #FFFFFF; color: #5B6CF6;
                border: 1px solid #5B6CF6; border-radius: 10px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background: #EEF2FF; }
        """)
        self.btn_new.clicked.connect(self._on_new_game)

        self.btn_reset = QPushButton("초기화")
        self.btn_reset.setMinimumHeight(28)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background: transparent; color: #ADB5BD;
                border: none; font-size: 11px;
            }
            QPushButton:hover { color: #FF6B6B; }
        """)
        self.btn_reset.hide()
        self.btn_reset.clicked.connect(self._on_new_game)

        self._lay.addWidget(self.lbl_slot)
        self._lay.addWidget(sep)
        self._lay.addStretch()
        self._lay.addWidget(self.lbl_status)
        self._lay.addWidget(self.lbl_gold)
        self._lay.addWidget(self.lbl_achievement)
        self._lay.addStretch()
        self._lay.addWidget(self.btn_continue)
        self._lay.addWidget(self.btn_new)
        self._lay.addWidget(self.btn_reset)

    def refresh(self):
        info = get_slot_info(self._slot_idx)
        if info["empty"]:
            self.lbl_status.setText("빈 슬롯")
            self.lbl_gold.setText("")
            self.lbl_achievement.setText("")
            self.btn_continue.hide()
            self.btn_new.setText("+ 새 게임")
            self.btn_new.setStyleSheet("""
                QPushButton {
                    background: #FFFFFF; color: #5B6CF6;
                    border: 1px solid #5B6CF6; border-radius: 10px;
                    font-size: 13px; font-weight: 600;
                }
                QPushButton:hover { background: #EEF2FF; }
            """)
            self.btn_reset.hide()
            self.setStyleSheet("""
                QFrame {
                    background: #FFFFFF;
                    border: 1px solid #E9ECEF;
                    border-radius: 16px;
                }
            """)
        elif info.get("corrupt"):
            self.lbl_status.setText("⚠ 손상된 슬롯")
            self.lbl_status.setStyleSheet(
                "color: #FF6B6B; font-size: 12px; font-weight: bold;"
                " background: #FFF5F5; border-radius: 6px; padding: 3px 8px;"
            )
            self.lbl_gold.setText("")
            self.lbl_achievement.setText("이어하기 불가 · 새 게임으로 덮어쓸 수 있습니다")
            self.btn_continue.hide()
            self.btn_new.setText("새 게임")
            self.btn_new.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #ADB5BD;
                    border: none; font-size: 11px;
                }
                QPushButton:hover { color: #FF6B6B; }
            """)
            self.btn_reset.hide()
            self.setStyleSheet("""
                QFrame {
                    background: #FFFFFF;
                    border: 1px solid #FF6B6B;
                    border-radius: 16px;
                }
            """)
        else:
            # 상태 배지
            status_txt = info["status_text"]
            self.lbl_status.setText(status_txt)
            self.lbl_status.setStyleSheet(
                "color: #5B6CF6; font-size: 12px; font-weight: bold;"
                " background: #EEF2FF; border-radius: 6px; padding: 3px 8px;"
            )
            self.lbl_gold.setText(f"🪙  {info['gold']:,} G")
            achv = info["last_achievement"]
            self.lbl_achievement.setText(f"최근: {achv}" if achv else "")
            self.btn_continue.show()
            self.btn_new.setText("새 게임")
            self.btn_new.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #ADB5BD;
                    border: none; font-size: 11px;
                }
                QPushButton:hover { color: #FF6B6B; }
            """)
            self.btn_reset.hide()
            self.setStyleSheet("""
                QFrame {
                    background: #FFFFFF;
                    border: 1px solid #5B6CF6;
                    border-radius: 16px;
                }
            """)

    def _on_new_game(self):
        info = get_slot_info(self._slot_idx)
        if not info["empty"]:
            reply = QMessageBox.question(
                self, "슬롯 초기화",
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


class SlotSelectScreen(QWidget):
    sig_new_game = pyqtSignal(int)
    sig_continue = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 48, 48, 48)
        root.setSpacing(32)

        # 타이틀
        title = QLabel("세이브 슬롯 선택")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color: #212529; font-size: 28px; font-weight: bold; background: transparent;"
        )
        subtitle = QLabel("슬롯을 선택해 게임을 이어하거나 새로 시작하세요")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #868E96; font-size: 14px; background: transparent;")

        title_col = QVBoxLayout()
        title_col.setSpacing(8)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        # 슬롯 카드 5개
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        self._cards: list[SlotCard] = []
        for i in range(SLOT_COUNT):
            card = SlotCard(i)
            card.sig_new_game.connect(self.sig_new_game)
            card.sig_continue.connect(self.sig_continue)
            self._cards.append(card)
            cards_row.addWidget(card, 1)

        # 하단 안내
        hint = QLabel("각 슬롯은 독립적으로 저장됩니다  ·  새 게임 시작 시 슬롯 데이터가 초기화됩니다")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #CED4DA; font-size: 12px; background: transparent;")

        root.addStretch()
        root.addLayout(title_col)
        root.addLayout(cards_row)
        root.addWidget(hint)
        root.addStretch()

    def refresh(self):
        for card in self._cards:
            card.refresh()
