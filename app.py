"""HoopAnalytics — Streamlit app entry point. V1: player profile page."""

import plotly.express as px
import streamlit as st

from src.pipeline import get_connection, get_headshot_url, get_or_build_player, with_per_game_averages

st.set_page_config(page_title="HoopAnalytics", page_icon="🏀")

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

        photo_col, header_col = st.columns([1, 3])
        photo_col.image(get_headshot_url(bio["PERSON_ID"]), width=150)
        header_col.header(bio["DISPLAY_FIRST_LAST"])

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
