"""Shared Streamlit-facing pipeline helpers: DB connection, fetch-or-load,
per-game averages, player headshots, and typo-tolerant player search.
Extracted from app.py once the comparison page (1.7) needed the exact same
lookup logic as the profile page (1.6).
"""

import difflib
import sqlite3

import pandas as pd
import streamlit as st
from nba_api.stats.static import players as static_players

from src.clean import clean_career_stats, clean_player_bio
from src.database import init_db, insert_career_stats, insert_player_bio
from src.fetch import fetch_player_career_stats, fetch_player_info

HEADSHOT_URL = "https://cdn.nba.com/headshots/nba/latest/1040x760/{person_id}.png"

# Loaded once at import time: nba_api's static list is offline/bundled data,
# not a network call, so this is cheap and safe to hold in memory.
_ALL_PLAYERS = static_players.get_players()


def search_players(term: str, limit: int = 8) -> list[tuple[str, int]]:
    """Search all NBA players (active + historical) by name, typo-tolerant.

    Two-tier strategy: substring match first (fast, and correctly ranks
    "LeBron James" first for "leb" -- see PROGRESS.md for why plain fuzzy
    matching alone gets this wrong for short, correctly-typed prefixes).
    Only falls back to fuzzy matching (difflib) when no substring match
    exists at all, which is what actually catches typos like "micheal
    jordn". Returns (display_name, person_id) pairs so a selection in
    st_searchbox resolves directly to an ID, no second lookup needed.
    """
    if not term:
        return []

    term_lower = term.lower()
    substring_matches = [p for p in _ALL_PLAYERS if term_lower in p["full_name"].lower()]
    if substring_matches:
        substring_matches.sort(
            key=lambda p: (not p["full_name"].lower().startswith(term_lower), len(p["full_name"]))
        )
        return [(p["full_name"], p["id"]) for p in substring_matches[:limit]]

    scored = []
    for p in _ALL_PLAYERS:
        name_lower = p["full_name"].lower()
        tokens = name_lower.split()
        best_ratio = max(
            difflib.SequenceMatcher(None, term_lower, name_lower).ratio(),
            max((difflib.SequenceMatcher(None, term_lower, t).ratio() for t in tokens), default=0),
        )
        if best_ratio > 0.6:
            scored.append((best_ratio, p))
    scored.sort(key=lambda x: -x[0])
    return [(p["full_name"], p["id"]) for _, p in scored[:limit]]


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    return init_db()


@st.cache_data(show_spinner="Loading player data...")
def get_or_build_player(_conn: sqlite3.Connection, person_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (bio_df, stats_df) for a player, reading from the DB if cached there,
    otherwise running the fetch -> clean -> insert pipeline first."""
    bio_df = pd.read_sql(
        "SELECT * FROM players WHERE PERSON_ID = ?", _conn, params=(person_id,)
    )
    if bio_df.empty:
        bio_df = clean_player_bio(fetch_player_info(person_id))
        stats_df = clean_career_stats(fetch_player_career_stats(person_id))
        insert_player_bio(_conn, bio_df)
        insert_career_stats(_conn, stats_df)
    else:
        stats_df = pd.read_sql(
            "SELECT * FROM career_stats WHERE PLAYER_ID = ? ORDER BY SEASON_ID",
            _conn,
            params=(person_id,),
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
