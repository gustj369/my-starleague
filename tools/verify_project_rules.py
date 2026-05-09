"""프로젝트 핵심 규칙을 빠르게 확인하는 읽기 중심 점검 스크립트."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.grade import calc_grade
from ui.styles import RACE_DISPLAY, RACE_SYMBOL
from database.slot_manager import get_slot_db_path


def check(name: str, ok: bool, detail: str = ""):
    mark = "OK" if ok else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{mark}] {name}{suffix}")
    return ok


def main() -> int:
    ok = True
    print("Legend League project rule check")
    print("Checking grade, race display, save path, and build contract...")
    print()

    ok &= check("95+ 등급은 Super", calc_grade(95) == "Super", calc_grade(95))
    ok &= check("90+ 등급은 SS", calc_grade(90) == "SS", calc_grade(90))

    expected_races = {
        "테란": "질풍파",
        "저그": "홍염파",
        "프로토스": "철벽파",
    }
    ok &= check("RACE_DISPLAY 매핑", RACE_DISPLAY == expected_races, repr(RACE_DISPLAY))

    expected_tabs = ["전체"] + [RACE_DISPLAY[race] for race in expected_races]
    ranking_text = (ROOT / "ui" / "ranking_screen.py").read_text(encoding="utf-8")
    ok &= check(
        "랭킹 탭 표시명은 RACE_DISPLAY 기반",
        'RACES_DISPLAY = ["전체"] + [RACE_DISPLAY[race] for race in RACES_DB[1:]]'
        in ranking_text,
        repr(expected_tabs),
    )
    old_labels = ("기동대", "공세대", "수호대")
    ui_files = [p for p in (ROOT / "ui").glob("*.py") if p.name != "styles.py"]
    stale = [
        f"{p.name}:{label}"
        for p in ui_files
        for label in old_labels
        if label in p.read_text(encoding="utf-8")
    ]
    ok &= check("UI에 예전 종족 표시명 없음", not stale, ", ".join(stale))

    ok &= check(
        "종족 심볼 매핑",
        RACE_SYMBOL == {"테란": "⚡", "저그": "🔥", "프로토스": "🛡"},
        repr(RACE_SYMBOL),
    )

    slot_path = get_slot_db_path(0)
    ok &= check("개발 슬롯 DB 경로", slot_path.name == "save_0.db", str(slot_path))

    spec_path = ROOT / "my_starleague.spec"
    ok &= check("PyInstaller spec 존재", spec_path.exists(), str(spec_path))
    if spec_path.exists():
        spec_text = spec_path.read_text(encoding="utf-8")
        ok &= check("EXE 이름은 LegendLeague", "name='LegendLeague'" in spec_text)

    print()
    if ok:
        print("All project rule checks passed.")
    else:
        print("Project rule check failed. Review the FAIL items above.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
