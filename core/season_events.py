"""시즌 시작 랜덤 이벤트 시스템"""
import json
import random
from database.db import get_connection

# ── 이벤트 풀 정의 ────────────────────────────────────────────
# effect: "gold" | "fatigue" | "narrative"
# target: 선수 이름 (fatigue), None (gold/narrative)
# value: 골드 변동(gold), 피로도 추가량(fatigue)
EVENT_POOL = [
    # 골드 이벤트
    {"id": "e01", "icon": "💰", "title": "스폰서십 계약 체결",
     "desc": "이번 시즌 새 스폰서가 등장했다. 추가 자금이 확보됐다.",
     "effect": "gold", "target": None, "value": 250},
    {"id": "e02", "icon": "📉", "title": "운영비 폭등",
     "desc": "시즌 준비 비용 청구서가 날아왔다. 골드가 감소했다.",
     "effect": "gold", "target": None, "value": -180},
    {"id": "e03", "icon": "🏆", "title": "전 시즌 성적 보너스",
     "desc": "지난 시즌 활약에 대한 리그 지원금이 들어왔다.",
     "effect": "gold", "target": None, "value": 150},

    # 피로도 페널티 이벤트 (특정 선수)
    {"id": "e04", "icon": "💥", "title": "드레이븐, 극한 특훈 강행",
     "desc": "드레이븐이 시즌 전 무리한 훈련을 강행했다. 피로가 쌓인 채로 출발한다.",
     "effect": "fatigue", "target": "드레이븐", "value": 28},
    {"id": "e05", "icon": "😴", "title": "루엔, 과도한 연습 게임",
     "desc": "루엔이 시즌 전 밤새 연습을 반복했다. 지친 상태로 리그에 임한다.",
     "effect": "fatigue", "target": "루엔", "value": 25},
    {"id": "e06", "icon": "⚡", "title": "카이렌, 분노의 훈련",
     "desc": "카이렌이 지난 시즌 탈락에 분개해 쉬지 않고 훈련했다. 체력이 소진됐다.",
     "effect": "fatigue", "target": "카이렌", "value": 22},
    {"id": "e07", "icon": "🔥", "title": "모르칸, 무리한 스파링",
     "desc": "모르칸이 시즌 전 15연속 스파링을 소화했다. 피로가 누적됐다.",
     "effect": "fatigue", "target": "모르칸", "value": 30},
    {"id": "e08", "icon": "💤", "title": "아셀, 컨디션 조절 실패",
     "desc": "아셀이 이번 시즌 준비 기간에 컨디션 관리에 실패했다.",
     "effect": "fatigue", "target": "아셀", "value": 20},
    {"id": "e09", "icon": "⚠️", "title": "티렌, 불규칙한 생활",
     "desc": "티렌이 시즌 전 불규칙한 생활로 체력이 저하됐다.",
     "effect": "fatigue", "target": "티렌", "value": 24},
    {"id": "e10", "icon": "🎮", "title": "카엘, 부상 직전 무리",
     "desc": "카엘이 성장 욕심에 과도하게 훈련했다. 이번 시즌 체력 부담이 크다.",
     "effect": "fatigue", "target": "카엘", "value": 20},

    # 순수 서사 이벤트
    {"id": "e11", "icon": "🔥", "title": "세라온-드레이븐 라이벌 구도 격화",
     "desc": "세라온과 드레이븐의 라이벌 구도가 이번 시즌 더욱 뜨거워졌다. 맞대결이 주목된다.",
     "effect": "narrative", "target": None, "value": 0},
    {"id": "e12", "icon": "❄️", "title": "하린, 침묵 속 준비 완료",
     "desc": "하린이 이번 시즌 내내 인터뷰를 거부하며 조용히 준비했다. 경기력에 기대가 모인다.",
     "effect": "narrative", "target": None, "value": 0},
    {"id": "e13", "icon": "🌟", "title": "에리나, '이번엔 진심' 발언",
     "desc": "에리나가 이번 시즌 만큼은 결승까지 간다고 선언했다. 팬들의 기대가 높아졌다.",
     "effect": "narrative", "target": None, "value": 0},
    {"id": "e14", "icon": "📣", "title": "루카스, 전략 분석 영상 공개",
     "desc": "루카스가 이번 시즌 상대 전략 분석 영상을 공개했다. 상대방들은 긴장하고 있다.",
     "effect": "narrative", "target": None, "value": 0},
    {"id": "e15", "icon": "⚔️", "title": "루엔-하린, 시즌 전 신경전",
     "desc": "루엔과 하린이 인터뷰에서 날선 말을 주고받았다. 맞대결 시 분위기가 심상치 않다.",
     "effect": "narrative", "target": None, "value": 0},
    {"id": "e16", "icon": "🚀", "title": "나이엘, 최고의 컨디션",
     "desc": "나이엘이 이번 시즌 최상의 컨디션이라고 밝혔다. 조기 탈락은 없을 전망이다.",
     "effect": "narrative", "target": None, "value": 0},
    {"id": "e17", "icon": "🎭", "title": "비올렌, 미스터리한 등장",
     "desc": "비올렌이 이번 시즌 새로운 전략을 들고 왔다는 소문이 돈다. 무엇을 준비했을지 아무도 모른다.",
     "effect": "narrative", "target": None, "value": 0},
    {"id": "e18", "icon": "💪", "title": "오린, 체력 단련 완료",
     "desc": "오린이 이번 시즌 전 체력 훈련에만 집중했다. 후반부 경기력이 기대된다.",
     "effect": "narrative", "target": None, "value": 0},
    {"id": "e19", "icon": "🌊", "title": "벨리아, 베테랑의 여유",
     "desc": "벨리아는 이번 시즌도 흔들림 없이 준비했다는 평가다. 안정감이 돋보인다.",
     "effect": "narrative", "target": None, "value": 0},
    {"id": "e20", "icon": "🎯", "title": "세린, 팀워크 특훈",
     "desc": "세린이 이번 시즌 파트너십 향상에 집중했다. 중요한 순간 활약이 기대된다.",
     "effect": "narrative", "target": None, "value": 0},
]


def generate_events(count: int = 2) -> list[dict]:
    """랜덤으로 이벤트 count개 선택 (중복 없음)"""
    gold_events      = [e for e in EVENT_POOL if e["effect"] == "gold"]
    fatigue_events   = [e for e in EVENT_POOL if e["effect"] == "fatigue"]
    narrative_events = [e for e in EVENT_POOL if e["effect"] == "narrative"]

    picked = []
    # 골드 or 피로 이벤트 1개
    pool1 = gold_events + fatigue_events
    if pool1:
        picked.append(random.choice(pool1))
    # 서사 이벤트 1개
    if narrative_events:
        picked.append(random.choice(narrative_events))
    # 추가로 count-2개 더 (피로/골드 위주)
    remaining = [e for e in pool1 if e not in picked]
    for _ in range(max(0, count - 2)):
        if remaining:
            ev = random.choice(remaining)
            picked.append(ev)
            remaining.remove(ev)
    return picked[:count]


def apply_gold_events(events: list[dict]) -> int:
    """골드 이벤트 즉시 적용. 변동 총액 반환."""
    from database.db import add_gold
    total_delta = 0
    for ev in events:
        if ev["effect"] == "gold":
            add_gold(ev["value"])
            total_delta += ev["value"]
    return total_delta


def store_fatigue_events(events: list[dict]):
    """피로도 이벤트를 game_state에 JSON으로 저장 (create_tournament 이후 적용용)"""
    fatigue_evs = [e for e in events if e["effect"] == "fatigue"]
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO game_state (key, value) VALUES ('pending_fatigue_events', ?)",
            (json.dumps(fatigue_evs),)
        )
        conn.commit()


def apply_pending_fatigue_events():
    """저장된 피로도 이벤트를 DB에 적용하고 삭제"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM game_state WHERE key='pending_fatigue_events'"
        ).fetchone()
        if not row:
            return
        events = json.loads(row["value"])
        for ev in events:
            target = ev.get("target")
            value  = ev.get("value", 0)
            if target and value > 0:
                conn.execute(
                    "UPDATE players SET fatigue = MIN(100, fatigue + ?) WHERE name = ?",
                    (value, target)
                )
        conn.execute("DELETE FROM game_state WHERE key='pending_fatigue_events'")
        conn.commit()


def get_effect_summary(ev: dict) -> str:
    if ev["effect"] == "gold":
        sign = "+" if ev["value"] > 0 else ""
        return f"골드 {sign}{ev['value']}G"
    elif ev["effect"] == "fatigue":
        return f"{ev['target']} 피로도 +{ev['value']}"
    else:
        return "서사 이벤트"
