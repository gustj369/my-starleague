"""온보딩 다이얼로그 — 첫 플레이 시 게임 규칙 안내"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt


def _section(title: str, body: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 12)
    lay.setSpacing(4)
    t = QLabel(title)
    t.setStyleSheet(
        "color: #5B6CF6; font-size: 13px; font-weight: bold; background: transparent;"
    )
    b = QLabel(body)
    b.setWordWrap(True)
    b.setStyleSheet("color: #212529; font-size: 12px; background: transparent; line-height: 160%;")
    b.setTextFormat(Qt.TextFormat.RichText)
    lay.addWidget(t)
    lay.addWidget(b)
    return w


def _tab(sections: list[tuple[str, str]]) -> QWidget:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; background: #FFFFFF; }")
    inner = QWidget()
    inner.setStyleSheet("background: #FFFFFF;")
    lay = QVBoxLayout(inner)
    lay.setContentsMargins(16, 16, 16, 16)
    lay.setSpacing(8)
    for title, body in sections:
        lay.addWidget(_section(title, body))
    lay.addStretch()
    scroll.setWidget(inner)
    return scroll


class OnboardingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("레전드 리그 — 게임 가이드")
        self.setMinimumSize(560, 480)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 16)
        root.setSpacing(0)

        # 타이틀 배너
        banner = QLabel("★  레전드 리그 게임 가이드")
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner.setStyleSheet(
            "background: #5B6CF6; color: #FFFFFF; font-size: 15px; "
            "font-weight: bold; padding: 14px;"
        )
        root.addWidget(banner)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabBar::tab { padding: 6px 16px; font-size: 12px; }
            QTabBar::tab:selected { color: #5B6CF6; font-weight: bold; }
        """)

        # ── 탭 1: 기본 규칙 ──────────────────────────────────
        tab1 = _tab([
            ("🎮 게임 목표",
             "16강 토너먼트에서 선수를 이끌어 <b>우승</b>하는 것이 목표입니다.<br>"
             "경기마다 선수는 성장하고 골드를 획득합니다. 골드로 아이템을 구매해 선수를 강화하세요."),
            ("⚔ 대결 구조",
             "한 경기는 <b>3세트 선승제</b>(결승 5세트 선승제)로 진행됩니다.<br>"
             "각 세트는 <b>초반 → 중반 → 후반</b> 3페이즈로 나뉘며, 2페이즈 이상 승리한 선수가 세트를 가져갑니다.<br>"
             "초반 승리 선수는 중반에 <b>+2 모멘텀</b> 보너스를 받습니다."),
            ("📊 등급 체계",
             "<b>Super > SS > S > A > B > C > D > E > F</b><br>"
             "Overall(종합 점수)에 따라 등급이 자동으로 결정됩니다. 경기 승리 시 능력치가 올라 등급이 상승할 수 있습니다.<br>"
             "Super·SS 등급 선수는 <b>최악의 맵</b>이 강제 지정되는 핸디캡이 적용됩니다."),
            ("💰 골드 획득",
             "• 경기 완료: +80G<br>"
             "• 라운드 통과: 16강 +100G / 8강 +150G / 4강 +200G / 우승 +500G<br>"
             "• 이변(낮은 등급이 높은 등급을 이김): 추가 최대 +300G"),
        ])
        tabs.addTab(tab1, "기본 규칙")

        # ── 탭 2: 전술 & 전략 ────────────────────────────────
        tab2 = _tab([
            ("✊ 전술 삼각 시스템 (페이즈 1)",
             "초반 페이즈에서 전술을 선택합니다.<br>"
             "• <b>공세</b> → 수비를 꺾음<br>"
             "• <b>수비</b> → 기동을 꺾음<br>"
             "• <b>기동</b> → 공세를 꺾음<br>"
             "전술 우위가 되면 초반 페이즈에 <b>보너스</b>가 적용됩니다."),
            ("📋 전략 시스템 (전 페이즈)",
             "• <b>초반집중</b>: 초반 +9, 후반 -5  →  빠른 승리를 노릴 때<br>"
             "• <b>균형</b>: 보정 없음  →  안정적인 운영<br>"
             "• <b>후반체력전</b>: 초반 -5 / 중반 +3 / 후반 +14  →  역전을 노릴 때<br>"
             "<br>전략 카운터: <b>후반체력전 > 초반집중 > 균형 > 후반체력전</b>"),
            ("🔄 다전제 모멘텀",
             "세트 스코어에서 뒤지고 있는 선수는 <b>역전 부스트</b>를 받습니다.<br>"
             "0-1로 뒤질 때 comeback 보너스 +3, 0-2일 때 최대 +6이 부여됩니다."),
        ])
        tabs.addTab(tab2, "전술 & 전략")

        # ── 탭 3: 선수 & 아이템 ──────────────────────────────
        tab3 = _tab([
            ("🏃 컨디션 & 피로도",
             "경기 전 컨디션이 롤됩니다.<br>"
             "• <b>최상</b> (+10%) / <b>보통</b> (±0%) / <b>저조</b> (-10%)<br>"
             "경기 후 피로도가 쌓입니다.<br>"
             "• 피로 30 이하: 페널티 없음<br>"
             "• 피로 31~60: 전투력 -5%<br>"
             "• 피로 61~80: 전투력 -12%<br>"
             "• 피로 81~100: 전투력 -20%<br>"
             "새 토너먼트 시작 시 피로도가 초기화됩니다."),
            ("🛒 아이템",
             "상점에서 골드로 아이템을 구매해 선수에게 장착할 수 있습니다.<br>"
             "선수당 최대 <b>3개</b>까지 장착 가능합니다.<br>"
             "• <b>능력치 아이템</b>: 특정 스탯 영구 상승<br>"
             "• <b>컨디션 아이템</b>: 경기 전 컨디션 1단계 상향 (1회용)<br>"
             "• <b>피로회복 아이템</b>: 피로도 1구간 회복 (1회용)"),
            ("🔥 라이벌 시스템",
             "특정 선수들 사이에 라이벌 관계가 설정되어 있습니다.<br>"
             "라이벌전에서는 양쪽의 <b>운 변동성</b>이 크게 확장되어<br>"
             "더 드라마틱한 경기 결과가 나타납니다."),
        ])
        tabs.addTab(tab3, "선수 & 아이템")

        root.addWidget(tabs, 1)

        # 닫기 버튼
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(16, 0, 16, 0)
        btn = QPushButton("✓  게임 시작!")
        btn.setProperty("class", "primary")
        btn.setMinimumHeight(44)
        btn.setMinimumWidth(160)
        btn.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(btn)
        btn_row.addStretch()
        root.addLayout(btn_row)
