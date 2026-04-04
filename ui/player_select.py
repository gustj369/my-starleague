"""내 선수 선택 화면 — 16강 시작 전 대표 선수 1명 선택"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QComboBox, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal

from database.db import get_connection
from ui.widgets import PlayerCard, make_separator
from ui.styles import RACE_COLORS, GRADE_STYLE


def _load_all_players(sort_by: str = "overall") -> list[dict]:
    valid = {"overall": "overall DESC", "grade": "overall DESC", "name": "name ASC"}
    order = valid.get(sort_by, "overall DESC")
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            f"SELECT * FROM players ORDER BY {order}"
        ).fetchall()]


class PlayerSelectScreen(QWidget):
    sig_confirm = pyqtSignal(int)   # my_player_id
    sig_back    = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_id: int | None = None
        self._cards: dict[int, PlayerCard] = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # 헤더
        hdr = QHBoxLayout()
        btn_back = QPushButton("← 메인 메뉴")
        btn_back.clicked.connect(self.sig_back)

        title = QLabel("내 선수 선택")
        title.setStyleSheet(
            "color: #ffd700; font-size: 22px; font-weight: bold; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hdr.addWidget(btn_back)
        hdr.addWidget(title, 1)
        hdr.addSpacing(btn_back.sizeHint().width())

        # 안내
        hint = QLabel(
            "16강 토너먼트에서 조종할 선수를 선택하세요.\n"
            "나머지 15명은 AI가 자동 조작합니다."
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #7a9ab8; font-size: 12px; background: transparent;")

        # 필터
        filter_row = QHBoxLayout()
        filter_row.addStretch()
        filter_row.addWidget(QLabel("종족:"))
        self.cmb_race = QComboBox()
        self.cmb_race.addItems(["전체", "테란", "저그", "프로토스"])
        self.cmb_race.currentTextChanged.connect(self._rebuild)
        filter_row.addWidget(self.cmb_race)
        filter_row.addSpacing(16)
        filter_row.addWidget(QLabel("정렬:"))
        self.cmb_sort = QComboBox()
        self.cmb_sort.addItems(["OVR 높은순", "이름순"])
        self.cmb_sort.currentIndexChanged.connect(self._rebuild)
        filter_row.addWidget(self.cmb_sort)
        filter_row.addSpacing(16)
        btn_random = QPushButton("🎲  랜덤 선택")
        btn_random.setFixedHeight(30)
        btn_random.setStyleSheet("""
            QPushButton { background: #1a3a6a; color: #c8d8e8; border: 1px solid #1e3a5f;
                          border-radius: 3px; font-size: 12px; padding: 0 12px; }
            QPushButton:hover { border-color: #4fc3f7; color: #ffd700; }
        """)
        btn_random.clicked.connect(self._on_random)
        filter_row.addWidget(btn_random)
        filter_row.addStretch()

        # 선택 표시 + 확인 버튼
        sel_row = QHBoxLayout()
        self.lbl_selected = QLabel("선수를 선택하세요")
        self.lbl_selected.setStyleSheet(
            "color: #4a6a8a; font-size: 14px; background: transparent;"
        )
        self.lbl_selected.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_confirm = QPushButton("▶  이 선수로 시작!")
        self.btn_confirm.setProperty("class", "primary")
        self.btn_confirm.setMinimumHeight(46)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self._on_confirm)

        sel_row.addWidget(self.lbl_selected, 1)
        sel_row.addSpacing(20)
        sel_row.addWidget(self.btn_confirm)

        # 선수 그리드
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; }")
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(10)
        self.scroll.setWidget(self.grid_widget)

        root.addLayout(hdr)
        root.addWidget(make_separator())
        root.addWidget(hint)
        root.addLayout(filter_row)
        root.addWidget(make_separator())
        root.addLayout(sel_row)
        root.addWidget(self.scroll, 1)

    # ──────────────────────────────────────────
    def refresh(self):
        self._selected_id = None
        self.lbl_selected.setText("선수를 선택하세요")
        self.lbl_selected.setStyleSheet("color: #4a6a8a; font-size: 14px; background: transparent;")
        self.btn_confirm.setEnabled(False)
        self._rebuild()

    def _rebuild(self):
        race = self.cmb_race.currentText() if hasattr(self, "cmb_race") else "전체"
        sort_idx = self.cmb_sort.currentIndex() if hasattr(self, "cmb_sort") else 0
        sort_by = ["overall", "name"][sort_idx] if sort_idx < 2 else "overall"
        players = _load_all_players(sort_by)
        if race != "전체":
            players = [p for p in players if p["race"] == race]

        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        cols = 4
        for idx, p in enumerate(players):
            card = PlayerCard(p, selected=(p["id"] == self._selected_id))
            card.mousePressEvent = lambda e, pid=p["id"]: self._on_card_click(pid)
            card.setCursor(Qt.CursorShape.PointingHandCursor)

            # 배지 추가 (핸디캡 / 업셋 보너스)
            grade = p.get("grade", "C")
            if grade in ("SSS", "SS"):
                badge = QLabel("⚠ 핸디캡", card)
                badge.setStyleSheet(
                    "background: #7B1FA2; color: #fff; font-size: 9px; "
                    "padding: 1px 4px; border-radius: 3px;"
                )
                badge.move(4, 4)
                badge.adjustSize()
            elif grade in ("B", "C", "D", "E", "F"):
                badge = QLabel("🔥 업셋보너스", card)
                badge.setStyleSheet(
                    "background: #1565C0; color: #fff; font-size: 9px; "
                    "padding: 1px 4px; border-radius: 3px;"
                )
                badge.move(4, 4)
                badge.adjustSize()

            self._cards[p["id"]] = card
            self.grid.addWidget(card, idx // cols, idx % cols)

        self.grid.setRowStretch(len(players) // cols + 1, 1)

    def _on_card_click(self, pid: int):
        players = _load_all_players()
        p = next((x for x in players if x["id"] == pid), None)
        if not p:
            return

        if self._selected_id == pid:
            # 이미 선택된 선수 클릭 → 확인으로 바로 진행
            self._on_confirm()
            return

        self._selected_id = pid
        color = RACE_COLORS.get(p["race"], "#fff")
        grade_str = GRADE_STYLE.get(p["grade"], "")
        self.lbl_selected.setText(
            f"선택: {p['name']}  ({p['race']})  ◆ {p['grade']}  OVR {p['overall']:.1f}"
        )
        self.lbl_selected.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold; background: transparent;")
        self.btn_confirm.setEnabled(True)

        for card_id, card in self._cards.items():
            card.set_selected(card_id == pid)

    def _on_random(self):
        import random as _random
        players = _load_all_players()
        race = self.cmb_race.currentText() if hasattr(self, "cmb_race") else "전체"
        if race != "전체":
            players = [p for p in players if p["race"] == race]
        if players:
            p = _random.choice(players)
            self._on_card_click(p["id"])

    def _on_confirm(self):
        if self._selected_id is not None:
            self.sig_confirm.emit(self._selected_id)
