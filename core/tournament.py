"""토너먼트 대진표 생성 및 진행 로직"""
import random
from database.db import get_connection, add_gold, set_current_tournament_id
from core.match import simulate_series, SETS_TO_WIN
from core.balance import roll_condition, add_fatigue

ROUNDS = ['16강', '8강', '4강', '결승']

# 라운드 통과 골드 보상 (다음 라운드 진입 시 지급)
ROUND_REWARDS = {
    '16강': 100,   # 16강 통과 시
    '8강':  150,
    '4강':  200,
    '결승': 500,   # 우승 시
}


# ─────────────────────────────────────────────────
# 생성
# ─────────────────────────────────────────────────

def create_tournament(my_player_id: int) -> int:
    """16강 대진 생성 후 tournament_id 반환"""
    with get_connection() as conn:
        rows = conn.execute("SELECT id FROM players").fetchall()
        all_ids = [r[0] for r in rows]

    if len(all_ids) < 16:
        raise ValueError(f"선수가 16명이어야 합니다. 현재 {len(all_ids)}명")

    # 16명 셔플 후 my_player가 반드시 포함
    pool = [i for i in all_ids if i != my_player_id]
    random.shuffle(pool)
    player_ids = [my_player_id] + pool[:15]
    random.shuffle(player_ids)

    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO tournaments (my_player_id) VALUES (?)",
            (my_player_id,)
        )
        tid = cur.lastrowid

        stw = SETS_TO_WIN.get('16강', 2)
        for i in range(8):
            a_id = player_ids[i * 2]
            b_id = player_ids[i * 2 + 1]
            is_my = 1 if (a_id == my_player_id or b_id == my_player_id) else 0
            conn.execute(
                """INSERT INTO tournament_matches
                   (tournament_id, round, match_order, player_a_id, player_b_id,
                    is_my_match, sets_to_win)
                   VALUES (?,?,?,?,?,?,?)""",
                (tid, '16강', i + 1, a_id, b_id, is_my, stw)
            )
        conn.commit()

    set_current_tournament_id(tid)
    return tid


# ─────────────────────────────────────────────────
# 조회
# ─────────────────────────────────────────────────

def get_tournament(tid: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tournaments WHERE id=?", (tid,)).fetchone()
        return dict(row) if row else None


def get_round_matches(tid: int, round_name: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT tm.*,
               pa.name  AS a_name,  pa.race AS a_race,  pa.grade AS a_grade,
               pb.name  AS b_name,  pb.race AS b_race,  pb.grade AS b_grade,
               pw.name  AS w_name
               FROM tournament_matches tm
               LEFT JOIN players pa ON pa.id = tm.player_a_id
               LEFT JOIN players pb ON pb.id = tm.player_b_id
               LEFT JOIN players pw ON pw.id = tm.winner_id
               WHERE tm.tournament_id=? AND tm.round=?
               ORDER BY tm.match_order""",
            (tid, round_name)
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_matches(tid: int) -> dict[str, list[dict]]:
    """라운드별 경기 딕셔너리 반환 (존재하는 라운드만)"""
    result = {}
    for r in ROUNDS:
        ms = get_round_matches(tid, r)
        if ms:
            result[r] = ms
    return result


def get_my_pending_match(tid: int) -> dict | None:
    """현재 라운드에서 내 선수의 미완료 경기"""
    t = get_tournament(tid)
    if not t or t['status'] != '진행중':
        return None
    for m in get_round_matches(tid, t['current_round']):
        if m['is_my_match'] and m['status'] == 'pending':
            return m
    return None


# ─────────────────────────────────────────────────
# 경기 진행
# ─────────────────────────────────────────────────

def simulate_ai_matches(tid: int):
    """현재 라운드 AI 경기 자동 시뮬레이션"""
    t = get_tournament(tid)
    if not t:
        return

    with get_connection() as conn:
        map_ids = [r[0] for r in conn.execute("SELECT id FROM maps").fetchall()]

    round_name = t['current_round']
    for m in get_round_matches(tid, round_name):
        if m['status'] == 'pending' and not m['is_my_match']:
            map_id = random.choice(map_ids)

            # AI 선수 컨디션 롤
            with get_connection() as conn:
                pa_row = conn.execute("SELECT grade FROM players WHERE id=?",
                                      (m['player_a_id'],)).fetchone()
                pb_row = conn.execute("SELECT grade FROM players WHERE id=?",
                                      (m['player_b_id'],)).fetchone()
            cond_a = roll_condition(pa_row["grade"]) if pa_row else "보통"
            cond_b = roll_condition(pb_row["grade"]) if pb_row else "보통"

            # 다전제 시뮬레이션
            outcome = simulate_series(
                m['player_a_id'], m['player_b_id'], map_id,
                round_name=round_name,
                a_condition=cond_a,
                b_condition=cond_b,
                award_gold=False,
            )
            _complete_tm(m['id'], outcome.winner_id, map_id,
                         outcome.a_wins, outcome.b_wins)

            # AI 선수 피로도 누적
            add_fatigue(m['player_a_id'], round_name)
            add_fatigue(m['player_b_id'], round_name)


def complete_my_match(tm_id: int, winner_id: int, map_id: int,
                      round_name: str = "", my_player_id: int = 0,
                      a_wins: int = 0, b_wins: int = 0):
    """내 선수 경기 완료 처리 + 피로도 누적"""
    _complete_tm(tm_id, winner_id, map_id, a_wins, b_wins)
    if round_name and my_player_id:
        add_fatigue(my_player_id, round_name)


def _complete_tm(tm_id: int, winner_id: int, map_id: int,
                 a_wins: int = 0, b_wins: int = 0):
    with get_connection() as conn:
        conn.execute(
            """UPDATE tournament_matches
               SET winner_id=?, map_id=?, status='completed',
                   a_wins=?, b_wins=?
               WHERE id=?""",
            (winner_id, map_id, a_wins, b_wins, tm_id)
        )
        conn.commit()


# ─────────────────────────────────────────────────
# 라운드 진행
# ─────────────────────────────────────────────────

def is_round_complete(tid: int) -> bool:
    t = get_tournament(tid)
    if not t:
        return False
    return all(m['status'] == 'completed' for m in get_round_matches(tid, t['current_round']))


def advance_round(tid: int) -> str | None:
    """다음 라운드 매치 생성. 반환: 새 라운드명 또는 None(토너먼트 종료)"""
    t = get_tournament(tid)
    if not t:
        return None

    current = t['current_round']
    cur_idx = ROUNDS.index(current)
    my_id = t['my_player_id']

    # 결승이 끝났으면 토너먼트 종료
    if current == '결승':
        _finish_tournament(tid)
        return None

    next_round = ROUNDS[cur_idx + 1]
    winners = _get_ordered_winners(tid, current)

    stw = SETS_TO_WIN.get(next_round, 2)
    with get_connection() as conn:
        for i in range(0, len(winners), 2):
            a_id = winners[i]
            b_id = winners[i + 1]
            order = i // 2 + 1
            is_my = 1 if (a_id == my_id or b_id == my_id) else 0
            conn.execute(
                """INSERT INTO tournament_matches
                   (tournament_id, round, match_order, player_a_id, player_b_id,
                    is_my_match, sets_to_win)
                   VALUES (?,?,?,?,?,?,?)""",
                (tid, next_round, order, a_id, b_id, is_my, stw)
            )
        conn.execute(
            "UPDATE tournaments SET current_round=? WHERE id=?",
            (next_round, tid)
        )
        conn.commit()

    # 이전 라운드 통과 보상 (my player가 살아있을 때)
    if is_my_player_alive(tid):
        add_gold(ROUND_REWARDS.get(current, 0))

    return next_round


def _get_ordered_winners(tid: int, round_name: str) -> list[int]:
    return [
        m['winner_id']
        for m in sorted(get_round_matches(tid, round_name), key=lambda x: x['match_order'])
    ]


def _finish_tournament(tid: int):
    t = get_tournament(tid)
    if not t:
        return
    final = get_round_matches(tid, '결승')
    if not final:
        return

    my_id = t['my_player_id']
    champion_id = final[0].get('winner_id')

    if champion_id == my_id:
        result = '우승'
        add_gold(ROUND_REWARDS['결승'])
    else:
        result = '준우승'

    with get_connection() as conn:
        conn.execute(
            "UPDATE tournaments SET status='완료', result=? WHERE id=?",
            (result, tid)
        )
        conn.commit()


# ─────────────────────────────────────────────────
# 상태 조회
# ─────────────────────────────────────────────────

def is_my_player_alive(tid: int) -> bool:
    t = get_tournament(tid)
    if not t:
        return False
    my_id = t['my_player_id']
    cur_idx = ROUNDS.index(t['current_round'])

    for rnd in ROUNDS[:cur_idx + 1]:
        for m in get_round_matches(tid, rnd):
            if m['status'] == 'completed':
                if m['player_a_id'] == my_id or m['player_b_id'] == my_id:
                    if m['winner_id'] != my_id:
                        return False
    return True


def get_elimination_round(tid: int) -> str:
    """내 선수가 탈락한 라운드 반환 (탈락 안 했으면 '진행중' 또는 '우승')"""
    t = get_tournament(tid)
    if not t:
        return '알 수 없음'
    if t.get('result'):
        return t['result']

    my_id = t['my_player_id']
    for rnd in ROUNDS:
        for m in get_round_matches(tid, rnd):
            if m['status'] == 'completed':
                if m['player_a_id'] == my_id or m['player_b_id'] == my_id:
                    if m['winner_id'] != my_id:
                        return f'{rnd} 탈락'
    return '진행중'
