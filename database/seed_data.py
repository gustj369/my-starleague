from database.db import get_connection, init_db
from core.grade import calc_overall, calc_grade


PLAYERS = [
    # (name, race, control, attack, defense, supply, strategy, sense)
    # ── 테란 6명 ──────────────────────────────────────────────
    ("이영호", "테란",   98, 95, 90, 88, 92, 95),   # SSS 93.0
    ("최연성", "테란",   88, 86, 91, 85, 90, 87),   # S   87.8
    ("박성균", "테란",   85, 88, 82, 80, 84, 83),   # A   83.7
    ("이신형", "테란",   83, 84, 80, 79, 82, 81),   # A   81.5
    ("윤용태", "테란",   80, 82, 78, 76, 80, 79),   # B   79.2
    ("김구현", "테란",   77, 78, 75, 74, 76, 77),   # B   76.2
    # ── 저그 5명 ──────────────────────────────────────────────
    ("이제동", "저그",   96, 98, 85, 95, 90, 94),   # SSS 93.0
    ("김명운", "저그",   82, 85, 80, 88, 83, 84),   # A   83.7
    ("박성준", "저그",   79, 81, 77, 83, 79, 80),   # B   79.8
    ("이영한", "저그",   76, 78, 75, 81, 77, 76),   # B   77.2
    ("김정우", "저그",   74, 75, 72, 78, 74, 73),   # B   74.3
    # ── 프로토스 5명 ──────────────────────────────────────────
    ("김택용", "프로토스", 94, 90, 88, 86, 95, 92), # SS  90.8
    ("송병구", "프로토스", 88, 86, 90, 84, 88, 87), # S   87.2
    ("허영무", "프로토스", 85, 83, 87, 82, 86, 84), # A   84.5
    ("장윤철", "프로토스", 81, 83, 85, 81, 84, 82), # A   82.7
    ("도재욱", "프로토스", 77, 79, 81, 78, 80, 78), # B   78.8
]

MAPS = [
    # (name, terran_bonus, zerg_bonus, protoss_bonus)
    ("블리츠",        +5, -3, +2),
    ("파이썬",        -2, +6, +1),
    ("네오 포비든존",  +3, +2, -2),
    ("아즈텍",        +1, -4, +7),
    ("로스트 템플",    0,  +4, +3),
]

# PRD v4 아이템
# (name, description, price, item_type, ctrl, atk, def_, sup, strat, sen, condition_up, fatigue_recover)
ITEMS = [
    ("컨트롤 강화제",  "컨트롤 +5",           150, "능력치",   5, 0, 0, 0, 0, 0, 0,  0),
    ("전략 매뉴얼",    "전략 +5",             150, "능력치",   0, 0, 0, 0, 5, 0, 0,  0),
    ("물량 부스터",    "물량 +5",             150, "능력치",   0, 0, 0, 5, 0, 0, 0,  0),
    ("올스탯 강화제",  "전 능력치 +2",         350, "능력치",   2, 2, 2, 2, 2, 2, 0,  0),
    ("에너지 드링크",  "컨디션 한 단계 상승",   200, "컨디션",   0, 0, 0, 0, 0, 0, 1,  0),
    ("휴식 아이템",    "피로도 -30",           180, "피로회복", 0, 0, 0, 0, 0, 0, 0, 30),
]

# 라이벌 관계 (PRD v4): (선수A, 선수B, stat_bonus, extra_luck)
RIVALS = [
    ("이영호", "이제동", 8, 5),   # 양쪽 전 능력치 +8, 이변 범위 추가 ±5
    ("이영호", "김택용", 5, 0),   # 양쪽 전 능력치 +5
    ("이제동", "송병구", 5, 0),   # 양쪽 전 능력치 +5
]

# PRD v4 능력치 조정 대상 (이름 → 새 수치)
STAT_UPDATES = {
    "김구현": (77, 78, 75, 74, 76, 77),
    "박성준": (79, 81, 77, 83, 79, 80),
    "이영한": (76, 78, 75, 81, 77, 76),
    "김정우": (74, 75, 72, 78, 74, 73),
    "장윤철": (81, 83, 85, 81, 84, 82),
    "도재욱": (77, 79, 81, 78, 80, 78),
}


def seed():
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    # ── 강태민 → 김정우 이름 변경 ────────────────────────────
    cur.execute("UPDATE players SET name='김정우' WHERE name='강태민'")

    # ── 선수 ──────────────────────────────────────────────────
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
    elif existing < 16:
        existing_names = {r[0] for r in cur.execute("SELECT name FROM players").fetchall()}
        for name, race, ctrl, atk, def_, sup, strat, sen in PLAYERS:
            if name not in existing_names:
                ov = calc_overall(ctrl, atk, def_, sup, strat, sen)
                gr = calc_grade(ov)
                cur.execute(
                    """INSERT INTO players
                       (name, race, control, attack, defense, supply, strategy, sense, overall, grade)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (name, race, ctrl, atk, def_, sup, strat, sen, ov, gr)
                )

    # ── 능력치 조정 (PRD v4 밸런스) ──────────────────────────
    for name, (ctrl, atk, def_, sup, strat, sen) in STAT_UPDATES.items():
        ov = calc_overall(ctrl, atk, def_, sup, strat, sen)
        gr = calc_grade(ov)
        cur.execute(
            """UPDATE players SET
               control=?, attack=?, defense=?, supply=?, strategy=?, sense=?,
               overall=?, grade=?
               WHERE name=?""",
            (ctrl, atk, def_, sup, strat, sen, ov, gr, name)
        )

    # ── 맵 ────────────────────────────────────────────────────
    if cur.execute("SELECT COUNT(*) FROM maps").fetchone()[0] == 0:
        for name, tb, zb, pb in MAPS:
            cur.execute(
                "INSERT INTO maps (name, terran_bonus, zerg_bonus, protoss_bonus) VALUES (?,?,?,?)",
                (name, tb, zb, pb)
            )

    # ── 아이템 (PRD v4: 초기화 후 재삽입) ─────────────────────
    cur.execute("DELETE FROM items")
    cur.execute("DELETE FROM player_items")
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

    # ── 라이벌 (PRD v4: 초기화 후 재삽입) ────────────────────
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
