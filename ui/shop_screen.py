"""아이템 상점 화면 — 아이템 타입 탭 필터 추가"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QMessageBox, QTabBar, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from database.db import get_connection, get_gold  # set_gold는 _buy_item 내부 트랜잭션으로 대체됨
from ui.widgets import make_separator
from ui.styles import RACE_DISPLAY

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
    """BUG-07 수정: 골드 조회·아이템 삽입·골드 차감을 단일 트랜잭션으로 원자화.
    이전 구현(조회→INSERT→차감 분리)은 INSERT 성공 후 예외 시 무료 아이템이 되거나
    중복 조회로 골드가 부정확하게 계산되는 TOCTOU 문제가 있었음.
    """
    with get_connection() as conn:
        # 단일 트랜잭션: 조회 + 삽입 + 차감
        gold_row = conn.execute(
            "SELECT value FROM game_state WHERE key='gold'"
        ).fetchone()
        gold = int(gold_row["value"]) if gold_row else 0

        if gold < price:
            return f"골드가 부족합니다. (보유: {gold}G, 필요: {price}G)"

        cnt = conn.execute(
            "SELECT COUNT(*) FROM player_items WHERE player_id=?", (player_id,)
        ).fetchone()[0]
        if cnt >= MAX_ITEMS:
            return f"선수당 최대 {MAX_ITEMS}개 아이템만 장착 가능합니다."

        conn.execute(
            "INSERT INTO player_items (player_id, item_id) VALUES (?,?)",
            (player_id, item_id)
        )
        conn.execute(
            "UPDATE game_state SET value=? WHERE key='gold'",
            (str(gold - price),)
        )
        conn.commit()
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
        self.cmb_player.currentIndexChanged.connect(self._update_equipped_panel)
        buy_row.addWidget(self.cmb_player)
        buy_row.addStretch()

        # 장착 아이템 현황 패널
        self.equipped_frame = QFrame()
        self.equipped_frame.setStyleSheet(
            "QFrame { background: #F8F9FA; border: 1px solid #E9ECEF; border-radius: 6px; }"
        )
        eq_lay = QHBoxLayout(self.equipped_frame)
        eq_lay.setContentsMargins(12, 6, 12, 6)
        eq_lay.setSpacing(6)
        eq_title = QLabel("장착 슬롯:")
        eq_title.setStyleSheet(
            "color: #868E96; font-size: 12px; font-weight: bold; background: transparent;"
        )
        eq_lay.addWidget(eq_title)
        self.lbl_equipped_slots: list[QLabel] = []
        for _ in range(MAX_ITEMS):
            lbl = QLabel("— 비어있음")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setMinimumWidth(140)
            lbl.setStyleSheet(
                "color: #ADB5BD; font-size: 12px; background: #FFFFFF; "
                "border: 1px solid #E9ECEF; border-radius: 4px; padding: 3px 8px;"
            )
            self.lbl_equipped_slots.append(lbl)
            eq_lay.addWidget(lbl)
        eq_lay.addStretch()

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
        root.addWidget(self.equipped_frame)
        root.addWidget(self.table, 1)
        root.addLayout(btn_row)

    # ──────────────────────────────────────────
    def _on_tab_changed(self, idx: int):
        self._current_type = ITEM_TYPES[idx] if idx < len(ITEM_TYPES) else "전체"
        self._reload_table()

    def refresh(self):
        self._players = _load_players()
        self.lbl_gold.setText(f"보유 골드: {get_gold()} G")

        self.cmb_player.blockSignals(True)
        self.cmb_player.clear()
        for p in self._players:
            cnt = _count_player_items(p["id"])
            self.cmb_player.addItem(f"{p['name']}  ({RACE_DISPLAY.get(p['race'], p['race'])})  [{cnt}/{MAX_ITEMS}]")
        self.cmb_player.blockSignals(False)

        self._update_equipped_panel()
        self._reload_table()

    def _update_equipped_panel(self):
        """선택된 선수의 장착 아이템 슬롯 패널을 갱신한다."""
        player_idx = self.cmb_player.currentIndex()
        if player_idx < 0 or player_idx >= len(self._players):
            for lbl in self.lbl_equipped_slots:
                lbl.setText("— 비어있음")
                lbl.setStyleSheet(
                    "color: #ADB5BD; font-size: 12px; background: #FFFFFF; "
                    "border: 1px solid #E9ECEF; border-radius: 4px; padding: 3px 8px;"
                )
            return
        player = self._players[player_idx]
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT i.name FROM player_items pi
                   JOIN items i ON i.id = pi.item_id
                   WHERE pi.player_id = ?""",
                (player["id"],),
            ).fetchall()
        item_names = [r["name"] for r in rows]
        for i, lbl in enumerate(self.lbl_equipped_slots):
            if i < len(item_names):
                lbl.setText(f"✓ {item_names[i]}")
                lbl.setStyleSheet(
                    "color: #15803D; font-size: 12px; background: #F0FDF4; "
                    "border: 1px solid #BBF7D0; border-radius: 4px; padding: 3px 8px;"
                )
            else:
                lbl.setText("— 비어있음")
                lbl.setStyleSheet(
                    "color: #ADB5BD; font-size: 12px; background: #FFFFFF; "
                    "border: 1px solid #E9ECEF; border-radius: 4px; padding: 3px 8px;"
                )

    def _reload_table(self):
        self._items = _load_items(self._current_type)
        current_gold = get_gold()   # 가격 셀 색상 결정을 위해 미리 조회
        self.table.setRowCount(0)
        for item in self._items:
            row = self.table.rowCount()
            self.table.insertRow(row)

            itype = item.get("item_type", "능력치")
            # 타입별 특수 표시
            extra_cond = item.get("condition_up", 0)
            extra_fat  = item.get("fatigue_recover", 0)

            # 아이템 툴팁 문자열 생성
            tip_lines = [f"【{item['name']}】  {itype}  |  {item['price']}G",
                         "", item["description"], ""]
            bonus_parts = []
            for key, label in zip(STAT_KEYS, STAT_LABELS):
                v = item.get(f"{key}_bonus", 0)
                if v > 0:
                    bonus_parts.append(f"{label} +{v}")
            if bonus_parts:
                tip_lines.append("능력치 효과: " + " · ".join(bonus_parts))
            if extra_cond > 0:
                tip_lines.append("컨디션 1단계 상향 (저조→보통→최상)")
            if extra_fat > 0:
                tip_lines.append("피로도 1구간 회복 (81~100→60 / 61~80→30 / 31~60→0)")
            tooltip_text = "\n".join(tip_lines)

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
                ti.setToolTip(tooltip_text)
                if ci >= 4 and isinstance(val, int) and val > 0:
                    ti.setForeground(QColor("#51CF66"))
                    ti.setText(f"+{val}")
                # 가격 컬럼: 골드 부족 시 빨간색
                if ci == 3:
                    if item["price"] > current_gold:
                        ti.setForeground(QColor("#FF6B6B"))
                    else:
                        ti.setForeground(QColor("#212529"))
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

        # 구매 확인 다이얼로그 — 실수 클릭으로 골드 소비 방지
        reply = QMessageBox.question(
            self,
            "구매 확인",
            f"[{item['name']}]을 {player['name']}에게 구매하시겠습니까?\n\n"
            f"가격: {item['price']} G  |  현재 보유: {get_gold():,} G",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # QA-SHOP-BTN 수정: 구매 처리 중 버튼 즉시 비활성화 → 연타 방지.
        # _buy_item()은 단일 트랜잭션(BUG-07 수정)이지만, QMessageBox 표시 전에
        # 버튼이 활성 상태로 남아 연타 클릭 시 중복 구매 시도가 발생할 수 있었음.
        self.btn_buy.setEnabled(False)
        try:
            err = _buy_item(player["id"], item["id"], item["price"])
        finally:
            self.btn_buy.setEnabled(True)   # 결과와 무관하게 복원

        if err:
            QMessageBox.warning(self, "구매 실패", err)
        else:
            QMessageBox.information(
                self, "구매 완료",
                f"{player['name']}에게 [{item['name']}]을 장착했습니다.\n"
                f"잔여 골드: {get_gold():,} G"
            )
            self.refresh()
            self._update_equipped_panel()
