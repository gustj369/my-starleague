"""토너먼트 종료 후 선수 성장 이벤트"""
import random
from database.db import get_connection
from core.grade import calc_overall, calc_grade


def _growth_max_delta(overall: float, cfg_max: int) -> int:
    """OVR 기반 성장 상한 감쇄.
    Super(95+): 최대 1 / SS(90+): 최대 2 / S(85+): 최대 cfg_max-1 / 그 외: cfg_max
    """
    if overall >= 95:
        return min(1, cfg_max)
    elif overall >= 90:
        return min(2, cfg_max)
    elif overall >= 85:
        return min(max(cfg_max - 1, 1), cfg_max)
    return cfg_max

STAT_KEYS = ["control", "attack", "defense", "supply", "strategy", "sense"]
STAT_LABELS = {
    "control":  "컨트롤",
    "attack":   "공격력",
    "defense":  "수비력",
    "supply":   "물량",
    "strategy": "전략",
    "sense":    "센스",
}

# 업적별 성장 테이블
GROWTH_TABLE = {
    "우승":      {"count": 2, "min_delta": 3, "max_delta": 5},
    "준우승":    {"count": 2, "min_delta": 2, "max_delta": 3},
    "4강 탈락":  {"count": 1, "min_delta": 1, "max_delta": 3},
    "8강 탈락":  {"count": 1, "min_delta": 1, "max_delta": 2},
    "16강 탈락": {"count": 1, "min_delta": 0, "max_delta": 1},  # 50% 확률로 성장 없음
}


def generate_growth_event(player_id: int, achievement: str) -> list[dict]:
    """업적에 따라 선수 성장 이벤트를 생성한다.

    Args:
        player_id:   players 테이블 PK
        achievement: GROWTH_TABLE 키 ("우승", "준우승", "4강 탈락", "8강 탈락", "16강 탈락")

    Returns:
        성장 이벤트 목록. 각 요소는 {"stat", "stat_label", "delta"}.
        성장 없으면 빈 리스트.
    """
    cfg = GROWTH_TABLE.get(achievement)
    if cfg is None:
        return []

    # 16강 탈락은 50% 확률로 성장 없음
    if achievement == "16강 탈락" and random.random() < 0.5:
        return []

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE id=?", (player_id,)
        ).fetchone()
    if row is None:
        return []
    player = dict(row)

    # 현재 낮은 스탯 우선 — 하위 4개 스탯 풀에서 선택
    sorted_stats = sorted(STAT_KEYS, key=lambda k: player[k])
    pool = sorted_stats[:4]

    # OVR 기반 성장 상한 감쇄 적용
    overall     = player.get("overall", 50.0)
    capped_max  = _growth_max_delta(overall, cfg["max_delta"])
    actual_min  = min(cfg["min_delta"], capped_max)

    selected = random.sample(pool, min(cfg["count"], len(pool)))
    events: list[dict] = []
    for stat in selected:
        delta = random.randint(actual_min, capped_max)
        if delta > 0:
            events.append({
                "stat":       stat,
                "stat_label": STAT_LABELS[stat],
                "delta":      delta,
            })
    return events


def apply_growth_event(player_id: int, events: list[dict]) -> None:
    """성장 이벤트를 DB에 반영하고 overall / grade 를 재계산한다.

    Args:
        player_id: players 테이블 PK
        events:    generate_growth_event() 반환값
    """
    if not events:
        return

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE id=?", (player_id,)
        ).fetchone()
        if row is None:
            return
        player = dict(row)

        for ev in events:
            stat = ev["stat"]
            player[stat] = min(100, player[stat] + ev["delta"])

        new_overall = calc_overall(**{k: player[k] for k in STAT_KEYS})
        new_grade   = calc_grade(new_overall)

        conn.execute(
            """UPDATE players
               SET control=?, attack=?, defense=?, supply=?, strategy=?, sense=?,
                   overall=?, grade=?
               WHERE id=?""",
            (
                player["control"], player["attack"], player["defense"],
                player["supply"],  player["strategy"], player["sense"],
                new_overall, new_grade, player_id,
            ),
        )
        conn.commit()
