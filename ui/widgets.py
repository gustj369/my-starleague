"""공통 재사용 위젯 모음"""
import math
from pathlib import Path
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPolygonF, QFont, QPixmap

from core.grade import GRADE_COLORS
from ui.styles import GRADE_STYLE, RACE_COLORS

# 이미지 디렉토리 (my_starleague/../image/)
_IMAGE_DIR = Path(__file__).parent.parent.parent / "image"


def get_player_image_path(name: str) -> str:
    """선수 이름으로 이미지 경로 반환. 없으면 빈 문자열."""
    path = _IMAGE_DIR / f"{name}.png"
    return str(path) if path.exists() else ""


def make_player_avatar(name: str, size: int = 90) -> QLabel:
    """선수 이미지 레이블 생성. 이미지 없으면 이름 이니셜 표시."""
    lbl = QLabel()
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    img_path = get_player_image_path(name)
    if img_path:
        px = QPixmap(img_path).scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        lbl.setPixmap(px)
        lbl.setStyleSheet(
            f"border-radius: {size//2}px; background: #0d1525; border: 1px solid #1e3a5f;"
        )
    else:
        initial = name[0] if name else "?"
        lbl.setText(initial)
        lbl.setStyleSheet(
            f"background: #1e3a5f; color: #ffd700; font-size: {size//3}px; "
            f"font-weight: bold; border-radius: {size//2}px; border: 1px solid #1e3a5f;"
        )
    return lbl

STAT_LABELS = ["컨트롤", "공격력", "수비력", "물량", "전략", "센스"]
STAT_KEYS   = ["control", "attack", "defense", "supply", "strategy", "sense"]


class RadarChart(QWidget):
    """6각형 레이더 차트"""

    def __init__(self, values: list[int], color: str = "#4fc3f7", parent=None):
        super().__init__(parent)
        self._values = values       # 6개 정수, 0~100
        self._color  = QColor(color)
        self.setMinimumSize(160, 160)

    def set_values(self, values: list[int]):
        self._values = values
        self.update()

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 20
        n = 6
        angles = [math.pi / 2 + 2 * math.pi * i / n for i in range(n)]

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(0, 0, w, h, QColor("#0d1525"))

        # 격자 (5단계)
        for level in range(1, 6):
            frac = level / 5
            pts = [QPointF(cx + r * frac * math.cos(a),
                           cy - r * frac * math.sin(a))
                   for a in angles]
            poly = QPolygonF(pts)
            pen = QPen(QColor("#1e3a5f"), 1)
            p.setPen(pen)
            p.drawPolygon(poly)

        # 축선
        for a in angles:
            p.setPen(QPen(QColor("#1e3a5f"), 1))
            p.drawLine(QPointF(cx, cy),
                       QPointF(cx + r * math.cos(a), cy - r * math.sin(a)))

        # 데이터 다각형
        pts = [
            QPointF(cx + r * (self._values[i] / 100) * math.cos(angles[i]),
                    cy - r * (self._values[i] / 100) * math.sin(angles[i]))
            for i in range(n)
        ]
        poly = QPolygonF(pts)
        fill = QColor(self._color)
        fill.setAlpha(60)
        p.setBrush(QBrush(fill))
        p.setPen(QPen(self._color, 2))
        p.drawPolygon(poly)

        # 꼭짓점 점
        p.setBrush(QBrush(self._color))
        for pt in pts:
            p.drawEllipse(pt, 3, 3)

        # 라벨
        p.setPen(QPen(QColor("#c8d8e8")))
        font = QFont("맑은 고딕", 8)
        p.setFont(font)
        label_r = r + 16
        for i, label in enumerate(STAT_LABELS):
            a = angles[i]
            lx = cx + label_r * math.cos(a) - 16
            ly = cy - label_r * math.sin(a) - 8
            p.drawText(QRectF(lx, ly, 36, 16),
                       Qt.AlignmentFlag.AlignCenter, label)

        p.end()


class PlayerCard(QFrame):
    """선수 정보 카드 위젯"""

    def __init__(self, player: dict, selected: bool = False, parent=None):
        super().__init__(parent)
        self._player = player
        self._selected = selected
        self._build()
        self._refresh_style()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # ── 이미지 ──
        self.lbl_avatar = make_player_avatar(self._player["name"], size=72)
        self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_row = QHBoxLayout()
        avatar_row.addStretch()
        avatar_row.addWidget(self.lbl_avatar)
        avatar_row.addStretch()

        # 이름 + 종족
        top = QHBoxLayout()
        self.lbl_name = QLabel(self._player["name"])
        self.lbl_name.setStyleSheet("font-size: 14px; font-weight: bold; background: transparent;")

        race = self._player["race"]
        self.lbl_race = QLabel(race)
        color = RACE_COLORS.get(race, "#ffffff")
        self.lbl_race.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: bold; background: transparent;"
        )
        self.lbl_race.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        top.addWidget(self.lbl_name)
        top.addWidget(self.lbl_race)

        # 등급
        grade = self._player["grade"]
        self.lbl_grade = QLabel(f"◆ {grade}")
        self.lbl_grade.setStyleSheet(GRADE_STYLE.get(grade, "") + " background: transparent; font-size: 18px;")
        self.lbl_grade.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # overall
        self.lbl_overall = QLabel(f"Overall {self._player['overall']:.1f}")
        self.lbl_overall.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_overall.setStyleSheet("color: #7a9ab8; font-size: 11px; background: transparent;")

        # 레이더 차트
        vals = [self._player[k] for k in STAT_KEYS]
        color = RACE_COLORS.get(self._player["race"], "#4fc3f7")
        self.radar = RadarChart(vals, color)

        layout.addLayout(avatar_row)
        layout.addLayout(top)
        layout.addWidget(self.lbl_grade)
        layout.addWidget(self.lbl_overall)
        layout.addWidget(self.radar)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._refresh_style()

    def _refresh_style(self):
        if self._selected:
            self.setProperty("class", "card-selected")
            self.setStyleSheet("""
                QFrame {
                    background-color: #0f2040;
                    border: 2px solid #ffd700;
                    border-radius: 6px;
                }
            """)
        else:
            self.setProperty("class", "card")
            self.setStyleSheet("""
                QFrame {
                    background-color: #0d1525;
                    border: 1px solid #1e3a5f;
                    border-radius: 6px;
                }
                QFrame:hover {
                    border-color: #4fc3f7;
                }
            """)

    def refresh(self, player: dict):
        self._player = player
        self.lbl_name.setText(player["name"])
        grade = player["grade"]
        self.lbl_grade.setText(f"◆ {grade}")
        self.lbl_grade.setStyleSheet(GRADE_STYLE.get(grade, "") + " background: transparent; font-size: 18px;")
        self.lbl_overall.setText(f"Overall {player['overall']:.1f}")
        self.radar.set_values([player[k] for k in STAT_KEYS])


class StatBar(QWidget):
    """단일 능력치 레이블 + 바 표시"""

    def __init__(self, label: str, value: int, color: str = "#4fc3f7", parent=None):
        super().__init__(parent)
        self._value = value
        self._color = QColor(color)
        self._label_text = label

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(50)
        lbl.setStyleSheet("color: #7a9ab8; font-size: 11px; background: transparent;")

        self._bar = _Bar(value, color)
        self._bar.setMinimumHeight(10)

        self._val_lbl = QLabel(str(value))
        self._val_lbl.setFixedWidth(30)
        self._val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._val_lbl.setStyleSheet("color: #c8d8e8; font-size: 11px; background: transparent;")

        row.addWidget(lbl)
        row.addWidget(self._bar, 1)
        row.addWidget(self._val_lbl)

    def set_value(self, value: int, delta: int = 0):
        self._value = value
        self._bar.set_value(value)
        text = str(value)
        if delta > 0:
            self._val_lbl.setStyleSheet("color: #81C784; font-size: 11px; font-weight: bold; background: transparent;")
            text += f" (+{delta})"
        elif delta < 0:
            self._val_lbl.setStyleSheet("color: #EF9A9A; font-size: 11px; font-weight: bold; background: transparent;")
            text += f" ({delta})"
        else:
            self._val_lbl.setStyleSheet("color: #c8d8e8; font-size: 11px; background: transparent;")
        self._val_lbl.setText(text)


class _Bar(QWidget):
    def __init__(self, value: int, color: str, parent=None):
        super().__init__(parent)
        self._value = value
        self._color = QColor(color)
        self.setFixedHeight(10)

    def set_value(self, value: int):
        self._value = value
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # 배경
        p.setBrush(QBrush(QColor("#1e3a5f")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, 4, 4)
        # 채우기
        fill_w = int(w * self._value / 100)
        if fill_w > 0:
            p.setBrush(QBrush(self._color))
            p.drawRoundedRect(0, 0, fill_w, h, 4, 4)
        p.end()


def make_separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("color: #1e3a5f;")
    return sep
