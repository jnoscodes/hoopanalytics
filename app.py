"""HoopAnalytics — Streamlit app entry point. V1: player profile page."""

import plotly.express as px
import streamlit as st

from src.pipeline import format_draft, format_height, get_connection, get_headshot_url, get_or_build_player, with_per_game_averages
from src.ui import bound_to_data, player_search

LEBRON_JAMES_ID = 2544

st.set_page_config(page_title="HoopAnalytics", page_icon="🏀")

st.title("🏀 HoopAnalytics")
st.caption("Player profile — search any NBA player by name.")

conn = get_connection()
person_id = player_search(conn, key="profile_search", label="Player name", default_id=LEBRON_JAMES_ID)

if person_id:
    bio_df, stats_df = get_or_build_player(conn, person_id)
    bio = bio_df.iloc[0]

    photo_col, header_col = st.columns([1, 3])
    photo_col.image(get_headshot_url(bio["PERSON_ID"]), width=150)
    header_col.header(bio["DISPLAY_FIRST_LAST"])
    # Free-text fields go in a wrapping caption, not st.metric tiles: metric
    # values are 36px and cut off with "..." past ~160px (4-column layout),
    # which "Timberwolves", "Guard-Forward" or a full draft line all exceed.
    # Blank fields (e.g. no current team) are skipped rather than shown empty.
    details = [bio["TEAM_NAME"], bio["POSITION"], bio["COUNTRY"]]
    header_col.caption(" · ".join(d for d in details if d))
    header_col.caption(format_draft(bio))

    cols = st.columns(4)
    cols[0].metric("Height", format_height(bio["HEIGHT"]))
    cols[1].metric("Weight", f'{bio["WEIGHT"]} lb')
    cols[2].metric("Experience", f'{bio["SEASON_EXP"]} yrs')
    cols[3].metric("Jersey", f'#{bio["JERSEY"]}')

    display_stats = with_per_game_averages(stats_df)

    st.subheader("Season-by-season stats")
    st.dataframe(
        display_stats[
            ["SEASON_ID", "TEAM_ABBREVIATION", "GP", "PPG", "RPG", "APG", "FG_PCT", "FG3_PCT", "FT_PCT"]
        ],
        hide_index=True,
        # Display labels only; the underlying columns keep their API/DB names.
        column_config={
            "SEASON_ID": "Season",
            "TEAM_ABBREVIATION": "Team",
            "GP": "Games",
            "FG_PCT": st.column_config.NumberColumn("FG%", format="percent"),
            "FG3_PCT": st.column_config.NumberColumn("3P%", format="percent"),
            "FT_PCT": st.column_config.NumberColumn("FT%", format="percent"),
        },
    )

    st.subheader("Points per game over career")
    fig = px.line(display_stats, x="SEASON_ID", y="PPG", markers=True)
    # Force categorical: Plotly auto-detects "2001-02"-style strings as
    # dates, silently dropping any season whose second half isn't 01-12.
    fig.update_xaxes(type="category")
    bound_to_data(fig, n_categories=len(display_stats), y_max=display_stats["PPG"].max())
    fig.update_layout(xaxis_title="Season", yaxis_title="Points per game")
    st.plotly_chart(fig, width="stretch")
