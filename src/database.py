"""SQLite schema and insertion for cleaned NBA data (from clean.py).

Two tables:
  - players: one row per player (bio data).
  - career_stats: one row per player-season (PLAYER_ID, SEASON_ID) as the
    composite primary key, with PLAYER_ID as a foreign key into players.

Inserts use INSERT OR REPLACE so re-running the pipeline for a player
updates their existing rows instead of duplicating or erroring.
"""

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "hoopanalytics.db"

CREATE_PLAYERS_TABLE = """
CREATE TABLE IF NOT EXISTS players (
    PERSON_ID INTEGER PRIMARY KEY,
    DISPLAY_FIRST_LAST TEXT NOT NULL,
    TEAM_NAME TEXT,
    POSITION TEXT,
    HEIGHT INTEGER,
    WEIGHT INTEGER,
    BIRTHDATE TEXT,
    COUNTRY TEXT,
    SEASON_EXP INTEGER,
    JERSEY TEXT,
    DRAFT_YEAR TEXT,
    DRAFT_ROUND TEXT,
    DRAFT_NUMBER TEXT
)
"""

CREATE_CAREER_STATS_TABLE = """
CREATE TABLE IF NOT EXISTS career_stats (
    PLAYER_ID INTEGER NOT NULL,
    SEASON_ID TEXT NOT NULL,
    TEAM_ABBREVIATION TEXT,
    PLAYER_AGE REAL,
    GP INTEGER,
    GS INTEGER,
    MIN INTEGER,
    PTS INTEGER,
    REB INTEGER,
    AST INTEGER,
    STL INTEGER,
    BLK INTEGER,
    TOV INTEGER,
    FG_PCT REAL,
    FG3_PCT REAL,
    FT_PCT REAL,
    PRIMARY KEY (PLAYER_ID, SEASON_ID),
    FOREIGN KEY (PLAYER_ID) REFERENCES players (PERSON_ID)
)
"""


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create the players/career_stats tables if they don't exist and return a connection.

    check_same_thread=False: the connection is meant to be created once and reused
    across calls (e.g. cached as a Streamlit resource), and Streamlit runs script
    reruns on a thread pool rather than one fixed thread. Safe here because the app
    only ever runs one query/insert at a time against this connection, never
    concurrent writes from multiple threads at once.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute(CREATE_PLAYERS_TABLE)
    conn.execute(CREATE_CAREER_STATS_TABLE)
    conn.commit()
    return conn


def _row_for_sqlite(row: tuple) -> tuple:
    """Convert values sqlite3 can't bind directly (e.g. pandas Timestamp) to strings."""
    return tuple(v.isoformat() if isinstance(v, pd.Timestamp) else v for v in row)


def insert_player_bio(conn: sqlite3.Connection, bio_df: pd.DataFrame) -> None:
    """Insert (or replace) a player's bio row from clean_player_bio()'s output."""
    columns = list(bio_df.columns)
    placeholders = ", ".join(["?"] * len(columns))
    query = f"INSERT OR REPLACE INTO players ({', '.join(columns)}) VALUES ({placeholders})"

    rows = [_row_for_sqlite(tuple(row)) for row in bio_df.itertuples(index=False)]
    conn.executemany(query, rows)
    conn.commit()


def insert_career_stats(conn: sqlite3.Connection, stats_df: pd.DataFrame) -> None:
    """Insert (or replace) a player's season-by-season rows from clean_career_stats()'s output."""
    columns = list(stats_df.columns)
    placeholders = ", ".join(["?"] * len(columns))
    query = f"INSERT OR REPLACE INTO career_stats ({', '.join(columns)}) VALUES ({placeholders})"

    rows = [tuple(row) for row in stats_df.itertuples(index=False)]
    conn.executemany(query, rows)
    conn.commit()


if __name__ == "__main__":
    from src.clean import clean_career_stats, clean_player_bio
    from src.fetch import fetch_player_career_stats, fetch_player_info, get_player_id

    lebron_id = get_player_id("LeBron James")
    bio_df = clean_player_bio(fetch_player_info(lebron_id))
    stats_df = clean_career_stats(fetch_player_career_stats(lebron_id))

    connection = init_db()
    insert_player_bio(connection, bio_df)
    insert_career_stats(connection, stats_df)

    print(pd.read_sql("SELECT * FROM players", connection).to_string(index=False))
    print()
    print(pd.read_sql("SELECT COUNT(*) AS season_rows FROM career_stats", connection).to_string(index=False))
    connection.close()
