"""Shared Streamlit-facing pipeline helpers: DB connection, fetch-or-load,
per-game averages, and player headshots. Extracted from app.py once the
comparison page (1.7) needed the exact same lookup logic as the profile
page (1.6).
"""

import sqlite3

import pandas as pd
import streamlit as st

from src.clean import clean_career_stats, clean_player_bio
from src.database import init_db, insert_career_stats, insert_player_bio
from src.fetch import fetch_player_career_stats, fetch_player_info, get_player_id

HEADSHOT_URL = "https://cdn.nba.com/headshots/nba/latest/1040x760/{person_id}.png"


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    return init_db()


@st.cache_data(show_spinner="Loading player data...")
def get_or_build_player(_conn: sqlite3.Connection, name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (bio_df, stats_df) for a player, reading from the DB if cached there,
    otherwise running the fetch -> clean -> insert pipeline first."""
    player_id = get_player_id(name)

    bio_df = pd.read_sql(
        "SELECT * FROM players WHERE PERSON_ID = ?", _conn, params=(player_id,)
    )
    if bio_df.empty:
        bio_df = clean_player_bio(fetch_player_info(player_id))
        stats_df = clean_career_stats(fetch_player_career_stats(player_id))
        insert_player_bio(_conn, bio_df)
        insert_career_stats(_conn, stats_df)
    else:
        stats_df = pd.read_sql(
            "SELECT * FROM career_stats WHERE PLAYER_ID = ? ORDER BY SEASON_ID",
            _conn,
            params=(player_id,),
        )

    return bio_df, stats_df


def with_per_game_averages(stats_df: pd.DataFrame) -> pd.DataFrame:
    """Add PPG/RPG/APG columns computed from season totals (display-time only)."""
    df = stats_df.copy()
    df["PPG"] = (df["PTS"] / df["GP"]).round(1)
    df["RPG"] = (df["REB"] / df["GP"]).round(1)
    df["APG"] = (df["AST"] / df["GP"]).round(1)
    return df


def format_height(height_inches) -> str:
    """Format a HEIGHT value for display; some players have no height on record."""
    if height_inches is None or pd.isna(height_inches):
        return "Unknown"
    return f"{int(height_inches)} in"


def get_headshot_url(person_id: int) -> str:
    """Build the NBA CDN headshot URL for a player.

    Unofficial: not part of nba_api's documented endpoints, just a known,
    stable CDN pattern. This is a browser-side st.image load, not something
    fetch.py's retry/cache logic touches -- if NBA ever changes the URL
    scheme, only the display breaks, not the data pipeline.
    """
    return HEADSHOT_URL.format(person_id=person_id)
