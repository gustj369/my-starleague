"""5슬롯 세이브 파일 관리"""
import sqlite3
import sys
import os
from pathlib import Path

# db.py 와 동일한 경로 로직 — EXE / 개발 환경 분기
if getattr(sys, 'frozen', False):
    SAVES_DIR = Path(os.getenv('APPDATA', Path.home())) / '마이스타리그' / 'saves'
else:
    SAVES_DIR = Path(__file__).parent.parent.parent / "saves"

SLOT_COUNT = 5


def get_slot_db_path(slot_idx: int) -> Path:
    SAVES_DIR.mkdir(parents=True, exist_ok=True)   # parents=True: 부모 폴더 자동 생성
    return SAVES_DIR / f"save_{slot_idx}.db"


def slot_exists(slot_idx: int) -> bool:
    return get_slot_db_path(slot_idx).exists()


def get_slot_info(slot_idx: int) -> dict:
    """슬롯 메타데이터 반환. 데이터 없으면 {'empty': True} 반환."""
    path = get_slot_db_path(slot_idx)
    if not path.exists():
        return {"empty": True, "slot": slot_idx}

    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT key, value FROM game_state").fetchall()
        data = {r["key"]: r["value"] for r in rows}
        conn.close()
    except Exception:
        return {"empty": True, "slot": slot_idx}

    if "db_version" not in data:
        return {"empty": True, "slot": slot_idx}

    gold = int(data.get("gold", 500))
    total = int(data.get("total_tournaments_played", 0))
    last_achievement = data.get("last_achievement", "")
    has_active = "current_tournament_id" in data

    if has_active:
        # 진행 중인 토너먼트의 라운드 확인
        try:
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row
            tid = int(data["current_tournament_id"])
            t = conn.execute(
                "SELECT current_round FROM tournaments WHERE id=?", (tid,)
            ).fetchone()
            conn.close()
            cur_round = t["current_round"] if t else "?"
            status_text = f"진행 중  ({cur_round})"
        except Exception:
            status_text = "진행 중"
    elif total > 0:
        status_text = f"{total}회 완료"
        if last_achievement:
            status_text += f"  —  {last_achievement}"
    else:
        status_text = "시작 전"

    return {
        "empty": False,
        "slot": slot_idx,
        "gold": gold,
        "total_tournaments": total,
        "last_achievement": last_achievement,
        "has_active_tournament": has_active,
        "status_text": status_text,
    }


def delete_slot(slot_idx: int):
    """슬롯 DB 파일 삭제 (초기화)"""
    path = get_slot_db_path(slot_idx)
    if path.exists():
        path.unlink()
