"""토너먼트 대진표 화면 — 브라켓 시각화"""
import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics
)

from core.tournament import (
    ROUNDS, get_all_matches, get_my_pending_match,
    is_round_complete, simulate_ai_matches
)
from core.balance import is_rival
from database.db import get_connection, get_gold
from ui.styles import RACE_COLORS, GRADE_STYLE
from ui.widgets import make_separator

# ── 브라켓 레이아웃 상수 ──────────────────────────
UNIT      = 28      # 선수 이름 1행 높이 (px)
MATCH_H   = UNIT * 2 + 4   # 매치 박스 높이 = 60px
MATCH_W   = 170     # 매치 박스 너비
COL_GAP   = 55      # 열 간격
COL_STEP  = MATCH_W + COL_GAP   # = 225
PAD       = 24      # 상하좌우 패딩

# 8개 16강 경기의 Y 중심점 (px)
R1_STEP   = MATCH_H + UNIT  # = 88  (간격 포함)
R1_C = [PAD + MATCH_H // 2 + i * R1_STEP for i in range(8)]
# = [50, 138, 226, 314, 402, 490, 578, 666]

R2_C = [(R1_C[2*i] + R1_C[2*i+1]) // 2 for i in range(4)]
R3_C = [(R2_C[2*i] + R2_C[2*i+1]) // 2 for i in range(2)]
R4_C = [(R3_C[0] + R3_C[1]) // 2]

ALL_C = [R1_C, R2_C, R3_C, R4_C]  # [round_idx][match_idx]
COL_X = [PAD + r * COL_STEP for r in range(4)]

CANVAS_H = R1_C[-1] + MATCH_H // 2 + PAD   # ≈ 718
CANVAS_W = COL_X[-1] + MATCH_W + PAD        # ≈ 882

# 색상 — 라이트 테마
C_BG      = QColor("#F8F9FA")
C_BOX     = QColor("#FFFFFF")
C_BORDER  = QColor("#E9ECEF")
C_MY      = QColor("#5B6CF6")
C_WIN     = QColor("#51CF66")
C_LOSE    = QColor("#FF6B6B")
C_TEXT    = QColor("#212529")
C_DIM     = QColor("#CED4DA")
C_LINE    = QColor("#DEE2E6")


class BracketCanvas(QWidget):
    """브라켓을 직접 그리는 캔버스 위젯"""
    sig_player_clicked = pyqtSignal(int)   # player_id — 선수 행 클릭 시 방출

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(CANVAS_W, CANVAS_H)
        self._data: dict[str, list[dict]] = {}
        self._my_id: int | None = None
        # ─── BUG FIX: paintEvent는 마우스 이동 등 매 갱신마다 호출됨.
        #     DB 연결을 paintEvent 내부에서 직접 열면 성능 저하 및 드문 경우
        #     충돌 원인이 됨 → set_data() 시 모든 선수 이름을 캐싱.
        self._name_cache: dict[int, str] = {}
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_data(self, data: dict[str, list[dict]], my_id: int):
        self._data = data
        self._my_id = my_id
        self._preload_names()   # DB 일괄 조회 → 캐시 갱신
        self.update()

    def _preload_names(self):
        """모든 매치의 선수 ID를 모아 DB에서 한 번에 조회 후 캐시에 저장"""
        pids: set[int] = set()
        for matches in self._data.values():
            for m in matches:
                for key in ("player_a_id", "player_b_id", "winner_id"):
                    v = m.get(key)
                    if v:
                        pids.add(v)
        if not pids:
            self._name_cache = {}
            return
        with get_connection() as conn:
            placeholders = ",".join("?" * len(pids))
            rows = conn.execute(
                f"SELECT id, name FROM players WHERE id IN ({placeholders})",
                list(pids),
            ).fetchall()
        self._name_cache = {r["id"]: r["name"] for r in rows}

    # ── 데이터 접근 헬퍼 ──────────────────────────
    def _get_match(self, round_idx: int, match_idx: int) -> dict | None:
        rnd = ROUNDS[round_idx]
        ms = self._data.get(rnd, [])
        if match_idx < len(ms):
            return ms[match_idx]
        return None

    def _player_name(self, player_id: int | None) -> str:
        if player_id is None:
            return "?"
        return self._name_cache.get(player_id, "?")

    # ── 클릭 이벤트 ──────────────────────────────
    def mousePressEvent(self, event):
        pid = self._find_player_at(event.pos().x(), event.pos().y())
        if pid is not None:
            self.sig_player_clicked.emit(pid)
        super().mousePressEvent(event)

    def _find_player_at(self, x: float, y: float) -> int | None:
        """클릭 좌표가 어느 선수 행 위인지 검사, 해당 player_id 반환"""
        counts = [8, 4, 2, 1]
        for r_idx in range(4):
            for m_idx in range(counts[r_idx]):
                m = self._get_match(r_idx, m_idx)
                if m is None:
                    continue
                cx  = COL_X[r_idx]
                cy  = ALL_C[r_idx][m_idx]
                top = cy - MATCH_H // 2

                # 선수 A 행
                if cx <= x <= cx + MATCH_W and top <= y <= top + UNIT:
                    pid = m.get("player_a_id")
                    if pid:
                        return pid
                # 선수 B 행
                b_top = top + UNIT + 4
                if cx <= x <= cx + MATCH_W and b_top <= y <= b_top + UNIT:
                    pid = m.get("player_b_id")
                    if pid:
                        return pid
        return None

    # ── 페인트 ────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(0, 0, CANVAS_W, CANVAS_H, C_BG)

        # 라운드 헤더
        self._draw_headers(p)

        # 연결선 (배경 먼저)
        self._draw_connectors(p)

        # 매치 박스
        for r_idx in range(4):
            count = [8, 4, 2, 1][r_idx]
            for m_idx in range(count):
                self._draw_match(p, r_idx, m_idx)

        p.end()

    def _draw_headers(self, p: QPainter):
        headers = ["16강", "8강", "4강", "결승"]
        font = QFont("맑은 고딕", 10, QFont.Weight.Bold)
        p.setFont(font)
        for r, label in enumerate(headers):
            x = COL_X[r]
            rect = QRectF(x, 0, MATCH_W, PAD - 2)
            p.setPen(QPen(QColor("#868E96")))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_connectors(self, p: QPainter):
        """이전 라운드 → 다음 라운드 L자형 연결선"""
        pen = QPen(C_LINE, 1)
        pen.setStyle(Qt.PenStyle.SolidLine)
        p.setPen(pen)

        for r_idx in range(3):
            count = [8, 4, 2][r_idx]
            for m_idx in range(count):
                m = self._get_match(r_idx, m_idx)
                if m is None:
                    continue

                src_cx  = ALL_C[r_idx][m_idx]
                src_rx  = COL_X[r_idx] + MATCH_W      # 현재 박스 오른쪽
                mid_x   = src_rx + COL_GAP // 2       # 중간점 X

                next_m_idx = m_idx // 2
                dst_cy  = ALL_C[r_idx + 1][next_m_idx]
                dst_lx  = COL_X[r_idx + 1]            # 다음 박스 왼쪽

                # 플레이어 슬롯 Y (A=top, B=bottom)
                is_upper = (m_idx % 2 == 0)
                if is_upper:
                    dst_slot_y = dst_cy - UNIT // 2
                else:
                    dst_slot_y = dst_cy + UNIT // 2 + 4

                # 이긴 선수가 있으면 색상 강조
                if m.get('winner_id'):
                    line_color = C_WIN
                else:
                    line_color = C_LINE
                p.setPen(QPen(line_color, 1))

                # ├── horizontal ──┬── vertical ──┬── horizontal
                p.drawLine(QPointF(src_rx, src_cx),   QPointF(mid_x, src_cx))
                p.drawLine(QPointF(mid_x, src_cx),    QPointF(mid_x, dst_slot_y))
                p.drawLine(QPointF(mid_x, dst_slot_y), QPointF(dst_lx, dst_slot_y))

    def _draw_match(self, p: QPainter, r_idx: int, m_idx: int):
        m = self._get_match(r_idx, m_idx)
        cx  = COL_X[r_idx]
        cy  = ALL_C[r_idx][m_idx]
        top = cy - MATCH_H // 2

        rect = QRectF(cx, top, MATCH_W, MATCH_H)

        # 박스 상태 판별
        is_my   = m and bool(m.get('is_my_match'))
        completed = m and m.get('status') == 'completed'
        a_id    = m.get('player_a_id') if m else None
        b_id    = m.get('player_b_id') if m else None
        is_rival_m = bool(a_id and b_id and is_rival(a_id, b_id))

        # 배경색: 내 경기(인디고) > 라이벌(연분홍) > 완료(연초록) > 기본(흰색)
        if is_my:
            box_color = QColor("#EEF2FF")
        elif is_rival_m:
            box_color = QColor("#FFF5F5")
        elif completed:
            box_color = QColor("#F0FDF4")
        else:
            box_color = C_BOX

        # 테두리색: 내 경기=인디고, 라이벌=빨강, 완료=초록, 기본=회색
        if is_my:
            border_color, border_w = C_MY, 2
        elif is_rival_m:
            border_color, border_w = QColor("#FF6B6B"), 2
        elif completed:
            border_color, border_w = C_WIN, 1
        else:
            border_color, border_w = C_BORDER, 1

        p.setBrush(QBrush(box_color))
        p.setPen(QPen(border_color, border_w))
        p.drawRoundedRect(rect, 4, 4)

        if m is None:
            return

        w_id = m.get('winner_id')

        self._draw_player_row(p, cx, top,             a_id, w_id, is_my)
        self._draw_player_row(p, cx, top + UNIT + 4,  b_id, w_id, is_my)

        # 구분선
        p.setPen(QPen(C_BORDER, 1))
        p.drawLine(QPointF(cx + 4, top + UNIT + 2),
                   QPointF(cx + MATCH_W - 4, top + UNIT + 2))

        # 세트 스코어 표시 (완료된 경기)
        if completed and m.get('a_wins', 0) + m.get('b_wins', 0) > 1:
            score_font = QFont("맑은 고딕", 8)
            p.setFont(score_font)
            p.setPen(QPen(C_WIN))
            score_str = f"{m['a_wins']}-{m['b_wins']}"
            p.drawText(
                QRectF(cx, top + MATCH_H - UNIT + 4, MATCH_W - 4, UNIT - 6),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                score_str + " "
            )

        # 라이벌 아이콘 (두 선수가 라이벌 관계일 때 🔥 표시)
        if a_id and b_id and is_rival(a_id, b_id):
            rival_font = QFont("Segoe UI Emoji", 10)
            p.setFont(rival_font)
            p.setPen(QPen(QColor("#FF6B6B")))
            p.drawText(
                QRectF(cx + MATCH_W - 22, top, 20, MATCH_H),
                Qt.AlignmentFlag.AlignCenter,
                "🔥"
            )

    def _draw_player_row(self, p: QPainter, bx: float, by: float,
                          player_id: int | None, winner_id: int | None,
                          is_my_match: bool):
        row_rect = QRectF(bx + 2, by, MATCH_W - 4, UNIT)

        name = self._player_name(player_id)
        is_winner   = (winner_id is not None and player_id == winner_id)
        is_loser    = (winner_id is not None and player_id != winner_id and player_id is not None)
        is_my_player = (player_id == self._my_id)

        # 이름 색상 결정
        if is_winner and is_my_player:
            color = C_MY
        elif is_winner:
            color = C_WIN
        elif is_loser:
            color = C_LOSE
        elif is_my_player:
            color = C_MY
        elif player_id is None:
            color = C_DIM
        else:
            color = C_TEXT

        font = QFont("맑은 고딕", 9)
        if is_winner or is_my_player:
            font.setBold(True)
        p.setFont(font)
        p.setPen(QPen(color))

        # 승자에게 ★ 접두어
        display = ("★ " if is_winner else "") + name
        p.drawText(row_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   "  " + display)


# ──────────────────────────────────────────────────────
class BracketScreen(QWidget):
    sig_prep_match = pyqtSignal()   # 내 경기 준비 버튼
    sig_back       = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tid: int | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # 헤더
        hdr = QHBoxLayout()
        self.lbl_title = QLabel("토너먼트 대진표")
        self.lbl_title.setStyleSheet(
            "color: #212529; font-size: 20px; font-weight: bold; background: transparent;"
        )
        self.lbl_gold = QLabel("")
        self.lbl_gold.setStyleSheet(
            "color: #F59E0B; font-size: 13px; font-weight: bold; background: transparent;"
        )
        btn_back = QPushButton("← 메인으로")
        btn_back.clicked.connect(self.sig_back)
        hdr.addWidget(self.lbl_title)
        hdr.addStretch()
        hdr.addWidget(self.lbl_gold)
        hdr.addSpacing(16)
        hdr.addWidget(btn_back)

        # 상태 안내
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet(
            "color: #5B6CF6; font-size: 13px; font-weight: bold; background: transparent;"
        )

        # 브라켓 캔버스 (스크롤 가능)
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self.canvas = BracketCanvas()
        self.canvas.sig_player_clicked.connect(self._on_player_clicked)
        scroll.setWidget(self.canvas)

        # 하단 버튼
        btn_row = QHBoxLayout()
        self.btn_ai = QPushButton("⚡  AI 경기 자동 진행")
        self.btn_ai.setMinimumHeight(42)
        self.btn_ai.clicked.connect(self._on_run_ai)

        self.btn_prep = QPushButton("⚔  내 경기 준비하기")
        self.btn_prep.setProperty("class", "primary")
        self.btn_prep.setMinimumHeight(42)
        self.btn_prep.setEnabled(False)
        self.btn_prep.clicked.connect(self.sig_prep_match)

        btn_row.addWidget(self.btn_ai)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_prep)

        root.addLayout(hdr)
        root.addWidget(make_separator())
        root.addWidget(self.lbl_status)
        root.addWidget(scroll, 1)
        root.addWidget(make_separator())
        root.addLayout(btn_row)

    # ──────────────────────────────────────────
    def load_tournament(self, tid: int, my_id: int):
        self._tid  = tid
        self._my_id = my_id
        self.refresh()

    def refresh(self):
        if self._tid is None:
            return
        data = get_all_matches(self._tid)
        self.canvas.set_data(data, self._my_id)
        self.lbl_gold.setText(f"Gold: {get_gold()} G")
        self._update_controls()

    def _update_controls(self):
        if self._tid is None:
            return
        my_match = get_my_pending_match(self._tid)
        all_ai_done = self._all_ai_done()

        if my_match and all_ai_done:
            self.lbl_status.setText("⚔ 내 경기 차례입니다! 준비하세요.")
            self.btn_prep.setEnabled(True)
            self.btn_ai.setEnabled(False)
        elif my_match and not all_ai_done:
            self.lbl_status.setText("먼저 AI 경기를 진행해주세요.")
            self.btn_prep.setEnabled(False)
            self.btn_ai.setEnabled(True)
        else:
            self.lbl_status.setText("이번 라운드 경기가 완료되었습니다.")
            self.btn_prep.setEnabled(False)
            self.btn_ai.setEnabled(False)

    def _all_ai_done(self) -> bool:
        """AI 경기가 모두 완료됐는지"""
        if self._tid is None:
            return True
        from core.tournament import get_tournament
        t = get_tournament(self._tid)
        if not t:
            return True
        data = get_all_matches(self._tid)
        matches = data.get(t['current_round'], [])
        return all(
            m['status'] == 'completed' or m['is_my_match']
            for m in matches
        )

    def _on_player_clicked(self, player_id: int):
        """브라켓 선수 행 클릭 → 프로필 팝업"""
        from ui.player_profile_dialog import PlayerProfileDialog
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
        if row:
            dlg = PlayerProfileDialog(dict(row), self)
            dlg.exec()

    def _on_run_ai(self):
        if self._tid is None:
            return
        simulate_ai_matches(self._tid)
        self.refresh()
