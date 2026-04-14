from database.db import get_connection, init_db
from core.grade import calc_overall, calc_grade

# PRD v6: 저작권 문제로 전체 캐릭터를 새 이름으로 교체
# 이미지 파일: ../image/{이름}.png
# 등급: 초기 최고 S (SSS/SS 없음)

PLAYERS = [
    # (name, race, control, attack, defense, supply, strategy, sense)
    # ── 테란 6명 ──────────────────────────────────────────────
    ("나이엘",  "테란",   88, 90, 84, 82, 86, 87),   # S  ~86.5
    ("드레이븐","테란",   84, 88, 80, 78, 82, 84),   # A  ~83.0
    ("루카스",  "테란",   80, 83, 76, 75, 79, 80),   # A  ~79.1
    ("아셀",    "테란",   72, 73, 68, 67, 70, 71),   # B  ~70.4
    ("카엘",    "테란",   68, 69, 65, 64, 67, 68),   # B  ~67.0
    ("티렌",    "테란",   67, 68, 65, 65, 66, 67),   # B  ~66.5
    # ── 저그 5명 ──────────────────────────────────────────────
    ("루엔",    "저그",   86, 88, 82, 90, 84, 86),   # S  ~86.1
    ("모르칸",  "저그",   82, 85, 78, 86, 80, 82),   # A  ~82.3
    ("세라온",  "저그",   78, 80, 75, 82, 77, 78),   # A  ~78.4
    ("오린",    "저그",   74, 76, 71, 78, 73, 74),   # B  ~74.4
    ("카이렌",  "저그",   69, 71, 67, 73, 69, 70),   # B  ~69.9
    # ── 프로토스 5명 ──────────────────────────────────────────
    ("벨리아",  "프로토스", 83, 82, 86, 80, 89, 84), # A  ~83.9
    ("비올렌",  "프로토스", 80, 79, 83, 77, 85, 80), # A  ~80.6
    ("세린",    "프로토스", 77, 76, 80, 74, 81, 77), # A  ~77.4
    ("에리나",  "프로토스", 73, 72, 75, 70, 77, 73), # B  ~73.3
    ("하린",    "프로토스", 69, 68, 72, 67, 73, 70), # B  ~69.7
]

MAPS = [
    # (name, terran_bonus, zerg_bonus, protoss_bonus)
    ("블리츠",        +5, -3, +2),
    ("파이썬",        -2, +6, +1),
    ("네오 포비든존",  +3, +2, -2),
    ("아즈텍",        +1, -4, +7),
    ("로스트 템플",    0,  +4, +3),
    # PRD v10 추가 맵
    ("데스티네이션",   -3, +3, +5),   # 저그/프로토스 특화
    ("스타게이트",     +4, +1, -2),   # 테란 특화
    ("블루스톰",       +2, -5, +6),   # 프로토스 강점
    ("루나",           -1, +5, +2),   # 저그 강점
    ("투혼",           +3, +2, +2),   # 균형 맵
]

# PRD v6 아이템 (12개)
# (name, description, price, item_type, ctrl, atk, def_, sup, strat, sen, condition_up, fatigue_recover)
ITEMS = [
    # ── 단일 능력치 (+5) ──────────────────────────────
    ("컨트롤 강화제",  "컨트롤 +5",              150, "능력치",   5, 0, 0, 0, 0, 0, 0,  0),
    ("공격력 강화제",  "공격력 +5",              150, "능력치",   0, 5, 0, 0, 0, 0, 0,  0),
    ("수비력 강화제",  "수비력 +5",              150, "능력치",   0, 0, 5, 0, 0, 0, 0,  0),
    ("전략 매뉴얼",    "전략 +5",                150, "능력치",   0, 0, 0, 0, 5, 0, 0,  0),
    ("물량 부스터",    "물량 +5",                150, "능력치",   0, 0, 0, 5, 0, 0, 0,  0),
    ("센스 훈련서",    "센스 +5",                150, "능력치",   0, 0, 0, 0, 0, 5, 0,  0),
    # ── 복합 능력치 ───────────────────────────────────
    ("올스탯 강화제",  "전 능력치 +2",            350, "능력치",   2, 2, 2, 2, 2, 2, 0,  0),
    ("집중력 강화제",  "컨트롤·전략 +4",          250, "능력치",   4, 0, 0, 0, 4, 0, 0,  0),
    ("전투 훈련서",    "공격력·수비력 +4",         250, "능력치",   0, 4, 4, 0, 0, 0, 0,  0),
    # ── 컨디션 ───────────────────────────────────────
    ("에너지 드링크",  "컨디션 한 단계 상승",      200, "컨디션",   0, 0, 0, 0, 0, 0, 1,  0),
    # ── 피로 회복 ─────────────────────────────────────
    ("휴식 아이템",    "피로도 -30",              180, "피로회복", 0, 0, 0, 0, 0, 0, 0, 30),
    ("피로회복제",     "피로도 -50",              280, "피로회복", 0, 0, 0, 0, 0, 0, 0, 50),
]

# 라이벌 관계 PRD v9: 캐릭터 설정 기반 전면 개편
# (선수A, 선수B, stat_bonus, extra_luck)
RIVALS = [
    # 핵심 라이벌 — 양방향 확인됨
    ("세라온",  "드레이븐", 5, 4),
    ("루엔",    "하린",     5, 4),
    ("카이렌",  "오린",     4, 3),
    ("벨리아",  "세린",     4, 3),
    ("나이엘",  "티렌",     4, 3),
    # 보조 라이벌 — 일방향 선언
    ("에리나",  "루엔",     3, 2),
    ("모르칸",  "카이렌",   3, 2),
    ("카엘",    "티렌",     3, 2),
    ("비올렌",  "하린",     3, 2),
    ("루카스",  "벨리아",   3, 2),
]

# DB 버전: PRD v6
DB_VERSION = 6


def seed():
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    # ── DB 버전 확인 → v6 미만이면 전체 리셋 ─────────────────
    version_row = cur.execute(
        "SELECT value FROM game_state WHERE key='db_version'"
    ).fetchone()
    current_version = int(version_row[0]) if version_row else 0

    if current_version < DB_VERSION:
        # 전체 데이터 초기화 (캐릭터 교체로 인한 마이그레이션)
        cur.executescript("""
            DELETE FROM tournament_matches;
            DELETE FROM tournaments;
            DELETE FROM player_items;
            DELETE FROM rivals;
            DELETE FROM match_results;
            DELETE FROM players;
            DELETE FROM items;
            DELETE FROM game_state;
        """)
        cur.execute(
            "INSERT INTO game_state (key, value) VALUES ('db_version', ?)",
            (str(DB_VERSION),)
        )
        cur.execute(
            "INSERT INTO game_state (key, value) VALUES ('gold', '500')"
        )
        cur.execute(
            "INSERT INTO game_state (key, value) VALUES ('total_tournaments_played', '0')"
        )

    # ── 선수 삽입 ─────────────────────────────────────────────
    existing = cur.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    if existing == 0:
        for name, race, ctrl, atk, def_, sup, strat, sen in PLAYERS:
            ov = calc_overall(ctrl, atk, def_, sup, strat, sen)
            gr = calc_grade(ov)
            cur.execute(
                """INSERT INTO players
                   (name, race, control, attack, defense, supply, strategy, sense, overall, grade)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (name, race, ctrl, atk, def_, sup, strat, sen, ov, gr)
            )

    # ── 맵 삽입 (없는 맵만 추가) ──────────────────────────────
    existing_maps = {r[0] for r in cur.execute("SELECT name FROM maps").fetchall()}
    for name, tb, zb, pb in MAPS:
        if name not in existing_maps:
            cur.execute(
                "INSERT INTO maps (name, terran_bonus, zerg_bonus, protoss_bonus) VALUES (?,?,?,?)",
                (name, tb, zb, pb)
            )

    # ── 아이템 (항상 최신 목록으로 유지) ─────────────────────
    cur.execute("DELETE FROM items")
    for name, desc, price, itype, ctrl, atk, def_, sup, strat, sen, cond_up, fat_rec in ITEMS:
        cur.execute(
            """INSERT INTO items
               (name, description, price, item_type,
                control_bonus, attack_bonus, defense_bonus,
                supply_bonus, strategy_bonus, sense_bonus,
                condition_up, fatigue_recover)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name, desc, price, itype,
             ctrl, atk, def_, sup, strat, sen,
             cond_up, fat_rec)
        )

    # ── 라이벌 (항상 최신 목록으로 유지) ─────────────────────
    name_to_id = {r["name"]: r["id"]
                  for r in cur.execute("SELECT id, name FROM players").fetchall()}

    cur.execute("DELETE FROM rivals")
    for a_name, b_name, stat_bonus, extra_luck in RIVALS:
        a_id = name_to_id.get(a_name)
        b_id = name_to_id.get(b_name)
        if a_id is None or b_id is None:
            continue
        for x, y in [(a_id, b_id), (b_id, a_id)]:
            cur.execute(
                """INSERT OR IGNORE INTO rivals
                   (player_a_id, player_b_id, stat_bonus, extra_luck)
                   VALUES (?,?,?,?)""",
                (x, y, stat_bonus, extra_luck)
            )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed()
    print("시드 데이터 삽입 완료.")
