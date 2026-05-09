"""공통 유틸리티 — 여러 모듈에서 공유하는 상수/헬퍼"""


def _safe_int(value, default: int = 0) -> int:
    """문자열·None 등을 int로 안전하게 변환. 변환 불가 시 default 반환."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


STAT_KEYS = ["control", "attack", "defense", "supply", "strategy", "sense"]

STAT_LABELS = {
    "control":  "컨트롤",
    "attack":   "공격력",
    "defense":  "수비력",
    "supply":   "물량",
    "strategy": "전략",
    "sense":    "센스",
}
