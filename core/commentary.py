"""경기 중계 텍스트 시스템 — 세트별 상황 묘사 문구 풀"""
import random

# ── 상황 판정 ─────────────────────────────────────────────────
# favorable  = A(내 선수) 유리  (power_diff > 5)
# unfavorable = B(상대) 유리   (power_diff < -5)
# close       = 박빙             (|diff| <= 5)

# ── 중계 문구 풀 ──────────────────────────────────────────────
# {a} = A 선수 이름, {b} = B 선수 이름

_POOL: dict[str, dict[str, list[str]]] = {

    # ── 초반 (opening) ───────────────────────────────────────
    "opening": {
        "favorable": [
            "{a}, 빠른 멀티 확장으로 자원 우위 선점!",
            "{a}, 초반 압박으로 {b}를 본진까지 밀어붙인다!",
            "{a}, 완벽한 타이밍으로 포지션 선점 성공.",
            "{a}, 초반 컨트롤부터 한 수 위를 보여주고 있다.",
            "{a}, 적절한 앞마당 전개로 경제적 우위를 가져간다.",
            "{a}의 빌드가 정확히 맞아떨어지며 초반을 지배한다!",
            "{b}가 당황한 사이, {a}는 차분하게 이득을 챙긴다.",
        ],
        "unfavorable": [
            "{b}, 초반 압박에 {a}의 본진까지 밀리는 상황.",
            "{a}, 초반 컨트롤 싸움에서 손해를 보고 있다.",
            "{b}, 기습적인 빌드로 {a}를 당황하게 만든다!",
            "{a}, 초반 타이밍을 놓쳐 수비에 급급한 모습.",
            "{b}, 초반 물량 차이로 {a}를 압도하고 있다.",
            "{a}의 빌드가 역으로 읽혔다. 초반부터 흔들리는 모습.",
            "{b}, 빌드 우위를 살려 {a}를 몰아붙인다!",
        ],
        "close": [
            "양 선수, 초반부터 팽팽한 심리전을 펼치고 있다.",
            "일진일퇴의 초반 공방, 어느 쪽도 우위를 점하지 못하고 있다.",
            "{a}와 {b}, 초반부터 긴장의 끈을 놓지 않는다.",
            "양 선수 모두 신중한 운영으로 탐색전을 이어간다.",
            "초반 교전 없이 안정적으로 멀티를 맞교환하는 양 선수.",
            "빌드 무승부, 두 선수 모두 정석 운영으로 중반을 노린다.",
        ],
    },

    # ── 중반 (midgame) ──────────────────────────────────────
    "midgame": {
        "favorable": [
            "{a}, 폭발적인 물량으로 {b}의 수비를 흔든다!",
            "{a}, 완벽한 전략으로 {b}의 허점을 파고든다.",
            "{a}, 중반 교전을 완승으로 가져가며 격차를 벌린다!",
            "{a}, 빠른 판단력으로 {b}의 주력 병력을 포위!",
            "{a}의 기세가 꺾이지 않는다. {b}, 수비에 전력을 다하는 모습.",
            "초반 우세를 살린 {a}, 중반에도 페이스를 이어간다.",
            "{a}, 핵심 병력 운용에서 압도적인 차이를 보인다!",
        ],
        "unfavorable": [
            "{b}, 폭발적인 역습으로 전세를 뒤집는다!",
            "{a}, 중반 교전에서 연속으로 손해를 보고 있다.",
            "{b}의 전략이 적중하며 {a}를 궁지에 몰아넣는다.",
            "{a}, 수비에 급급한 나머지 멀티 운영에 차질이 생겼다.",
            "{b}, 빠른 전환으로 {a}의 전략을 완벽히 차단!",
            "{a}가 중반에서 흔들린다. {b}, 격차를 점점 벌린다.",
            "{b}, 연속 교전 승리로 경기 주도권을 가져온다!",
        ],
        "close": [
            "일진일퇴의 공방, 두 선수 모두 한 치도 물러서지 않는다.",
            "중반 교전이 팽팽하게 맞물리며 승부를 가늠하기 어렵다.",
            "{a}와 {b}, 서로의 전략을 읽어내며 맞대응 중.",
            "양 선수 모두 실수 없는 완벽한 운영을 이어가고 있다.",
            "중반 병력 싸움이 계속되고 있다. 자원 효율이 결정적 변수!",
            "팽팽한 중반전, 후반의 체력이 승부를 가를 것 같다.",
        ],
    },

    # ── 결정적 장면 (decisive) — 승자 기준 ──────────────────
    "decisive": {
        "favorable": [
            "완벽한 타이밍 공격! {b}의 주력 병력이 전멸한다!",
            "{a}, 쐐기를 박는 결정타! 이 경기는 사실상 끝났다.",
            "{a}, 클러치 컨트롤로 역전의 실마리조차 남기지 않는다!",
            "{b}, 마지막 저항을 시도하지만 역부족이다.",
            "{a}의 마무리가 완벽하다. 세트 승리 확정!",
            "후반 체력 싸움에서도 {a}가 우위를 유지하며 세트를 마무리!",
            "{a}, 막판까지 집중력을 잃지 않고 완벽한 세트 승리!",
        ],
        "unfavorable": [
            "아깝다! 아슬아슬하게 역전을 허용하고 만다.",
            "{b}, 역전의 발판을 마련하며 세트를 가져간다!",
            "{a}, 막판 수비 실수로 기회를 날려버렸다.",
            "{b}, 극적인 역전승! 경기장 분위기가 뒤집혔다!",
            "{a}의 아성이 무너졌다. {b}, 집중력으로 세트 선취!",
            "체력 열세를 극복한 {b}, 극적으로 세트를 가져간다!",
            "막판에 {a}가 흔들렸다. {b}, 끈질기게 버텨 세트 승리!",
        ],
        "close": [
            "마지막 교전, 결정적 실수를 범한 쪽이 패배를 인정한다.",
            "박빙의 승부, 단 하나의 실수가 세트의 운명을 갈랐다.",
            "끝까지 알 수 없었던 세트, 드디어 승부가 결정됐다!",
            "손에 땀을 쥐게 했던 세트, 아슬아슬하게 승자가 가려졌다.",
            "마지막 순간까지 포기하지 않은 두 선수, 더 집중한 쪽이 웃었다.",
            "후반 체력 싸움, 단 한 번의 운영 차이가 세트를 결정지었다.",
        ],
    },
}


def _get_situation(a_power: float, b_power: float) -> str:
    diff = a_power - b_power
    if diff > 5:
        return "favorable"
    elif diff < -5:
        return "unfavorable"
    return "close"


def get_set_commentary(
    a_name: str,
    b_name: str,
    a_power: float,
    b_power: float,
    winner_id: int,
    a_id: int,
    phases: list | None = None,
) -> list[str]:
    """한 세트에 대한 중계 문구 3줄 반환.

    phases가 제공되면 각 페이즈의 실제 파워로 상황을 계산하고
    【초반】/【중반】/【후반】 라벨을 앞에 붙인다.
    """
    sections = ["opening", "midgame", "decisive"]

    if phases and len(phases) == 3:
        lines = []
        for i, phase in enumerate(phases):
            label = f"【{phase.phase_name}】"
            section = sections[i]

            if section == "decisive":
                # 결정적 장면은 실제 페이즈 승자 기준
                sit = "favorable" if phase.winner_id == a_id else "unfavorable"
            else:
                sit = _get_situation(phase.a_power, phase.b_power)

            line = random.choice(_POOL[section][sit]).format(a=a_name, b=b_name)
            lines.append(f"{label} {line}")
        return lines

    # 페이즈 정보 없을 때 폴백 (AI 경기 등)
    situation = _get_situation(a_power, b_power)
    decisive_situation = "favorable" if winner_id == a_id else "unfavorable"
    return [
        random.choice(_POOL["opening"][situation]).format(a=a_name, b=b_name),
        random.choice(_POOL["midgame"][situation]).format(a=a_name, b=b_name),
        random.choice(_POOL["decisive"][decisive_situation]).format(a=a_name, b=b_name),
    ]
