"""밸런스 시스템 — 핸디캡 / 컨디션 / 피로도 / 라이벌 / 이변 보상"""
import random
from database.db import get_connection

STAT_KEYS   = ["control", "attack", "defense", "supply", "strategy", "sense"]
GRADE_ORDER = ["SSS", "SS", "S", "A", "B", "C", "D", "E", "F"]

# ── 컨디션 ────────────────────────────────────────────────────
CONDITIONS = ["최상", "보통", "저조"]

CONDITION_MULT = {
    "최상": 1.10,
    "보통": 1.00,
    "저조": 0.90,
}

CONDITION_COLOR = {
    "최상": "#51CF66",
    "보통": "#868E96",
    "저조": "#FF6B6B",
}

# 등급별 컨디션 확률 [최상, 보통, 저조]
# 고등급일수록 안정적(보통 비율↑), 저등급일수록 변동 폭 큼.
# 모든 등급에서 기대 컨디션 배수 ≈ 1.0 (최상%=저조%로 중립 유지).
CONDITION_PROB = {
    "SSS": [0.15, 0.70, 0.15],   # 매우 안정적
    "SS":  [0.18, 0.64, 0.18],
    "S":   [0.20, 0.60, 0.20],   # 안정
    "A":   [0.25, 0.50, 0.25],   # 균형
    "B":   [0.30, 0.40, 0.30],   # 변동 있음
    "C":   [0.33, 0.34, 0.33],   # 높은 변동
    "D":   [0.35, 0.30, 0.35],
    "E":   [0.35, 0.30, 0.35],
    "F":   [0.35, 0.30, 0.35],
}

# ── 피로도 ────────────────────────────────────────────────────
FATIGUE_INC = {
    "16강": 10,
    "8강":  15,
    "4강":  20,
    "결승": 25,
}


def fatigue_mult(fatigue: int) -> float:
    if fatigue <= 30:
        return 1.00
    elif fatigue <= 60:
        return 0.95
    elif fatigue <= 80:
        return 0.88
    else:
        return 0.80


def add_fatigue(player_id: int, round_name: str):
    """라운드 종료 후 피로도 증가 (최대 100)"""
    inc = FATIGUE_INC.get(round_name, 10)
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET fatigue = MIN(100, fatigue + ?) WHERE id = ?",
            (inc, player_id)
        )
        conn.commit()


# ── 컨디션 롤 ─────────────────────────────────────────────────
def roll_condition(grade: str) -> str:
    probs = CONDITION_PROB.get(grade, [0.40, 0.45, 0.15])
    return random.choices(CONDITIONS, weights=probs, k=1)[0]


def apply_condition_item(condition: str) -> str:
    """에너지 드링크 사용 시 컨디션 1단계 상승"""
    if condition == "저조":
        return "보통"
    elif condition == "보통":
        return "최상"
    return "최상"


# ── 핸디캡 (랜덤 범위) ────────────────────────────────────────
# 하위 등급일수록 랜덤 폭이 넓어 "운이 좋은 날" 이변 가능 (PRD v6)
# B(±20) vs S(±10): 강한 B ~20% 이변 확률, 약한 B ~6% — 스탯 차이가 의미 있음
_LUCK_RANGE: dict[str, int] = {
    "SSS": 7,    # 최고 등급 — 안정적, 소폭 하향
    "SS":  8,
    "S":   10,
    "A":   13,   # 15→13: S와의 갭 축소, 이변 빈도 조정
    "B":   18,   # 20→18: 약간 안정화
    "C":   21,
    "D":   24,
    "E":   26,
    "F":   28,   # 최하위 — 최대 변동성 (역전 드라마 가능)
}


def luck_range(grade: str) -> tuple[int, int]:
    """등급별 운 범위 반환"""
    r = _LUCK_RANGE.get(grade, 15)
    return (-r, r)


def calc_grade_gap_boost(underdog_grade: str, favorite_grade: str) -> tuple[int, int]:
    """언더독 부스트 및 강자 패널티.

    PRD v6: 등급 차 boost는 적용하지 않음 — 넓은 luck 범위로 자연스럽게 이변 발생.
    다전제 모멘텀(comeback) 보정만 simulate_set에서 유지.
    """
    return (0, 0)


def get_locked_map_id(player: dict, maps: list[dict]) -> int | None:
    """SSS/SS 선수는 자신에게 가장 유리한 맵이 고정됨 (핸디캡)"""
    grade = player.get("grade", "C")
    if grade not in ("SSS", "SS"):
        return None

    race = player.get("race", "")
    bonus_col = {
        "테란":   "terran_bonus",
        "저그":   "zerg_bonus",
        "프로토스": "protoss_bonus",
    }.get(race)

    if not bonus_col or not maps:
        return None

    best = max(maps, key=lambda m: m.get(bonus_col, 0))
    return best["id"]


# ── 라이벌 ────────────────────────────────────────────────────
def get_rival_info(a_id: int, b_id: int) -> dict | None:
    """두 선수 간 라이벌 정보 조회. 없으면 None"""
    with get_connection() as conn:
        row = conn.execute(
            """SELECT stat_bonus, extra_luck FROM rivals
               WHERE player_a_id = ? AND player_b_id = ?""",
            (a_id, b_id)
        ).fetchone()
    if row:
        return {"stat_bonus": row["stat_bonus"], "extra_luck": row["extra_luck"]}
    return None


def is_rival(a_id: int, b_id: int) -> bool:
    return get_rival_info(a_id, b_id) is not None


def get_h2h_record(player_a_id: int, player_b_id: int) -> dict:
    """두 선수 간 통산 맞대결 전적 반환
    Returns: {"total": int, "a_wins": int, "b_wins": int}
    """
    with get_connection() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN winner_id = ? THEN 1 ELSE 0 END) as a_wins
               FROM match_results
               WHERE (player_a_id = ? AND player_b_id = ?)
                  OR (player_a_id = ? AND player_b_id = ?)""",
            (player_a_id, player_a_id, player_b_id, player_b_id, player_a_id)
        ).fetchone()
    total = row["total"] or 0
    a_wins = row["a_wins"] or 0
    return {"total": total, "a_wins": a_wins, "b_wins": total - a_wins}


# ── 이변 ──────────────────────────────────────────────────────
def calc_upset_level(winner_grade: str, loser_grade: str) -> int:
    """이변 레벨 — 양수면 하위 등급이 상위 등급을 이긴 것"""
    try:
        wi = GRADE_ORDER.index(winner_grade)
        li = GRADE_ORDER.index(loser_grade)
        return li - wi   # 양수 = 이변
    except ValueError:
        return 0


def calc_upset_rewards(diff: int) -> tuple[int, dict]:
    """이변 레벨에 따른 골드 + 스탯 보너스 반환 (PRD v4 기준)

    1등급 차이: +80G,  랜덤 1개 항목 +2
    2등급 차이: +150G, 랜덤 2개 항목 +3
    3+등급 차이: +300G, 전 능력치 +2
    """
    if diff <= 0:
        return (0, {})

    stat_delta = {k: 0 for k in STAT_KEYS}

    if diff == 1:
        gold = 80
        key = random.choice(STAT_KEYS)
        stat_delta[key] = 2
    elif diff == 2:
        gold = 150
        keys = random.sample(STAT_KEYS, 2)
        for k in keys:
            stat_delta[k] = 3
    else:  # diff >= 3
        gold = 300
        for k in STAT_KEYS:
            stat_delta[k] = 2

    return (gold, stat_delta)


# ── 유효 스탯 계산 ────────────────────────────────────────────
def calc_effective(
    player: dict,
    stat_items: dict,      # {stat_key: bonus_sum}
    map_bonus: int,
    condition: str,
    rival_bonus: int = 0,
    fatigue_val: int | None = None,
) -> dict:
    """
    최종 유효 스탯 딕셔너리 반환.
    stat_items: 보유 아이템 합산 보너스
    map_bonus:  맵 종족 보너스 (전체 스탯에 균등 적용)
    condition:  '최상' / '보통' / '저조'
    rival_bonus: 라이벌전 스탯 보너스
    fatigue_val: override (None이면 player['fatigue'] 사용)
    """
    fat = fatigue_val if fatigue_val is not None else player.get("fatigue", 0)
    fat_m = fatigue_mult(fat)
    cond_m = CONDITION_MULT.get(condition, 1.00)

    eff = {}
    for key in STAT_KEYS:
        base = player.get(key, 50)
        item_b = stat_items.get(key, 0)
        val = (base + item_b + map_bonus + rival_bonus) * fat_m * cond_m
        eff[key] = val
    return eff


def calc_power(eff: dict, grade: str, extra_luck_range: int = 0,
               underdog_boost: int = 0, favorite_penalty: int = 0) -> float:
    """유효 스탯 → 전투력 (평균 + 랜덤 운).

    extra_luck_range:  라이벌전 등 드라마 상황에서 운의 범위를 양방향 확장.
                       (양쪽에 동일 상수를 더하면 상쇄되므로, 범위 확장으로 변동성↑)
    underdog_boost:    언더독 랜덤 상한 확장 (등급 차·모멘텀 기반)
    favorite_penalty:  강자 랜덤 상한 축소 (심리적 이완)
    """
    lo, hi = luck_range(grade)
    adj_lo = lo - extra_luck_range          # 하한도 확장 → 독립 변수로 진짜 변동성↑
    adj_hi = hi + underdog_boost - favorite_penalty + extra_luck_range
    luck = random.uniform(adj_lo, adj_hi)
    base = sum(eff[k] for k in STAT_KEYS) / len(STAT_KEYS)
    return round(base + luck, 2)
