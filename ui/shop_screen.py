"""아이템 상점 화면 — 아이템 타입 탭 필터 추가"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QMessageBox, QTabBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from database.db import get_connection, get_gold, set_gold
from ui.widgets import make_separator

STAT_KEYS   = ["control", "attack", "defense", "supply", "strategy", "sense"]
STAT_LABELS = ["컨트롤", "공격력", "수비력", "물량", "전략", "센스"]
MAX_ITEMS   = 3

ITEM_TYPES = ["전체", "능력치", "컨디션", "피로회복"]


def _load_items(item_type: str = "전체") -> list[dict]:
    with get_connection() as conn:
        if item_type == "전체":
            rows = conn.execute("SELECT * FROM items ORDER BY price").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM items WHERE item_type=? ORDER BY price",
                (item_type,)
            ).fetchall()
    return [dict(r) for r in rows]


def _load_players() -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id, name, race FROM players ORDER BY name"
        ).fetchall()]


def _count_player_items(player_id: int) -> int:
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM player_items WHERE player_id=?", (player_id,)
        ).fetchone()[0]


def _buy_item(player_id: int, item_id: int, price: int) -> str | None:
    gold = get_gold()
    if gold < price:
        return f"골드가 부족합니다. (보유: {gold}G, 필요: {price}G)"
    if _count_player_items(player_id) >= MAX_ITEMS:
        return f"선수당 최대 {MAX_ITEMS}개 아이템만 장착 가능합니다."
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO player_items (player_id, item_id) VALUES (?,?)",
            (player_id, item_id)
        )
        conn.commit()
    set_gold(gold - price)
    return None


class ShopScreen(QWidget):
    sig_back = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict] = []
        self._players: list[dict] = []
        self._current_type: str = "전체"
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # 헤더
        hdr = QHBoxLayout()
        title = QLabel("아이템 상점")
        title.setStyleSheet(
            "color: #212529; font-size: 22px; font-weight: bold; background: transparent;"
        )
        self.btn_back = QPushButton("← 돌아가기")
        self.btn_back.clicked.connect(self.sig_back)
        hdr.addWidget(title)
        hdr.addStretch()
        self.lbl_gold = QLabel("")
        self.lbl_gold.setStyleSheet(
            "color: #F59E0B; font-weight: bold; font-size: 15px; background: transparent;"
        )
        hdr.addWidget(self.lbl_gold)
        hdr.addSpacing(16)
        hdr.addWidget(self.btn_back)

        # 타입 탭 필터
        self.tab_bar = QTabBar()
        self.tab_bar.setStyleSheet("""
            QTabBar::tab {
                background: #F8F9FA; color: #868E96;
                border: none; border-bottom: 2px solid transparent;
                padding: 6px 18px; margin-right: 4px; font-size: 12px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #F8F9FA; color: #5B6CF6;
                border-bottom: 2px solid #5B6CF6;
            }
            QTabBar::tab:hover { color: #5B6CF6; }
        """)
        for t in ITEM_TYPES:
            self.tab_bar.addTab(t)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)

        # 장착 선수 선택
        buy_row = QHBoxLayout()
        buy_row.addWidget(QLabel("장착 선수:"))
        self.cmb_player = QComboBox()
        self.cmb_player.setMinimumWidth(160)
        buy_row.addWidget(self.cmb_player)
        buy_row.addStretch()

        # 아이템 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ["아이템명", "유형", "설명", "가격",
             "컨트롤", "공격력", "수비력", "물량", "전략", "센스"]
        )
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 65)
        for c in range(4, 10):
            self.table.setColumnWidth(c, 58)

        # 구매 버튼
        btn_row = QHBoxLayout()
        self.btn_buy = QPushButton("💰  구매")
        self.btn_buy.setProperty("class", "primary")
        self.btn_buy.setMinimumWidth(140)
        self.btn_buy.clicked.connect(self._on_buy)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_buy)

        root.addLayout(hdr)
        root.addWidget(make_separator())
        root.addWidget(self.tab_bar)
        root.addLayout(buy_row)
        root.addWidget(self.table, 1)
        root.addLayout(btn_row)

    # ──────────────────────────────────────────
    def _on_tab_changed(self, idx: int):
        self._current_type = ITEM_TYPES[idx] if idx < len(ITEM_TYPES) else "전체"
        self._reload_table()

    def refresh(self):
        self._players = _load_players()
        self.lbl_gold.setText(f"보유 골드: {get_gold()} G")

        self.cmb_player.clear()
        for p in self._players:
            cnt = _count_player_items(p["id"])
            self.cmb_player.addItem(f"{p['name']}  ({p['race']})  [{cnt}/{MAX_ITEMS}]")

        self._reload_table()

    def _reload_table(self):
        self._items = _load_items(self._current_type)
        self.table.setRowCount(0)
        for item in self._items:
            row = self.table.rowCount()
            self.table.insertRow(row)

            itype = item.get("item_type", "능력치")
            # 타입별 특수 표시
            extra_cond = item.get("condition_up", 0)
            extra_fat  = item.get("fatigue_recover", 0)

            cols = [
                item["name"],
                itype,
                item["description"],
                f"{item['price']}G",
                item["control_bonus"],
                item["attack_bonus"],
                item["defense_bonus"],
                item["supply_bonus"],
                item["strategy_bonus"],
                item["sense_bonus"],
            ]
            for ci, val in enumerate(cols):
                ti = QTableWidgetItem(str(val))
                ti.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if ci >= 4 and isinstance(val, int) and val > 0:
                    ti.setForeground(QColor("#51CF66"))
                    ti.setText(f"+{val}")
                # 유형 컬럼 색상
                if ci == 1:
                    type_color = {
                        "능력치": "#5B6CF6",
                        "컨디션": "#51CF66",
                        "피로회복": "#F59E0B",
                    }.get(itype, "#212529")
                    ti.setForeground(QColor(type_color))
                self.table.setItem(row, ci, ti)

    def _on_buy(self):
        sel = self.table.selectedItems()
        if not sel:
            QMessageBox.warning(self, "상점", "아이템을 선택하세요.")
            return
        row = self.table.currentRow()
        if row < 0 or row >= len(self._items):
            return
        item = self._items[row]

        player_idx = self.cmb_player.currentIndex()
        if player_idx < 0:
            return
        player = self._players[player_idx]

        err = _buy_item(player["id"], item["id"], item["price"])
        if err:
            QMessageBox.warning(self, "구매 실패", err)
        else:
            QMessageBox.information(
                self, "구매 완료",
                f"{player['name']}에게 [{item['name']}]을 장착했습니다.\n"
                f"잔여 골드: {get_gold()} G"
            )
            self.refresh()
