"""Save slot database file management."""
import sqlite3
import sys
import os
from pathlib import Path


if getattr(sys, "frozen", False):
    SAVES_DIR = Path(os.getenv("APPDATA", Path.home())) / "\ub9c8\uc774\uc2a4\ud0c0\ub9ac\uadf8" / "saves"
else:
    SAVES_DIR = Path(__file__).parent.parent.parent / "saves"

SLOT_COUNT = 5


def _corrupt_slot_info(slot_idx: int) -> dict:
    return {
        "empty": False,
        "corrupt": True,
        "slot": slot_idx,
        "status_text": "\uc190\uc0c1\ub41c \uc2ac\ub86f",
        "last_achievement": "",
        "gold": 0,
    }


def get_slot_db_path(slot_idx: int) -> Path:
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    return SAVES_DIR / f"save_{slot_idx}.db"


def slot_exists(slot_idx: int) -> bool:
    return get_slot_db_path(slot_idx).exists()


def get_slot_info(slot_idx: int) -> dict:
    """Return slot metadata. Empty slots return {'empty': True}."""
    path = get_slot_db_path(slot_idx)
    if not path.exists():
        return {"empty": True, "slot": slot_idx}

    try:
        with sqlite3.connect(str(path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT key, value FROM game_state").fetchall()
        data = {r["key"]: r["value"] for r in rows}
    except Exception:
        return _corrupt_slot_info(slot_idx)

    if "db_version" not in data:
        return _corrupt_slot_info(slot_idx)

    try:
        gold = int(data.get("gold", 500))
        total = int(data.get("total_tournaments_played", 0))
    except (TypeError, ValueError):
        return _corrupt_slot_info(slot_idx)

    last_achievement = data.get("last_achievement", "")
    has_active = "current_tournament_id" in data

    if has_active:
        try:
            tid = int(data["current_tournament_id"])
            with sqlite3.connect(str(path)) as conn:
                conn.row_factory = sqlite3.Row
                t = conn.execute(
                    "SELECT current_round FROM tournaments WHERE id=?", (tid,)
                ).fetchone()
            cur_round = t["current_round"] if t else "?"
            status_text = f"\uc9c4\ud589 \uc911 ({cur_round})"
        except Exception:
            status_text = "\uc9c4\ud589 \uc911"
    elif total > 0:
        status_text = f"{total}\ud68c \uc644\ub8cc"
        if last_achievement:
            status_text += f"  \u00b7 {last_achievement}"
    else:
        status_text = "\uc2dc\uc791 \uc804"

    return {
        "empty": False,
        "corrupt": False,
        "slot": slot_idx,
        "gold": gold,
        "total_tournaments": total,
        "last_achievement": last_achievement,
        "has_active_tournament": has_active,
        "status_text": status_text,
    }


def delete_slot(slot_idx: int):
    """Delete a slot DB file."""
    path = get_slot_db_path(slot_idx)
    if path.exists():
        path.unlink()
