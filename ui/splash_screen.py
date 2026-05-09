"""스플래시 스크린 — EXE 첫 로딩 시 표시"""
from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtGui import QPixmap, QColor, QPainter, QFont, QLinearGradient, QBrush
from PyQt6.QtCore import Qt

def show_splash(app: QApplication, duration_ms: int = 2400, version: str = "v1.0.0") -> QSplashScreen:
    """스플래시 화면을 생성·표시하고 QSplashScreen 객체 반환.
    호출 측에서 메인 윈도우 show() 후 splash.finish(win)을 호출해야 함.
    version: main.py 의 APP_VERSION 을 전달받아 표시 (중복 정의 방지).
    """
    W, H = 680, 400
    pm = QPixmap(W, H)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # ── 배경 그라데이션 (다크 인디고) ──
    grad = QLinearGradient(0, 0, 0, H)
    grad.setColorAt(0.0, QColor("#0F0E1A"))
    grad.setColorAt(1.0, QColor("#1E1B3A"))
    p.fillRect(0, 0, W, H, QBrush(grad))

    # ── 상단 강조 라인 ──
    p.setPen(Qt.PenStyle.NoPen)
    accent = QLinearGradient(0, 0, W, 0)
    accent.setColorAt(0.0, QColor(0, 0, 0, 0))
    accent.setColorAt(0.4, QColor("#5B6CF6"))
    accent.setColorAt(0.6, QColor("#7B8CF8"))
    accent.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.setBrush(QBrush(accent))
    p.drawRect(0, 0, W, 3)

    # ── 영문 서브타이틀 ──
    f_sub = QFont("맑은 고딕", 11, QFont.Weight.Bold)
    p.setFont(f_sub)
    p.setPen(QColor("#5B6CF6"))
    p.drawText(0, 90, W, 36, Qt.AlignmentFlag.AlignCenter, "LEGEND  LEAGUE")

    # ── 메인 타이틀 ──
    f_title = QFont("맑은 고딕", 42, QFont.Weight.Bold)
    p.setFont(f_title)
    p.setPen(QColor("#FFFFFF"))
    p.drawText(0, 130, W, 80, Qt.AlignmentFlag.AlignCenter, "레전드 리그")

    # ── 시즌 텍스트 ──
    f_season = QFont("맑은 고딕", 13)
    p.setFont(f_season)
    p.setPen(QColor("#ADB5BD"))
    p.drawText(0, 232, W, 36, Qt.AlignmentFlag.AlignCenter, "2026 SEASON")

    # ── 구분선 ──
    sep_grad = QLinearGradient(100, 0, W - 100, 0)
    sep_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
    sep_grad.setColorAt(0.3, QColor("#5B6CF6"))
    sep_grad.setColorAt(0.7, QColor("#5B6CF6"))
    sep_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.setBrush(QBrush(sep_grad))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(100, 280, W - 200, 1)

    # ── 로딩 텍스트 ──
    f_loading = QFont("맑은 고딕", 10)
    p.setFont(f_loading)
    p.setPen(QColor("#5B6CF6"))
    p.drawText(0, 300, W, 36, Qt.AlignmentFlag.AlignCenter, "불러오는 중...")

    # ── 버전 ──
    f_ver = QFont("맑은 고딕", 9)
    p.setFont(f_ver)
    p.setPen(QColor("#495057"))
    p.drawText(0, H - 28, W - 16, 24,
               Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
               version)

    # ── 하단 강조 라인 ──
    p.setBrush(QBrush(accent))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(0, H - 3, W, 3)

    p.end()

    splash = QSplashScreen(pm, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()
    return splash
