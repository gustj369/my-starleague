WEIGHTS = {
    "control":  0.20,
    "attack":   0.20,
    "defense":  0.15,
    "supply":   0.15,
    "strategy": 0.15,
    "sense":    0.15,
}

GRADE_TABLE = [
    (95, "SSS"),
    (90, "SS"),
    (85, "S"),
    (75, "A"),
    (65, "B"),
    (55, "C"),
    (45, "D"),
    (35, "E"),
    (0,  "F"),
]


def calc_overall(control: int, attack: int, defense: int,
                 supply: int, strategy: int, sense: int) -> float:
    return round(
        control  * WEIGHTS["control"]  +
        attack   * WEIGHTS["attack"]   +
        defense  * WEIGHTS["defense"]  +
        supply   * WEIGHTS["supply"]   +
        strategy * WEIGHTS["strategy"] +
        sense    * WEIGHTS["sense"],
        2
    )


def calc_grade(overall: float) -> str:
    for threshold, grade in GRADE_TABLE:
        if overall >= threshold:
            return grade
    return "F"


GRADE_COLORS = {
    # 라이트 테마 기준 — 흰/밝은 배경에서 명확히 읽힐 것
    "SSS": "#F59E0B",   # 골드 (라이트 테마 골드)
    "SS":  "#868E96",   # 실버 (중간 회색)
    "S":   "#5B6CF6",   # 인디고 (라이트 테마 주색)
    "A":   "#3B82F6",   # 파란색
    "B":   "#51CF66",   # 초록
    "C":   "#ADB5BD",   # 연회색 (흰 배경에서 보임, 기존 #FFFFFF 버그 수정)
    "D":   "#F59E0B",   # 주황/골드
    "E":   "#FF6B6B",   # 산호 빨강
    "F":   "#EF5350",   # 빨강
}
