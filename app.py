"""HoopAnalytics — Streamlit app entry point. V1: player profile page."""

import plotly.express as px
import streamlit as st
from streamlit_searchbox import st_searchbox

from src.pipeline import format_height, get_connection, get_headshot_url, get_or_build_player, search_players, with_per_game_averages

LEBRON_JAMES_ID = 2544

st.set_page_config(page_title="HoopAnalytics", page_icon="🏀")

st.title("🏀 HoopAnalytics")
st.caption("Player profile — search any NBA player by name.")

conn = get_connection()
person_id = st_searchbox(
    search_players,
    label="Player name",
    placeholder="Search for a player...",
    default=LEBRON_JAMES_ID,
    default_searchterm="LeBron James",
    key="profile_search",
)

if person_id:
    bio_df, stats_df = get_or_build_player(conn, person_id)
    bio = bio_df.iloc[0]

    photo_col, header_col = st.columns([1, 3])
    photo_col.image(get_headshot_url(bio["PERSON_ID"]), width=150)
    header_col.header(bio["DISPLAY_FIRST_LAST"])

    cols = st.columns(4)
    cols[0].metric("Team", bio["TEAM_NAME"])
    cols[1].metric("Position", bio["POSITION"])
    cols[2].metric("Height", format_height(bio["HEIGHT"]))
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
    # Force categorical: Plotly auto-detects "2001-02"-style strings as
    # dates, silently dropping any season whose second half isn't 01-12.
    fig.update_xaxes(type="category")
    fig.update_layout(xaxis_title="Season", yaxis_title="Points per game")
    st.plotly_chart(fig, width="stretch")
