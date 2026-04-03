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
    "SSS": "#FFD700",   # 금색
    "SS":  "#E8E8E8",   # 밝은 은색
    "S":   "#C0C0C0",   # 은색
    "A":   "#4FC3F7",   # 청색
    "B":   "#81C784",   # 녹색
    "C":   "#FFFFFF",   # 흰색
    "D":   "#FFB74D",   # 주황색
    "E":   "#EF9A9A",   # 연한 빨강
    "F":   "#EF5350",   # 빨강
}
