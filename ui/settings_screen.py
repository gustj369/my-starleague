"""설정 화면 — 중계 속도, 기타 옵션"""
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from database.db import get_setting, set_setting
from ui.widgets import make_separator

# 중계 속도 옵션: (표시명, 설정값, 딜레이ms)
SPEED_OPTIONS = [
    ("느림",   "slow",    1500),
    ("보통",   "normal",   900),
    ("빠름",   "fast",     400),
    ("즉시",   "instant",    0),
]


def get_commentary_delay() -> int:
    """현재 설정에 따른 중계 딜레이(ms) 반환."""
    val = get_setting("commentary_speed", "normal")
    for _, key, delay in SPEED_OPTIONS:
        if key == val:
            return delay
    return 900


class SettingsScreen(QWidget):
    sig_back = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._speed_btns: list[QPushButton] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(60, 40, 60, 40)
        root.setSpacing(0)

        # ── 헤더 ──
        hdr = QHBoxLayout()
        btn_back = QPushButton("◀  뒤로")
        btn_back.setFixedHeight(34)
        btn_back.setStyleSheet("""
            QPushButton {
                background: transparent; color: #5B6CF6;
                border: 1px solid #C5C8FF; border-radius: 8px;
                padding: 0 14px; font-size: 12px;
            }
            QPushButton:hover { background: #EEF2FF; }
        """)
        btn_back.clicked.connect(self.sig_back)

        title = QLabel("⚙  설정")
        title.setStyleSheet(
            "color: #212529; font-size: 22px; font-weight: bold; background: transparent;"
        )

        hdr.addWidget(btn_back)
        hdr.addSpacing(16)
        hdr.addWidget(title)
        hdr.addStretch()
        root.addLayout(hdr)
        root.addSpacing(24)
        root.addWidget(make_separator())
        root.addSpacing(28)

        # ── 중계 속도 섹션 ──
        sec_lbl = QLabel("중계 속도")
        sec_lbl.setStyleSheet(
            "color: #5B6CF6; font-size: 15px; font-weight: bold; background: transparent;"
        )
        root.addWidget(sec_lbl)
        root.addSpacing(6)

        desc = QLabel(
            "경기 중계 텍스트가 표시되는 속도를 설정합니다.\n"
            "빠르게 설정할수록 경기가 빨리 진행됩니다."
        )
        desc.setStyleSheet("color: #868E96; font-size: 12px; background: transparent;")
        root.addWidget(desc)
        root.addSpacing(14)

        speed_row = QHBoxLayout()
        speed_row.setSpacing(12)
        for label, key, delay in SPEED_OPTIONS:
            btn = QPushButton(f"{label}\n({delay}ms)" if delay > 0 else f"{label}\n(즉시)")
            btn.setProperty("_speed_key", key)
            btn.setMinimumHeight(72)
            btn.setMinimumWidth(120)
            btn.setStyleSheet("""
                QPushButton {
                    background: #FFFFFF; color: #495057;
                    border: 1px solid #DEE2E6; border-radius: 12px;
                    font-size: 13px; font-weight: bold; padding: 8px;
                }
                QPushButton:hover {
                    border-color: #5B6CF6; color: #5B6CF6; background: #EEF2FF;
                }
            """)
            btn.clicked.connect(lambda _, k=key: self._on_speed_picked(k))
            self._speed_btns.append(btn)
            speed_row.addWidget(btn)
        speed_row.addStretch()
        root.addLayout(speed_row)
        root.addSpacing(8)

        self.lbl_speed_cur = QLabel("")
        self.lbl_speed_cur.setStyleSheet(
            "color: #5B6CF6; font-size: 12px; background: transparent;"
        )
        root.addWidget(self.lbl_speed_cur)
        root.addSpacing(32)
        root.addWidget(make_separator())
        root.addSpacing(24)

        check_lbl = QLabel("수동 확인 체크리스트")
        check_lbl.setStyleSheet(
            "color: #5B6CF6; font-size: 15px; font-weight: bold; background: transparent;"
        )
        root.addWidget(check_lbl)
        root.addSpacing(6)

        check_desc = QLabel(
            "코드 변경 후 기본 흐름을 손으로 확인할 때 참고하세요.<br>"
            "문서 위치: RTS2/docs/manual-checklist.md"
        )
        check_desc.setStyleSheet("color: #868E96; font-size: 12px; background: transparent;")
        root.addWidget(check_desc)
        root.addStretch()

        # ── 버전 정보 (우하단) ──
        root.addSpacing(8)
        self.lbl_version = QLabel("")
        self.lbl_version.setStyleSheet(
            "color: #CED4DA; font-size: 11px; background: transparent;"
        )
        root.addWidget(self.lbl_version)

    def _on_speed_picked(self, key: str):
        set_setting("commentary_speed", key)
        self._update_speed_ui(key)

    def _update_speed_ui(self, current_key: str):
        label_map = {k: lbl for lbl, k, _ in SPEED_OPTIONS}
        delay_map = {k: d for _, k, d in SPEED_OPTIONS}

        for btn in self._speed_btns:
            k = btn.property("_speed_key")
            if k == current_key:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #EEF2FF; color: #5B6CF6;
                        border: 2px solid #5B6CF6; border-radius: 12px;
                        font-size: 13px; font-weight: bold; padding: 8px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #FFFFFF; color: #495057;
                        border: 1px solid #DEE2E6; border-radius: 12px;
                        font-size: 13px; font-weight: bold; padding: 8px;
                    }
                    QPushButton:hover {
                        border-color: #5B6CF6; color: #5B6CF6; background: #EEF2FF;
                    }
                """)

        lbl = label_map.get(current_key, "보통")
        delay = delay_map.get(current_key, 900)
        suffix = f"({delay}ms)" if delay > 0 else "(즉시 표시)"
        self.lbl_speed_cur.setText(f"✔ 현재 설정: {lbl}  {suffix}")

    def refresh(self):
        """화면 진입 시 현재 설정 로드."""
        current = get_setting("commentary_speed", "normal")
        self._update_speed_ui(current)
        # 버전 정보 갱신
        app = QApplication.instance()
        app_ver = app.applicationVersion() if app else "v1.0.0"
        db_ver = get_setting("db_version", "?")
        self.lbl_version.setText(f"앱 버전: {app_ver}  |  DB 버전: {db_ver}")
