"""Streamlit page: compare two players, each on an independently selected season."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.pipeline import format_height, get_connection, get_headshot_url, get_or_build_player, with_per_game_averages

st.set_page_config(page_title="HoopAnalytics — Comparison", page_icon="🆚")

st.title("🆚 Player Comparison")
st.caption("Compare two players, each on their own selected season.")

conn = get_connection()


def render_player_column(column, label: str, default_name: str, key_prefix: str):
    """Render one player's inputs/bio/season picker; return (display_name, season_row, full_stats) or None."""
    with column:
        name = st.text_input(f"Player {label}", value=default_name, key=f"{key_prefix}_name")
        if not name:
            return None

        try:
            bio_df, stats_df = get_or_build_player(conn, name)
        except ValueError as exc:
            st.error(str(exc))
            return None

        bio = bio_df.iloc[0]
        stats_df = with_per_game_averages(stats_df).sort_values("SEASON_ID").reset_index(drop=True)

        st.image(get_headshot_url(bio["PERSON_ID"]), width=150)
        st.subheader(bio["DISPLAY_FIRST_LAST"])
        st.caption(f'{bio["TEAM_NAME"]} · {bio["POSITION"]} · {format_height(bio["HEIGHT"])} · {bio["WEIGHT"]} lb')

        seasons = stats_df["SEASON_ID"].tolist()
        season = st.selectbox(
            "Season", seasons, index=len(seasons) - 1, key=f"{key_prefix}_season"
        )
        season_row = stats_df[stats_df["SEASON_ID"] == season].iloc[0]

        m1, m2, m3 = st.columns(3)
        m1.metric("PPG", season_row["PPG"])
        m2.metric("RPG", season_row["RPG"])
        m3.metric("APG", season_row["APG"])

        m1, m2, m3 = st.columns(3)
        m1.metric("FG%", f'{season_row["FG_PCT"]:.3f}')
        m2.metric("3P%", f'{season_row["FG3_PCT"]:.3f}')
        m3.metric("FT%", f'{season_row["FT_PCT"]:.3f}')

        return bio["DISPLAY_FIRST_LAST"], season_row, stats_df


col_a, col_b = st.columns(2)
result_a = render_player_column(col_a, "A", "LeBron James", "a")
result_b = render_player_column(col_b, "B", "LaMelo Ball", "b")

if result_a and result_b:
    name_a, season_a, stats_a = result_a
    name_b, season_b, stats_b = result_b

    st.subheader("Selected-season head-to-head")
    comparison_df = pd.DataFrame(
        {
            "Player": [name_a, name_b],
            "PPG": [season_a["PPG"], season_b["PPG"]],
            "RPG": [season_a["RPG"], season_b["RPG"]],
            "APG": [season_a["APG"], season_b["APG"]],
        }
    ).melt(id_vars="Player", var_name="Stat", value_name="Per game")

    bar_fig = px.bar(comparison_df, x="Stat", y="Per game", color="Player", barmode="group")
    st.plotly_chart(bar_fig, width="stretch")

    st.subheader("Career trend: points per game")
    x_mode = st.radio(
        "Align seasons by", ["Calendar season", "Career season #"], horizontal=True
    )

    stats_a = stats_a.assign(Player=name_a, SEASON_NUM=range(1, len(stats_a) + 1))
    stats_b = stats_b.assign(Player=name_b, SEASON_NUM=range(1, len(stats_b) + 1))
    combined = pd.concat([stats_a, stats_b], ignore_index=True)

    x_col = "SEASON_ID" if x_mode == "Calendar season" else "SEASON_NUM"
    x_title = "Season" if x_mode == "Calendar season" else "Season # in career"

    line_fig = px.line(combined, x=x_col, y="PPG", color="Player", markers=True)
    line_fig.update_layout(xaxis_title=x_title, yaxis_title="Points per game")
    st.plotly_chart(line_fig, width="stretch")
