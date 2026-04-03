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
    "최상": "#4fc3f7",
    "보통": "#c8d8e8",
    "저조": "#EF9A9A",
}

# 등급별 컨디션 확률 [최상, 보통, 저조]
# 고등급일수록 저조 확률↑ (강한 선수도 컨디션 난조 가능)
CONDITION_PROB = {
    "SSS": [0.20, 0.50, 0.30],
    "SS":  [0.20, 0.50, 0.30],
    "S":   [0.30, 0.50, 0.20],
    "A":   [0.30, 0.50, 0.20],
    "B":   [0.40, 0.45, 0.15],
    "C":   [0.40, 0.45, 0.15],
    "D":   [0.40, 0.45, 0.15],
    "E":   [0.40, 0.45, 0.15],
    "F":   [0.40, 0.45, 0.15],
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
def luck_range(grade: str) -> tuple[int, int]:
    """등급별 운 범위 반환. SSS/SS는 폭이 넓어 이변 가능성↑"""
    if grade in ("SSS", "SS"):
        return (-15, 15)
    elif grade in ("S", "A"):
        return (-10, 10)
    else:
        return (-5, 5)


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


def calc_power(eff: dict, grade: str, extra_luck: int = 0) -> float:
    """유효 스탯 → 전투력 (평균 + 랜덤 운)"""
    lo, hi = luck_range(grade)
    luck = random.randint(lo, hi) + extra_luck
    base = sum(eff[k] for k in STAT_KEYS) / len(STAT_KEYS)
    return round(base + luck, 2)
