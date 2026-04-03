"""대결 시뮬레이션 — PRD v4 다전제 + 밸런스 시스템"""
import random
from dataclasses import dataclass, field
from typing import Dict, List

from database.db import get_connection, add_gold
from core.grade import calc_overall, calc_grade
from core.balance import (
    STAT_KEYS, calc_effective, calc_power,
    get_rival_info, calc_upset_level, calc_upset_rewards,
    roll_condition,
)

RACE_BONUS_COL = {
    "테란":    "terran_bonus",
    "저그":    "zerg_bonus",
    "프로토스": "protoss_bonus",
}

# 라운드별 다전제 (선승 수)
SETS_TO_WIN = {
    "16강": 2,
    "8강":  2,
    "4강":  2,
    "결승": 3,
}


# ── 데이터 클래스 ──────────────────────────────────────────────
@dataclass
class SetResult:
    set_number: int
    winner_id: int
    loser_id: int
    a_power: float
    b_power: float


@dataclass
class MatchOutcome:
    winner_id: int
    loser_id: int
    player_a_delta: Dict[str, int] = field(default_factory=dict)
    player_b_delta: Dict[str, int] = field(default_factory=dict)
    a_power: float = 0.0       # 세트 평균 전투력
    b_power: float = 0.0
    match_id: int = 0
    is_upset: bool = False
    upset_gold: int = 0
    a_condition: str = "보통"
    b_condition: str = "보통"
    a_fatigue: int = 0
    b_fatigue: int = 0
    is_rival_match: bool = False
    a_wins: int = 0
    b_wins: int = 0
    sets: List[SetResult] = field(default_factory=list)


# ── DB 헬퍼 ──────────────────────────────────────────────────
def _get_player(cur, player_id: int) -> dict:
    row = cur.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
    if row is None:
        raise ValueError(f"선수 id={player_id} 없음")
    return dict(row)


def _get_map(cur, map_id: int) -> dict:
    row = cur.execute("SELECT * FROM maps WHERE id=?", (map_id,)).fetchone()
    if row is None:
        raise ValueError(f"맵 id={map_id} 없음")
    return dict(row)


def _get_item_bonuses(cur, player_id: int) -> Dict[str, int]:
    rows = cur.execute(
        """SELECT i.control_bonus, i.attack_bonus, i.defense_bonus,
                  i.supply_bonus, i.strategy_bonus, i.sense_bonus
           FROM player_items pi
           JOIN items i ON i.id = pi.item_id
           WHERE pi.player_id = ?""",
        (player_id,)
    ).fetchall()
    bonuses = {k: 0 for k in STAT_KEYS}
    for row in rows:
        bonuses["control"]  += row["control_bonus"]
        bonuses["attack"]   += row["attack_bonus"]
        bonuses["defense"]  += row["defense_bonus"]
        bonuses["supply"]   += row["supply_bonus"]
        bonuses["strategy"] += row["strategy_bonus"]
        bonuses["sense"]    += row["sense_bonus"]
    return bonuses


# ── 스탯 변동 ─────────────────────────────────────────────────
def _apply_winner_delta(upset_bonus: Dict[str, int] | None = None) -> Dict[str, int]:
    num_boost = random.randint(1, 2)
    keys = random.sample(STAT_KEYS, num_boost)
    delta = {k: 0 for k in STAT_KEYS}
    for k in keys:
        delta[k] = random.randint(1, 3)
    if upset_bonus:
        for k in STAT_KEYS:
            delta[k] = delta.get(k, 0) + upset_bonus.get(k, 0)
    return delta


def _apply_loser_delta(player: dict, power_diff: float) -> Dict[str, int]:
    delta = {k: 0 for k in STAT_KEYS}
    drop_key = random.choice(STAT_KEYS)
    drop_val = random.randint(1, 2)
    current = player[drop_key]
    delta[drop_key] = -min(drop_val, current - 1)
    if power_diff >= 10:
        delta["sense"] += 1  # 역경에서 배움
    return delta


def _update_player_stats(cur, player: dict, delta: Dict[str, int]):
    new_stats = {k: max(1, player[k] + delta[k]) for k in STAT_KEYS}
    overall = calc_overall(**new_stats)
    grade = calc_grade(overall)
    cur.execute(
        """UPDATE players
           SET control=?, attack=?, defense=?, supply=?, strategy=?, sense=?,
               overall=?, grade=?
           WHERE id=?""",
        (new_stats["control"], new_stats["attack"], new_stats["defense"],
         new_stats["supply"],  new_stats["strategy"], new_stats["sense"],
         overall, grade, player["id"])
    )


def _save_match_result(cur, map_id, a_id, b_id, winner_id,
                       a_delta, b_delta, is_upset) -> int:
    cur.execute(
        """INSERT INTO match_results
           (map_id, player_a_id, player_b_id, winner_id,
            a_control_delta, a_attack_delta, a_defense_delta,
            a_supply_delta,  a_strategy_delta, a_sense_delta,
            b_control_delta, b_attack_delta, b_defense_delta,
            b_supply_delta,  b_strategy_delta, b_sense_delta,
            is_upset)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (map_id, a_id, b_id, winner_id,
         a_delta["control"],  a_delta["attack"],  a_delta["defense"],
         a_delta["supply"],   a_delta["strategy"], a_delta["sense"],
         b_delta["control"],  b_delta["attack"],  b_delta["defense"],
         b_delta["supply"],   b_delta["strategy"], b_delta["sense"],
         1 if is_upset else 0)
    )
    return cur.lastrowid


# ── 단일 세트 시뮬레이션 (DB 저장 없음) ───────────────────────
def simulate_set(
    player_a_id: int,
    player_b_id: int,
    map_id: int,
    a_condition: str = "보통",
    b_condition: str = "보통",
    a_fatigue_override: int | None = None,
    b_fatigue_override: int | None = None,
    set_number: int = 1,
) -> SetResult:
    """단일 세트 결과 반환. DB에 쓰지 않는다."""
    conn = get_connection()
    cur = conn.cursor()

    pa = _get_player(cur, player_a_id)
    pb = _get_player(cur, player_b_id)
    mp = _get_map(cur, map_id)
    ia = _get_item_bonuses(cur, player_a_id)
    ib = _get_item_bonuses(cur, player_b_id)
    conn.close()

    map_bonus_a = mp[RACE_BONUS_COL[pa["race"]]]
    map_bonus_b = mp[RACE_BONUS_COL[pb["race"]]]

    rival_info = get_rival_info(player_a_id, player_b_id)
    rival_stat = rival_info["stat_bonus"] if rival_info else 0
    extra_luck  = rival_info["extra_luck"]  if rival_info else 0

    eff_a = calc_effective(pa, ia, map_bonus_a, a_condition, rival_stat,
                           fatigue_val=a_fatigue_override)
    eff_b = calc_effective(pb, ib, map_bonus_b, b_condition, rival_stat,
                           fatigue_val=b_fatigue_override)

    power_a = calc_power(eff_a, pa["grade"], extra_luck)
    power_b = calc_power(eff_b, pb["grade"], extra_luck)

    winner_id = player_a_id if power_a >= power_b else player_b_id
    loser_id  = player_b_id if winner_id == player_a_id else player_a_id

    return SetResult(
        set_number=set_number,
        winner_id=winner_id,
        loser_id=loser_id,
        a_power=round(power_a, 2),
        b_power=round(power_b, 2),
    )


# ── 다전제 직접 완료 (내 경기용) ─────────────────────────────
def finalize_match(
    player_a_id: int,
    player_b_id: int,
    sets: List[SetResult],
    map_id: int,
    a_condition: str = "보통",
    b_condition: str = "보통",
    award_gold: bool = True,
) -> MatchOutcome:
    """시뮬레이션 화면에서 세트가 끝난 뒤 호출.
    stats 업데이트 + match_results 저장 + 골드 지급.
    """
    a_wins = sum(1 for s in sets if s.winner_id == player_a_id)
    b_wins = sum(1 for s in sets if s.winner_id == player_b_id)
    winner_id = player_a_id if a_wins > b_wins else player_b_id
    loser_id  = player_b_id if winner_id == player_a_id else player_a_id

    conn = get_connection()
    cur = conn.cursor()
    pa = _get_player(cur, player_a_id)
    pb = _get_player(cur, player_b_id)

    power_diff = abs(
        sum(s.a_power for s in sets) / len(sets) -
        sum(s.b_power for s in sets) / len(sets)
    )

    winner = pa if winner_id == player_a_id else pb
    loser  = pb if winner_id == player_a_id else pa

    upset_level = calc_upset_level(winner["grade"], loser["grade"])
    is_upset = upset_level > 0
    upset_gold, upset_stat_bonus = calc_upset_rewards(upset_level) if is_upset else (0, {})

    if winner_id == player_a_id:
        a_delta = _apply_winner_delta(upset_stat_bonus if is_upset else None)
        b_delta = _apply_loser_delta(pb, power_diff)
    else:
        b_delta = _apply_winner_delta(upset_stat_bonus if is_upset else None)
        a_delta = _apply_loser_delta(pa, power_diff)

    _update_player_stats(cur, pa, a_delta)
    _update_player_stats(cur, pb, b_delta)

    rival_info = get_rival_info(player_a_id, player_b_id)
    is_rival_match = rival_info is not None

    match_id = _save_match_result(cur, map_id, player_a_id, player_b_id,
                                  winner_id, a_delta, b_delta, is_upset)
    conn.commit()
    conn.close()

    if award_gold:
        total = 80 + upset_gold
        add_gold(total)

    avg_a = sum(s.a_power for s in sets) / len(sets)
    avg_b = sum(s.b_power for s in sets) / len(sets)

    return MatchOutcome(
        winner_id=winner_id,
        loser_id=loser_id,
        player_a_delta=a_delta,
        player_b_delta=b_delta,
        a_power=round(avg_a, 2),
        b_power=round(avg_b, 2),
        match_id=match_id,
        is_upset=is_upset,
        upset_gold=upset_gold,
        a_condition=a_condition,
        b_condition=b_condition,
        a_fatigue=pa.get("fatigue", 0),
        b_fatigue=pb.get("fatigue", 0),
        is_rival_match=is_rival_match,
        a_wins=a_wins,
        b_wins=b_wins,
        sets=sets,
    )


# ── AI용 다전제 시뮬레이션 ────────────────────────────────────
def simulate_series(
    player_a_id: int,
    player_b_id: int,
    map_id: int,
    round_name: str = "16강",
    a_condition: str = "보통",
    b_condition: str = "보통",
    award_gold: bool = False,
) -> MatchOutcome:
    """AI 경기: 다전제 완전 자동 시뮬레이션 + DB 저장."""
    sets_to_win = SETS_TO_WIN.get(round_name, 2)
    sets: List[SetResult] = []
    a_wins = 0
    b_wins = 0
    set_num = 1

    while a_wins < sets_to_win and b_wins < sets_to_win:
        s = simulate_set(player_a_id, player_b_id, map_id,
                         a_condition, b_condition, set_number=set_num)
        sets.append(s)
        if s.winner_id == player_a_id:
            a_wins += 1
        else:
            b_wins += 1
        set_num += 1

    return finalize_match(
        player_a_id, player_b_id,
        sets, map_id,
        a_condition, b_condition,
        award_gold=award_gold,
    )


# ── 하위 호환 래퍼 (기존 코드가 simulate() 를 직접 호출하는 경우) ──
def simulate(
    player_a_id: int,
    player_b_id: int,
    map_id: int,
    award_gold: bool = True,
    a_condition: str = "보통",
    b_condition: str = "보통",
) -> MatchOutcome:
    """단일 세트 대결 (기존 호환용). 내부적으로 1세트만 실행."""
    s = simulate_set(player_a_id, player_b_id, map_id,
                     a_condition, b_condition, set_number=1)
    return finalize_match(
        player_a_id, player_b_id,
        [s], map_id,
        a_condition, b_condition,
        award_gold=award_gold,
    )
