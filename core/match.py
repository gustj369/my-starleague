"""대결 시뮬레이션 — PRD v7 3페이즈 + 빌드 선택 시스템"""
import random
from dataclasses import dataclass, field
from typing import Dict, List

from database.db import get_connection, add_gold
from core.grade import calc_overall, calc_grade
from core.balance import (
    STAT_KEYS, GRADE_ORDER, calc_effective, calc_power,
    get_rival_info, calc_upset_level, calc_upset_rewards,
    calc_grade_gap_boost, roll_condition,
)
from core.builds import calc_build_result, BUILD_ADVANTAGE_BOOST

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

# 세트 전략 페이즈 보정값
# PRD v13 조정:
#   초반집중:   초반에 모든 것을 쏟아붓고 후반에 체력 소진 (초반 +9, 후반 -5)
#              기존 +12/-6에서 완화 → Phase1+모멘텀 연쇄 과다 스택 해소
#   균형:       안정적 운영, 변동 없음
#   후반체력전: 초반 체력 비축 후 중반부터 힘을 발휘 (초반 -5, 중반 +3, 후반 +14)
#              기존 초반 -6→-5로 완화 → 역전 경로를 좀 더 현실적으로
#   → 전략 삼각 구도: 초반집중>균형, 후반체력전>초반집중(역전), 균형>후반체력전(Phase1+2 선점)
STRATEGY_PHASE_BONUS = {
    "초반집중":   {"초반": +9, "중반":  0, "후반":  -5},
    "균형":       {"초반":  0, "중반":  0, "후반":   0},
    "후반체력전": {"초반": -5, "중반": +3, "후반": +14},
}


# ── 데이터 클래스 ──────────────────────────────────────────────
@dataclass
class PhaseResult:
    phase_name: str   # "초반" / "중반" / "후반"
    winner_id: int
    a_power: float
    b_power: float


@dataclass
class SetResult:
    set_number: int
    winner_id: int
    loser_id: int
    a_power: float
    b_power: float
    phases: List[PhaseResult] = field(default_factory=list)
    build_a: str = "바위"
    build_b: str = "바위"
    build_result: int = 0   # +1=a 빌드 승, 0=무승부, -1=b 빌드 승


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


# ── OVR 기반 성장 감쇄 ────────────────────────────────────────
def _growth_factor(overall: float) -> float:
    """고OVR일수록 성장이 둔해지는 감쇄 계수.
    Super(95+): 0.4배 / SS(90+): 0.6배 / S(85+): 0.8배 / 그 외: 1.0배
    """
    if overall >= 95:
        return 0.4
    elif overall >= 90:
        return 0.6
    elif overall >= 85:
        return 0.8
    return 1.0


def _scale_delta(raw: int, factor: float) -> int:
    """소수 감쇄 시 확률적 반올림 (0.7 → 70% 확률로 1, 30% 확률로 0)"""
    val = raw * factor
    base = int(val)
    frac = val - base
    return base + (1 if random.random() < frac else 0)


# ── 스탯 변동 ─────────────────────────────────────────────────
def _apply_winner_delta(player: dict, upset_bonus: Dict[str, int] | None = None) -> Dict[str, int]:
    """승자 스탯 변동. OVR 기반 성장 감쇄 적용."""
    overall = player.get("overall", 50.0)
    factor  = _growth_factor(overall)

    num_boost = random.randint(1, 2)
    keys = random.sample(STAT_KEYS, num_boost)
    delta = {k: 0 for k in STAT_KEYS}
    for k in keys:
        delta[k] = _scale_delta(random.randint(1, 3), factor)
    if upset_bonus:
        for k in STAT_KEYS:
            bonus = _scale_delta(upset_bonus.get(k, 0), factor)
            delta[k] = delta.get(k, 0) + bonus
    return delta


def _apply_loser_delta(player: dict, power_diff: float) -> Dict[str, int]:
    """PRD v10: 패자 스탯 감소 강화 — 스탯 인플레이션 억제.
    - 기본: 1개 스탯 -1~-3
    - 큰 차이로 졌을 때(power_diff≥15): 추가 1개 스탯 -1
    - 역경에서 배움(sense +1)은 power_diff≥15일 때로 상향
    """
    delta = {k: 0 for k in STAT_KEYS}
    drop_key = random.choice(STAT_KEYS)
    drop_val = random.randint(1, 3)   # -2 max → -3 max
    current = player[drop_key]
    delta[drop_key] = -min(drop_val, current - 1)

    if power_diff >= 15:
        # 압도적 패배: 추가 스탯 하락
        keys_pool = [k for k in STAT_KEYS if k != drop_key]
        extra_key = random.choice(keys_pool)
        delta[extra_key] = -min(1, player[extra_key] - 1)
        # 역경에서 배움 (sense는 빠지지 않음)
        if drop_key != "sense" and extra_key != "sense":
            delta["sense"] = min(1, 100 - player["sense"])
    elif power_diff >= 8:
        # 역경에서 배움 (기존 조건 완화)
        if drop_key != "sense":
            delta["sense"] = min(1, 100 - player["sense"])
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
    series_score: tuple[int, int] = (0, 0),
    build_a: str = "바위",
    build_b: str = "바위",
    strategy_a: str = "균형",
    strategy_b: str = "균형",   # AI/상대방 전략 (PRD v12: 양방향 적용)
) -> SetResult:
    """단일 세트 결과 반환. DB에 쓰지 않는다.

    PRD v7: 초반/중반/후반 3페이즈로 세트 승패 결정.
    - 초반: 빌드 우위 선수에게 BUILD_ADVANTAGE_BOOST
    - 중반: 초반 승자에게 +3 모멘텀
    - 후반: 피로도 +15 시뮬레이션 (체력 저하)
    - 2/3 페이즈 승리 시 세트 승리
    """
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
    # PRD v10 수정: rival_stat을 양쪽에 동일하게 적용하면 상쇄되어 효과 없음.
    # → rival_stat 제거, extra_luck은 "변동성 확장"(extra_luck_range)으로 재설계.
    #   라이벌전에서 양쪽의 luck 범위가 독립적으로 확장 → 더 드라마틱한 경기.
    extra_luck_range = rival_info["extra_luck"] if rival_info else 0

    a_fat = a_fatigue_override if a_fatigue_override is not None else pa.get("fatigue", 0)
    b_fat = b_fatigue_override if b_fatigue_override is not None else pb.get("fatigue", 0)

    eff_a = calc_effective(pa, ia, map_bonus_a, a_condition, rival_bonus=0, fatigue_val=a_fat)
    eff_b = calc_effective(pb, ib, map_bonus_b, b_condition, rival_bonus=0, fatigue_val=b_fat)

    # ── 언더독 부스트 + 강자 패널티 ──────────────────────────
    a_boost = a_penalty = 0
    b_boost = b_penalty = 0

    a_grade = pa["grade"]
    b_grade = pb["grade"]
    try:
        a_idx = GRADE_ORDER.index(a_grade)
        b_idx = GRADE_ORDER.index(b_grade)
    except ValueError:
        a_idx = b_idx = 4

    if a_idx > b_idx:
        boost, penalty = calc_grade_gap_boost(a_grade, b_grade)
        a_boost += boost
        b_penalty += penalty
    elif b_idx > a_idx:
        boost, penalty = calc_grade_gap_boost(b_grade, a_grade)
        b_boost += boost
        a_penalty += penalty

    # ── 다전제 역전 모멘텀 ────────────────────────────────────
    # PRD v13: gap×4 max8 → gap×3 max6 (항상 초반집중이 최적해로 수렴하는 문제 완화)
    a_sets, b_sets = series_score
    gap = abs(b_sets - a_sets)
    comeback = min(gap * 3, 6)
    if b_sets > a_sets:
        a_boost += comeback   # a가 뒤져있으면 역전 의지 부스트
    elif a_sets > b_sets:
        b_boost += comeback

    # ── 빌드 결과 ─────────────────────────────────────────────
    br = calc_build_result(build_a, build_b)

    # ── 전략 보정값 가져오기 (양방향 적용, PRD v12) ──────────
    strat_bonus_a = STRATEGY_PHASE_BONUS.get(strategy_a, STRATEGY_PHASE_BONUS["균형"])
    strat_bonus_b = STRATEGY_PHASE_BONUS.get(strategy_b, STRATEGY_PHASE_BONUS["균형"])

    # ── 페이즈 1: 초반 — 빌드 우위 + 전략 적용 ───────────────
    p1_a_boost = a_boost + (BUILD_ADVANTAGE_BOOST if br > 0 else 0) + strat_bonus_a["초반"]
    p1_b_boost = b_boost + (BUILD_ADVANTAGE_BOOST if br < 0 else 0) + strat_bonus_b["초반"]

    p1_a = calc_power(eff_a, a_grade, extra_luck_range=extra_luck_range,
                      underdog_boost=p1_a_boost, favorite_penalty=a_penalty)
    p1_b = calc_power(eff_b, b_grade, extra_luck_range=extra_luck_range,
                      underdog_boost=p1_b_boost, favorite_penalty=b_penalty)
    p1_winner = player_a_id if p1_a >= p1_b else player_b_id

    # ── 페이즈 2: 중반 — 초반 모멘텀 +2 + 전략 적용 ──────────
    # PRD v13: +3→+2 (전술 우위의 Phase1 승리가 Phase2까지 과도하게 전파되던 문제 완화)
    p2_a_boost = a_boost + (2 if p1_winner == player_a_id else 0) + strat_bonus_a["중반"]
    p2_b_boost = b_boost + (2 if p1_winner == player_b_id else 0) + strat_bonus_b["중반"]

    p2_a = calc_power(eff_a, a_grade, extra_luck_range=extra_luck_range,
                      underdog_boost=p2_a_boost, favorite_penalty=a_penalty)
    p2_b = calc_power(eff_b, b_grade, extra_luck_range=extra_luck_range,
                      underdog_boost=p2_b_boost, favorite_penalty=b_penalty)
    p2_winner = player_a_id if p2_a >= p2_b else player_b_id

    # ── 페이즈 3: 후반 — 피로도 +15 시뮬레이션 + 전략 적용 ───
    eff_a_late = calc_effective(pa, ia, map_bonus_a, a_condition, rival_bonus=0,
                                fatigue_val=min(100, a_fat + 15))
    eff_b_late = calc_effective(pb, ib, map_bonus_b, b_condition, rival_bonus=0,
                                fatigue_val=min(100, b_fat + 15))

    p3_a = calc_power(eff_a_late, a_grade, extra_luck_range=extra_luck_range,
                      underdog_boost=a_boost + strat_bonus_a["후반"], favorite_penalty=a_penalty)
    p3_b = calc_power(eff_b_late, b_grade, extra_luck_range=extra_luck_range,
                      underdog_boost=b_boost + strat_bonus_b["후반"], favorite_penalty=b_penalty)
    p3_winner = player_a_id if p3_a >= p3_b else player_b_id

    # ── 세트 승자: 2/3 페이즈 승리 ───────────────────────────
    a_phase_wins = sum(
        1 for w in [p1_winner, p2_winner, p3_winner] if w == player_a_id
    )
    winner_id = player_a_id if a_phase_wins >= 2 else player_b_id
    loser_id  = player_b_id if winner_id == player_a_id else player_a_id

    phases = [
        PhaseResult("초반", p1_winner, round(p1_a, 2), round(p1_b, 2)),
        PhaseResult("중반", p2_winner, round(p2_a, 2), round(p2_b, 2)),
        PhaseResult("후반", p3_winner, round(p3_a, 2), round(p3_b, 2)),
    ]

    avg_a = round((p1_a + p2_a + p3_a) / 3, 2)
    avg_b = round((p1_b + p2_b + p3_b) / 3, 2)

    return SetResult(
        set_number=set_number,
        winner_id=winner_id,
        loser_id=loser_id,
        a_power=avg_a,
        b_power=avg_b,
        phases=phases,
        build_a=build_a,
        build_b=build_b,
        build_result=br,
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
        a_delta = _apply_winner_delta(winner, upset_stat_bonus if is_upset else None)
        b_delta = _apply_loser_delta(pb, power_diff)
    else:
        b_delta = _apply_winner_delta(winner, upset_stat_bonus if is_upset else None)
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
    """AI 경기: 다전제 완전 자동 시뮬레이션 + DB 저장.

    PRD v7: AI 경기도 빌드를 랜덤 선택해 페이즈 시뮬레이션.
    """
    import random as _random
    from core.builds import BUILD_TYPES

    sets_to_win = SETS_TO_WIN.get(round_name, 2)
    sets: List[SetResult] = []
    a_wins = 0
    b_wins = 0
    set_num = 1

    STRATEGIES = ["초반집중", "균형", "후반체력전"]
    while a_wins < sets_to_win and b_wins < sets_to_win:
        ai_build_a    = _random.choice(BUILD_TYPES)
        ai_build_b    = _random.choice(BUILD_TYPES)
        ai_strategy_a = _random.choice(STRATEGIES)
        ai_strategy_b = _random.choice(STRATEGIES)
        s = simulate_set(
            player_a_id, player_b_id, map_id,
            a_condition, b_condition,
            set_number=set_num,
            series_score=(a_wins, b_wins),
            build_a=ai_build_a,
            build_b=ai_build_b,
            strategy_a=ai_strategy_a,
            strategy_b=ai_strategy_b,
        )
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


# ── 하위 호환 래퍼 ────────────────────────────────────────────
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
