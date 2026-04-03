import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "my_starleague.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
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
    set_gold(get_gold() + amount)


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
