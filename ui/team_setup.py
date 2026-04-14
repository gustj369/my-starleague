"""팀 편성 화면 — 선수 A, B 선택"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QComboBox, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from database.db import get_connection
from ui.widgets import PlayerCard, make_separator
from ui.styles import RACE_COLORS


def _load_players(race_filter: str = "전체") -> list[dict]:
    with get_connection() as conn:
        if race_filter == "전체":
            rows = conn.execute("SELECT * FROM players ORDER BY overall DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM players WHERE race=? ORDER BY overall DESC",
                (race_filter,)
            ).fetchall()
    return [dict(r) for r in rows]


class TeamSetupScreen(QWidget):
    sig_proceed = pyqtSignal(int, int)   # player_a_id, player_b_id
    sig_back    = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_a: int | None = None
        self._selected_b: int | None = None
        self._cards: dict[int, PlayerCard] = {}   # player_id → card
        self._build_ui()
        self._load_players()

    # ──────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # 헤더
        hdr = QHBoxLayout()
        title = QLabel("팀 편성")
        title.setProperty("class", "title")
        title.setStyleSheet("color: #212529; font-size: 22px; font-weight: bold; background: transparent;")

        self.btn_back = QPushButton("← 메인 메뉴")
        self.btn_back.clicked.connect(self.sig_back)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.btn_back)

        # 필터
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("종족 필터:"))
        self.cmb_race = QComboBox()
        self.cmb_race.addItems(["전체", "테란", "저그", "프로토스"])
        self.cmb_race.currentTextChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.cmb_race)
        filter_row.addStretch()

        hint = QLabel("선수를 클릭하여 A / B 슬롯에 배정합니다. (첫 클릭 → A, 두 번째 클릭 → B)")
        hint.setStyleSheet("color: #868E96; font-size: 11px; background: transparent;")
        filter_row.addWidget(hint)

        # 선택 현황
        sel_row = QHBoxLayout()
        self.lbl_sel_a = self._slot_label("A")
        self.lbl_sel_b = self._slot_label("B")
        sel_row.addWidget(self._slot_box("선수 A", self.lbl_sel_a))
        sel_row.addSpacing(20)
        sel_row.addWidget(self._slot_box("선수 B", self.lbl_sel_b))
        sel_row.addStretch()

        self.btn_proceed = QPushButton("▶  대결 설정으로")
        self.btn_proceed.setProperty("class", "primary")
        self.btn_proceed.setEnabled(False)
        self.btn_proceed.clicked.connect(self._on_proceed)
        sel_row.addWidget(self.btn_proceed)

        # 선수 그리드 (스크롤)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; }")

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        self.scroll.setWidget(self.grid_widget)

        root.addLayout(hdr)
        root.addWidget(make_separator())
        root.addLayout(filter_row)
        root.addLayout(sel_row)
        root.addWidget(make_separator())
        root.addWidget(self.scroll, 1)

    # ──────────────────────────────────────────
    @staticmethod
    def _slot_label(slot: str) -> QLabel:
        lbl = QLabel(f"미선택")
        lbl.setStyleSheet("color: #868E96; font-size: 13px; background: transparent;")
        return lbl

    @staticmethod
    def _slot_box(title: str, content_label: QLabel) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { background: #F8F9FA; border: 1px solid #E9ECEF; border-radius: 6px; }
        """)
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(10, 6, 10, 6)
        t = QLabel(f"[{title}]")
        t.setStyleSheet("color: #5B6CF6; font-weight: bold; font-size: 13px; background: transparent;")
        lay.addWidget(t)
        lay.addWidget(content_label)
        return frame

    # ──────────────────────────────────────────
    def _load_players(self):
        race = self.cmb_race.currentText() if hasattr(self, "cmb_race") else "전체"
        players = _load_players(race)
        self._rebuild_grid(players)

    def _rebuild_grid(self, players: list[dict]):
        # 기존 카드 제거
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        cols = 4
        for idx, p in enumerate(players):
            card = PlayerCard(p, selected=(
                p["id"] == self._selected_a or p["id"] == self._selected_b
            ))
            card.mousePressEvent = lambda e, pid=p["id"]: self._on_card_click(pid)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            self._cards[p["id"]] = card
            self.grid_layout.addWidget(card, idx // cols, idx % cols)

        # 빈 공간 채우기
        self.grid_layout.setRowStretch(len(players) // cols + 1, 1)

    def _on_filter_changed(self, race: str):
        self._load_players()

    def _on_card_click(self, player_id: int):
        players = _load_players()
        player = next((p for p in players if p["id"] == player_id), None)
        if player is None:
            return

        # 이미 선택된 경우 해제
        if player_id == self._selected_a:
            self._selected_a = None
            self.lbl_sel_a.setText("미선택")
            self.lbl_sel_a.setStyleSheet("color: #868E96; font-size: 13px; background: transparent;")
        elif player_id == self._selected_b:
            self._selected_b = None
            self.lbl_sel_b.setText("미선택")
            self.lbl_sel_b.setStyleSheet("color: #868E96; font-size: 13px; background: transparent;")
        elif self._selected_a is None:
            self._selected_a = player_id
            self.lbl_sel_a.setText(f"{player['name']} ({player['race']})")
            color = RACE_COLORS.get(player["race"], "#ffffff")
            self.lbl_sel_a.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold; background: transparent;")
        elif self._selected_b is None:
            if player_id == self._selected_a:
                return
            self._selected_b = player_id
            self.lbl_sel_b.setText(f"{player['name']} ({player['race']})")
            color = RACE_COLORS.get(player["race"], "#ffffff")
            self.lbl_sel_b.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold; background: transparent;")

        # 카드 선택 상태 갱신
        for pid, card in self._cards.items():
            card.set_selected(pid == self._selected_a or pid == self._selected_b)

        self.btn_proceed.setEnabled(
            self._selected_a is not None and self._selected_b is not None
        )

    def _on_proceed(self):
        if self._selected_a and self._selected_b:
            self.sig_proceed.emit(self._selected_a, self._selected_b)

    def refresh(self):
        """화면 복귀 시 데이터 새로고침"""
        self._selected_a = None
        self._selected_b = None
        self.lbl_sel_a.setText("미선택")
        self.lbl_sel_b.setText("미선택")
        self.lbl_sel_a.setStyleSheet("color: #868E96; font-size: 13px; background: transparent;")
        self.lbl_sel_b.setStyleSheet("color: #868E96; font-size: 13px; background: transparent;")
        self.btn_proceed.setEnabled(False)
        self._load_players()
