"""HoopAnalytics — Streamlit app entry point. V1: player profile page."""

import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

from src.clean import clean_career_stats, clean_player_bio
from src.database import init_db, insert_career_stats, insert_player_bio
from src.fetch import fetch_player_career_stats, fetch_player_info, get_player_id

st.set_page_config(page_title="HoopAnalytics", page_icon="🏀")


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


st.title("🏀 HoopAnalytics")
st.caption("Player profile — search any NBA player by name.")

conn = get_connection()
player_name = st.text_input("Player name", value="LeBron James")

if player_name:
    try:
        bio_df, stats_df = get_or_build_player(conn, player_name)
    except ValueError as exc:
        st.error(str(exc))
    else:
        bio = bio_df.iloc[0]

        st.header(bio["DISPLAY_FIRST_LAST"])
        cols = st.columns(4)
        cols[0].metric("Team", bio["TEAM_NAME"])
        cols[1].metric("Position", bio["POSITION"])
        cols[2].metric("Height", f'{bio["HEIGHT"]} in')
        cols[3].metric("Weight", f'{bio["WEIGHT"]} lb')

        cols = st.columns(4)
        cols[0].metric("Country", bio["COUNTRY"])
        cols[1].metric("Experience", f'{bio["SEASON_EXP"]} yrs')
        cols[2].metric("Draft", f'{bio["DRAFT_YEAR"]} R{bio["DRAFT_ROUND"]} #{bio["DRAFT_NUMBER"]}')
        cols[3].metric("Jersey", f'#{bio["JERSEY"]}')

        display_stats = with_per_game_averages(stats_df)

        st.subheader("Season-by-season stats")
        st.dataframe(
            display_stats[
                ["SEASON_ID", "TEAM_ABBREVIATION", "GP", "PPG", "RPG", "APG", "FG_PCT", "FG3_PCT", "FT_PCT"]
            ],
            hide_index=True,
        )

        st.subheader("Points per game over career")
        fig = px.line(display_stats, x="SEASON_ID", y="PPG", markers=True)
        fig.update_layout(xaxis_title="Season", yaxis_title="Points per game")
        st.plotly_chart(fig, width="stretch")
