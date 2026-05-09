"""밸런스 시스템 — 핸디캡 / 컨디션 / 피로도 / 라이벌 / 이변 보상"""
import random
from database.db import get_connection
from core.utils import STAT_KEYS  # noqa: F401 — match.py 등 하위 임포트 경로 유지

GRADE_ORDER = ["Super", "SS", "S", "A", "B", "C", "D", "E", "F"]

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
    "Super": [0.15, 0.70, 0.15], # 매우 안정적
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


def apply_fatigue_item(current_fatigue: int) -> int:
    """피로회복 아이템: 피로도를 한 구간 아래로 점프.

    언제 사용해도 의미 있도록 구간 단위로 이동.
      81~100 (×0.80) → 60  (×0.88 구간 진입점)
      61~80  (×0.88) → 30  (×0.95 구간 진입점)
      31~60  (×0.95) →  0  (×1.00 최적 구간)
       0~30  (×1.00) → 변화 없음 (이미 최적)
    """
    if current_fatigue > 80:
        return 60
    elif current_fatigue > 60:
        return 30
    elif current_fatigue > 30:
        return 0
    return current_fatigue  # 이미 최적 구간


# ── 핸디캡 (랜덤 범위) ────────────────────────────────────────
# 하위 등급일수록 랜덤 폭이 넓어 "운이 좋은 날" 이변 가능 (PRD v6)
# B(±20) vs S(±10): 강한 B ~20% 이변 확률, 약한 B ~6% — 스탯 차이가 의미 있음
_LUCK_RANGE: dict[str, int] = {
    "Super": 7,
    "SS":  8,
    "S":   10,
    "A":   13,
    "B":   20,   # ±20: S(±10)와 격차 확보 → 이변 여지 확보
    "C":   22,
    "D":   24,
    "E":   26,
    "F":   28,
}


def luck_range(grade: str) -> tuple[int, int]:
    """등급별 운 범위 반환"""
    r = _LUCK_RANGE.get(grade, 15)
    return (-r, r)


def calc_grade_gap_boost(underdog_grade: str, favorite_grade: str) -> tuple[int, int]:
    """언더독 부스트 및 강자 패널티.

    등급 차가 클수록 하위 등급 선수의 luck 상한이 확장되고,
    상위 등급 선수의 luck 상한이 축소됨 → 이변 확률 증가.

    Returns: (underdog_boost, favorite_penalty)

    1등급 차 (A vs B):   boost=5,  penalty=2  → 이변 ~20%
    2등급 차 (S vs B):   boost=9,  penalty=3  → 이변 ~25%
    3등급 차 (A vs D):   boost=14, penalty=4  → 이변 ~12%
    4등급 차 (S vs F):   boost=20, penalty=5  → 이변 ~5%
    5등급+ 차 (Super vs D): boost=27, penalty=6 → 이변 ~2% (기적)
    ── 기존 3등급 상한에서 단층을 없애 등급 차에 비례한 연속 스케일 적용 ──
    """
    try:
        u_idx = GRADE_ORDER.index(underdog_grade)
        f_idx = GRADE_ORDER.index(favorite_grade)
        diff = u_idx - f_idx   # 양수 = 언더독이 하위 등급
    except ValueError:
        return (0, 0)

    if diff <= 0:
        return (0, 0)
    elif diff == 1:
        return (5, 2)    # 1등급 차: 미세 보정
    elif diff == 2:
        return (9, 3)    # 2등급 차 (S vs B): 이변 ~25%
    elif diff == 3:
        return (14, 4)   # 3등급 차: 이변 ~12%
    elif diff == 4:
        return (20, 5)   # 4등급 차: 이변 ~5%
    else:
        return (27, 6)   # 5등급+ 차: 기적적 이변 (~2%)


def get_locked_map_id(player: dict, maps: list[dict]) -> int | None:
    """Super/SS 선수는 자신에게 가장 불리한 맵이 강제 지정됨 (진짜 핸디캡).

    설계 의도: 최강 등급일수록 최악의 환경에서 경기해 난이도를 높임.
    → 이전 구현(최고 맵 고정)이 오히려 이점이 되던 문제 수정.
    """
    grade = player.get("grade", "C")
    if grade not in ("Super", "SS"):
        return None

    race = player.get("race", "")
    bonus_col = {
        "테란":   "terran_bonus",
        "저그":   "zerg_bonus",
        "프로토스": "protoss_bonus",
    }.get(race)

    if not bonus_col or not maps:
        return None

    # 종족 보너스가 가장 낮은 맵 → 진짜 불리한 환경
    worst = min(maps, key=lambda m: m.get(bonus_col, 0))
    return worst["id"]


# ── 라이벌 ────────────────────────────────────────────────────
def get_rival_info(a_id: int, b_id: int, _cur=None) -> dict | None:
    """두 선수 간 라이벌 정보 조회. 없으면 None.

    _cur: 공유 커서를 전달하면 별도 연결을 열지 않는다 (내부용).
    """
    if _cur is not None:
        row = _cur.execute(
            """SELECT stat_bonus, extra_luck FROM rivals
               WHERE player_a_id = ? AND player_b_id = ?""",
            (a_id, b_id)
        ).fetchone()
    else:
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

    # BUG-04 수정: map_bonus(지형 이점)는 선수의 컨디션·피로도와 무관한 환경 변수이므로
    # fat_m * cond_m 배수 적용 밖에서 평탄 가산.
    # 이전 코드에서는 map_bonus도 배수가 곱해져 최상 컨디션+최고 맵보너스 시
    # 복합 증폭이 발생하였음.
    eff = {}
    for key in STAT_KEYS:
        base = player.get(key, 50)
        item_b = stat_items.get(key, 0)
        val = (base + item_b + rival_bonus) * fat_m * cond_m + map_bonus
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
