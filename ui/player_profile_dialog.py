"""선수 프로필 팝업 다이얼로그"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from database.db import get_connection
from ui.widgets import get_player_image_path, make_separator
from ui.styles import GRADE_STYLE, RACE_COLORS, RACE_DISPLAY
from core.player_data import PLAYER_DATA
from core.utils import STAT_KEYS


def _load_stats(player_id: int) -> dict:
    """해당 선수의 전체 대결 통계 반환"""
    with get_connection() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as matches,
                      SUM(CASE WHEN winner_id = ? THEN 1 ELSE 0 END) as wins
               FROM match_results
               WHERE player_a_id = ? OR player_b_id = ?""",
            (player_id, player_id, player_id)
        ).fetchone()
    matches = row["matches"] or 0
    wins = row["wins"] or 0
    return {"matches": matches, "wins": wins, "losses": matches - wins}


class PlayerProfileDialog(QDialog):
    def __init__(self, player: dict, parent=None):
        super().__init__(parent)
        self._player = player
        self.setWindowTitle(f"{player['name']} — 선수 프로필")
        self.setMinimumWidth(420)
        self.setMinimumHeight(520)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        p = self._player
        pd = PLAYER_DATA.get(p["name"], {})
        stats = _load_stats(p["id"])

        # ── 이미지 + 기본 정보 ──
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        # 이미지
        img_lbl = QLabel()
        img_lbl.setFixedSize(110, 110)
        img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_path = get_player_image_path(p["name"])
        if img_path:
            px = QPixmap(img_path).scaled(
                110, 110,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            img_lbl.setPixmap(px)
            img_lbl.setStyleSheet(
                "border-radius: 55px; background: #EEF2FF; border: 2px solid #C5C8FF;"
            )
        else:
            img_lbl.setText(p["name"][:1])
            img_lbl.setStyleSheet(
                "background: #EEF2FF; color: #5B6CF6; font-size: 36px; "
                "font-weight: bold; border-radius: 55px; border: 2px solid #C5C8FF;"
            )

        # 이름 + 등급 + 종족
        info_col = QVBoxLayout()
        info_col.setSpacing(6)

        name_lbl = QLabel(p["name"])
        name_lbl.setStyleSheet(
            f"color: {RACE_COLORS.get(p['race'], '#fff')}; "
            f"font-size: 24px; font-weight: bold; background: transparent;"
        )

        grade = p["grade"]
        grade_lbl = QLabel(f"◆ {grade}   OVR {p['overall']:.1f}")
        grade_lbl.setStyleSheet(
            GRADE_STYLE.get(grade, "") + " font-size: 17px; background: transparent;"
        )

        race_lbl = QLabel(RACE_DISPLAY.get(p["race"], p["race"]))
        race_lbl.setStyleSheet(
            f"color: {RACE_COLORS.get(p['race'], '#fff')}; "
            f"font-size: 13px; background: transparent;"
        )

        style_lbl = QLabel(pd.get("style", ""))
        style_lbl.setStyleSheet(
            "color: #5B6CF6; font-size: 12px; font-style: italic; background: transparent;"
        )

        info_col.addWidget(name_lbl)
        info_col.addWidget(grade_lbl)
        info_col.addWidget(race_lbl)
        info_col.addWidget(style_lbl)
        info_col.addStretch()

        top_row.addWidget(img_lbl)
        top_row.addLayout(info_col, 1)
        root.addLayout(top_row)
        root.addWidget(make_separator())

        # ── 전적 ──
        rival_name = pd.get("rival", "없음")
        record_frame = QFrame()
        record_frame.setStyleSheet(
            "QFrame { background: #F8F9FA; border: 1px solid #E9ECEF; border-radius: 8px; }"
        )
        rec_lay = QHBoxLayout(record_frame)
        rec_lay.setContentsMargins(16, 10, 16, 10)
        rec_lay.setSpacing(0)

        win_rate = f"{stats['wins']/stats['matches']*100:.1f}%" if stats["matches"] > 0 else "—"

        for label, value, color in [
            ("전체 경기", str(stats["matches"]), "#212529"),
            ("승", str(stats["wins"]), "#51CF66"),
            ("패", str(stats["losses"]), "#FF6B6B"),
            ("승률", win_rate, "#F59E0B"),
        ]:
            col = QVBoxLayout()
            col.setSpacing(2)
            v_lbl = QLabel(value)
            v_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v_lbl.setStyleSheet(
                f"color: {color}; font-size: 20px; font-weight: bold; background: transparent;"
            )
            l_lbl = QLabel(label)
            l_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l_lbl.setStyleSheet("color: #868E96; font-size: 11px; background: transparent;")
            col.addWidget(v_lbl)
            col.addWidget(l_lbl)
            rec_lay.addLayout(col, 1)

        root.addWidget(record_frame)

        # ── 캐릭터 정보 ──
        char_frame = QFrame()
        char_frame.setStyleSheet(
            "QFrame { background: #F8F9FA; border: 1px solid #E9ECEF; border-radius: 8px; }"
        )
        char_lay = QVBoxLayout(char_frame)
        char_lay.setContentsMargins(16, 12, 16, 12)
        char_lay.setSpacing(8)

        def info_row(label: str, value: str, value_color: str = "#212529"):
            row = QHBoxLayout()
            l = QLabel(label)
            l.setFixedWidth(70)
            l.setStyleSheet("color: #868E96; font-size: 12px; background: transparent;")
            v = QLabel(value)
            v.setWordWrap(True)
            v.setStyleSheet(f"color: {value_color}; font-size: 12px; background: transparent;")
            row.addWidget(l)
            row.addWidget(v, 1)
            return row

        char_lay.addLayout(info_row("라이벌", rival_name, "#F59E0B"))

        pre_quotes = pd.get("pre_match", [])
        if pre_quotes:
            char_lay.addLayout(info_row("경기 전", f'"{pre_quotes[0]}"', "#212529"))

        win_quotes = pd.get("win", [])
        if win_quotes:
            char_lay.addLayout(info_row("승리 시", f'"{win_quotes[0]}"', "#51CF66"))

        loss_quotes = pd.get("loss", [])
        if loss_quotes:
            char_lay.addLayout(info_row("패배 시", f'"{loss_quotes[0]}"', "#FF6B6B"))

        if pd.get("rival_quote"):
            char_lay.addLayout(info_row("라이벌 대사", f'"{pd["rival_quote"]}"', "#F59E0B"))

        root.addWidget(char_frame)

        # ── 닫기 버튼 ──
        close_btn = QPushButton("닫기")
        close_btn.setMinimumHeight(38)
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn)
