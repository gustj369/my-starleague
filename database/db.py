import sqlite3
import os
import sys
from pathlib import Path

# ── 슬롯 시스템 ───────────────────────────────────────────────
# EXE 환경: 세이브 파일을 AppData\Roaming\마이스타리그\saves\ 에 저장
# 개발 환경: 프로젝트 루트/saves/ 에 저장
if getattr(sys, 'frozen', False):
    _SAVES_DIR = Path(os.getenv('APPDATA', Path.home())) / '마이스타리그' / 'saves'
else:
    _SAVES_DIR = Path(__file__).parent.parent.parent / "saves"
_ACTIVE_SLOT: int = -1   # 선택된 슬롯 인덱스 (0~4)


def set_active_slot(slot_idx: int):
    global _ACTIVE_SLOT
    _ACTIVE_SLOT = slot_idx


def get_db_path() -> str:
    """현재 활성 슬롯의 DB 파일 경로 반환.

    BUG-12 수정: _ACTIVE_SLOT 기본값이 -1 이므로 set_active_slot() 호출 전에
    get_db_path() 가 실행되면 save_-1.db 가 생성되던 버그 → 가드 추가.
    """
    if _ACTIVE_SLOT < 0:
        raise RuntimeError(
            "슬롯이 선택되지 않았습니다. set_active_slot()을 먼저 호출하세요."
        )
    _SAVES_DIR.mkdir(parents=True, exist_ok=True)   # ← parents=True 필수 (첫 실행 시 부모 폴더 없음)
    return str(_SAVES_DIR / f"save_{_ACTIVE_SLOT}.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # QA-WAL 수정: WAL(Write-Ahead Log) 모드 활성화.
    # 기본 DELETE 모드에서는 finalize_match() 중 Alt+F4 강제 종료 시
    # 커밋 미완료 데이터(성장 델타 적용 but 골드 미지급 등)가 발생할 수 있음.
    # WAL 모드는 충돌 시 자동 롤백으로 DB 정합성을 보장함.
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            race        TEXT    NOT NULL CHECK(race IN ('테란','저그','프로토스')),
            control     INTEGER NOT NULL DEFAULT 50,
            attack      INTEGER NOT NULL DEFAULT 50,
            defense     INTEGER NOT NULL DEFAULT 50,
            supply      INTEGER NOT NULL DEFAULT 50,
            strategy    INTEGER NOT NULL DEFAULT 50,
            sense       INTEGER NOT NULL DEFAULT 50,
            overall     REAL    NOT NULL DEFAULT 50.0,
            grade       TEXT    NOT NULL DEFAULT 'C',
            condition   TEXT    NOT NULL DEFAULT '보통',
            fatigue     INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS maps (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            terran_bonus INTEGER NOT NULL DEFAULT 0,
            zerg_bonus   INTEGER NOT NULL DEFAULT 0,
            protoss_bonus INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS items (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL,
            description      TEXT    NOT NULL DEFAULT '',
            price            INTEGER NOT NULL DEFAULT 100,
            item_type        TEXT    NOT NULL DEFAULT '능력치',
            control_bonus    INTEGER NOT NULL DEFAULT 0,
            attack_bonus     INTEGER NOT NULL DEFAULT 0,
            defense_bonus    INTEGER NOT NULL DEFAULT 0,
            supply_bonus     INTEGER NOT NULL DEFAULT 0,
            strategy_bonus   INTEGER NOT NULL DEFAULT 0,
            sense_bonus      INTEGER NOT NULL DEFAULT 0,
            condition_up     INTEGER NOT NULL DEFAULT 0,
            fatigue_recover  INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS player_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id  INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
            item_id    INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS match_results (
            match_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            map_id         INTEGER NOT NULL REFERENCES maps(id),
            player_a_id    INTEGER NOT NULL REFERENCES players(id),
            player_b_id    INTEGER NOT NULL REFERENCES players(id),
            winner_id      INTEGER NOT NULL REFERENCES players(id),
            a_control_delta  INTEGER NOT NULL DEFAULT 0,
            a_attack_delta   INTEGER NOT NULL DEFAULT 0,
            a_defense_delta  INTEGER NOT NULL DEFAULT 0,
            a_supply_delta   INTEGER NOT NULL DEFAULT 0,
            a_strategy_delta INTEGER NOT NULL DEFAULT 0,
            a_sense_delta    INTEGER NOT NULL DEFAULT 0,
            b_control_delta  INTEGER NOT NULL DEFAULT 0,
            b_attack_delta   INTEGER NOT NULL DEFAULT 0,
            b_defense_delta  INTEGER NOT NULL DEFAULT 0,
            b_supply_delta   INTEGER NOT NULL DEFAULT 0,
            b_strategy_delta INTEGER NOT NULL DEFAULT 0,
            b_sense_delta    INTEGER NOT NULL DEFAULT 0,
            is_upset         INTEGER NOT NULL DEFAULT 0,
            timestamp        TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS rivals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            player_a_id  INTEGER NOT NULL REFERENCES players(id),
            player_b_id  INTEGER NOT NULL REFERENCES players(id),
            stat_bonus   INTEGER NOT NULL DEFAULT 0,
            extra_luck   INTEGER NOT NULL DEFAULT 0,
            UNIQUE(player_a_id, player_b_id)
        );

        CREATE TABLE IF NOT EXISTS game_state (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tournaments (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            my_player_id  INTEGER NOT NULL REFERENCES players(id),
            current_round TEXT    NOT NULL DEFAULT '16강',
            status        TEXT    NOT NULL DEFAULT '진행중',
            result        TEXT,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS tournament_matches (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            round         TEXT    NOT NULL,
            match_order   INTEGER NOT NULL,
            player_a_id   INTEGER REFERENCES players(id),
            player_b_id   INTEGER REFERENCES players(id),
            is_my_match   INTEGER NOT NULL DEFAULT 0,
            map_id        INTEGER REFERENCES maps(id),
            winner_id     INTEGER REFERENCES players(id),
            status        TEXT    NOT NULL DEFAULT 'pending',
            sets_to_win   INTEGER NOT NULL DEFAULT 2,
            a_wins        INTEGER NOT NULL DEFAULT 0,
            b_wins        INTEGER NOT NULL DEFAULT 0
        );
    """)

    # 초기 골드 세팅 (최초 1회)
    cur.execute(
        "INSERT OR IGNORE INTO game_state (key, value) VALUES ('gold', '500')"
    )

    conn.commit()
    conn.close()


def migrate_db():
    """기존 DB에 새 컬럼/테이블 추가 (ALTER TABLE ADD COLUMN)"""
    conn = get_connection()
    cur = conn.cursor()

    migrations = [
        # players 테이블
        "ALTER TABLE players ADD COLUMN condition TEXT NOT NULL DEFAULT '보통'",
        "ALTER TABLE players ADD COLUMN fatigue   INTEGER NOT NULL DEFAULT 0",
        # items 테이블
        "ALTER TABLE items ADD COLUMN item_type       TEXT    NOT NULL DEFAULT '능력치'",
        "ALTER TABLE items ADD COLUMN condition_up    INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE items ADD COLUMN fatigue_recover INTEGER NOT NULL DEFAULT 0",
        # match_results 테이블
        "ALTER TABLE match_results ADD COLUMN is_upset INTEGER NOT NULL DEFAULT 0",
        # tournament_matches 테이블 (다전제)
        "ALTER TABLE tournament_matches ADD COLUMN sets_to_win INTEGER NOT NULL DEFAULT 2",
        "ALTER TABLE tournament_matches ADD COLUMN a_wins     INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE tournament_matches ADD COLUMN b_wins     INTEGER NOT NULL DEFAULT 0",
    ]

    for sql in migrations:
        try:
            cur.execute(sql)
        except Exception:
            pass  # 이미 존재하는 컬럼이면 무시

    # rivals 테이블 (CREATE TABLE IF NOT EXISTS 로 처리)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rivals (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            player_a_id  INTEGER NOT NULL REFERENCES players(id),
            player_b_id  INTEGER NOT NULL REFERENCES players(id),
            stat_bonus   INTEGER NOT NULL DEFAULT 0,
            extra_luck   INTEGER NOT NULL DEFAULT 0,
            UNIQUE(player_a_id, player_b_id)
        )
    """)

    # SSS → Super 등급 이름 변경 마이그레이션 (기존 세이브 파일 호환)
    try:
        cur.execute("UPDATE players SET grade='Super' WHERE grade='SSS'")
    except Exception:
        pass

    conn.commit()
    conn.close()


def get_gold() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM game_state WHERE key='gold'").fetchone()
        return int(row["value"]) if row else 500


def set_gold(amount: int):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO game_state (key, value) VALUES ('gold', ?)",
            (str(amount),)
        )
        conn.commit()


def add_gold(amount: int):
    """BUG-14 수정: get_gold() + set_gold() 분리 시 두 트랜잭션 사이에 다른 호출이
    끼어들 수 있는 비원자적 read-modify-write 문제 → 단일 SQL UPDATE 로 원자화.
    """
    with get_connection() as conn:
        conn.execute(
            "UPDATE game_state SET value = CAST(value AS INTEGER) + ? WHERE key='gold'",
            (amount,)
        )
        conn.commit()


def get_current_tournament_id() -> int | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM game_state WHERE key='current_tournament_id'"
        ).fetchone()
        return int(row["value"]) if row else None


def set_current_tournament_id(tid: int | None):
    with get_connection() as conn:
        if tid is None:
            conn.execute("DELETE FROM game_state WHERE key='current_tournament_id'")
        else:
            conn.execute(
                "INSERT OR REPLACE INTO game_state (key, value) VALUES ('current_tournament_id', ?)",
                (str(tid),)
            )
        conn.commit()


# 업적 우선순위 (높을수록 좋은 성적)
_ACHIEVEMENT_RANK: dict[str, int] = {
    "우승":      5,
    "준우승":    4,
    "4강 탈락":  3,
    "8강 탈락":  2,
    "16강 탈락": 1,
}


def get_game_summary() -> dict:
    """골드·누적 토너먼트 수·마지막 업적·최고 업적 반환"""
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM game_state").fetchall()
    data = {r["key"]: r["value"] for r in rows}
    return {
        "gold": int(data.get("gold", 500)),
        "total_tournaments": int(data.get("total_tournaments_played", 0)),
        "last_achievement": data.get("last_achievement", ""),
        "best_achievement": data.get("best_achievement", ""),
    }


def save_tournament_result(achievement: str, gold_earned: int):
    """토너먼트 종료 시 업적·플레이 횟수·최고 업적 저장. current_tournament_id는 유지."""
    with get_connection() as conn:
        cur_count_row = conn.execute(
            "SELECT value FROM game_state WHERE key='total_tournaments_played'"
        ).fetchone()
        cur_count = int(cur_count_row["value"]) if cur_count_row else 0

        conn.execute(
            "INSERT OR REPLACE INTO game_state (key, value) VALUES ('last_achievement', ?)",
            (achievement,)
        )
        conn.execute(
            "INSERT OR REPLACE INTO game_state (key, value) VALUES ('total_tournaments_played', ?)",
            (str(cur_count + 1),)
        )

        # 최고 업적 갱신 (더 좋은 성적이면 교체)
        best_row = conn.execute(
            "SELECT value FROM game_state WHERE key='best_achievement'"
        ).fetchone()
        best = best_row["value"] if best_row else ""
        if _ACHIEVEMENT_RANK.get(achievement, 0) >= _ACHIEVEMENT_RANK.get(best, 0):
            conn.execute(
                "INSERT OR REPLACE INTO game_state (key, value) VALUES ('best_achievement', ?)",
                (achievement,)
            )

        conn.commit()
