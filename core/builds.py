"""전술 삼각 시스템 — 공세/수비/기동 순환 우위

PRD v11: 스타크래프트 IP 제거.
  가위/바위/보 + 종족별 빌드명 → 독창적 전술 삼각체계로 대체.
  디자인 근거: Aggression > Defense > Mobility > Aggression (순환 우위)
    - 공세: 빠른 압박, 초반 우위 추구  (Aggression)
    - 수비: 진지 구축, 지속전 선호     (Defense)
    - 기동: 유연한 우회, 분산 전략     (Mobility)
  공세 → 수비 → 기동 → 공세 (앞이 뒤를 이김)
"""

# ── 전술 유형 ─────────────────────────────────────────────────
TACTIC_TYPES = ["공세", "수비", "기동"]

# 전술 유형별 세부 설명 (UI 툴팁용)
TACTIC_DESC = {
    "공세": "빠른 선제 압박으로 상대를 제압. 수비전에 강하나 기동전에 취약.",
    "수비": "견고한 진지 구축과 지속전. 기동전에 강하나 공세에 취약.",
    "기동": "유연한 우회와 분산 기습. 공세에 강하나 수비전에 취약.",
}

# 전술 유형별 대표 전법명 (순수 오리지널, 종족 무관)
TACTIC_NAMES = {
    "공세": "속공 돌파",
    "수비": "진지 사수",
    "기동": "우회 기습",
}

# 전술 우열 관계: {이기는_전술: 지는_전술}
# 공세 > 수비 > 기동 > 공세
TACTIC_WINS = {"공세": "수비", "수비": "기동", "기동": "공세"}

# 전술 우위 시 초반 페이즈 파워 부스트
# PRD v10 유지: 15→10 (전략 보너스와 중복 시 스탯 차이를 압도하는 문제 해소)
TACTIC_ADVANTAGE_BOOST = 10

# ── 하위 호환성 alias ─────────────────────────────────────────
BUILD_TYPES          = TACTIC_TYPES
BUILD_ADVANTAGE_BOOST = TACTIC_ADVANTAGE_BOOST
RPS_WINS             = TACTIC_WINS


def get_build_name(my_tactic: str, opp_tactic: str = "", build_type: str = "") -> str:
    """전술 유형에 맞는 전법 이름 반환.

    이전 시그니처 (my_race, opp_race, build_type)와 호환:
    첫 번째 인자만 사용해 전술 이름을 반환한다.
    """
    # build_type이 전술 타입이면 그것을 우선 사용 (레거시 호환)
    key = build_type if build_type in TACTIC_NAMES else my_tactic
    return TACTIC_NAMES.get(key, key)


def calc_build_result(tactic_a: str, tactic_b: str) -> int:
    """전술 우열 계산.

    Returns:
        +1: a 우세 (a가 b를 이김)
         0: 무승부
        -1: b 우세 (b가 a를 이김)
    """
    if tactic_a == tactic_b:
        return 0
    if TACTIC_WINS.get(tactic_a) == tactic_b:
        return 1
    return -1
