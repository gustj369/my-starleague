"""게임 폰트 로더 — Press Start 2P (헤더), Orbitron (수치), Malgun Gothic (한글 본문)"""
import os
import sys
from pathlib import Path
from PyQt6.QtGui import QFontDatabase

# EXE 환경: sys._MEIPASS (번들 임시 폴더) / fonts
# 개발 환경: 소스 루트 / fonts
if getattr(sys, 'frozen', False):
    _FONTS_DIR = Path(sys._MEIPASS) / "fonts"
else:
    _FONTS_DIR = Path(__file__).parent.parent / "fonts"

_FONT_FILES = {
    "press_start": "PressStart2P.ttf",
    "orbitron":    "Orbitron-Regular.ttf",
}

# 실제 로드된 폰트 패밀리명
FONT_HEADER = "Malgun Gothic"   # 기본값 (다운로드 실패 시 fallback)
FONT_NUMBER = "Malgun Gothic"
FONT_BODY   = "Malgun Gothic"


def load_fonts() -> dict[str, str]:
    """폰트 파일을 QFontDatabase에 등록하고 패밀리명 반환"""
    global FONT_HEADER, FONT_NUMBER

    for key, fname in _FONT_FILES.items():
        path = str(_FONTS_DIR / fname)
        if not os.path.exists(path):
            continue
        fid = QFontDatabase.addApplicationFont(path)
        if fid < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(fid)
        if not families:
            continue
        family = families[0]
        if key == "press_start":
            FONT_HEADER = family
        elif key == "orbitron":
            FONT_NUMBER = family

    return {
        "header": FONT_HEADER,
        "number": FONT_NUMBER,
        "body":   FONT_BODY,
    }
