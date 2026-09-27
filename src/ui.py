"""Reusable Streamlit UI pieces shared by the profile and comparison pages."""

import logging
import sqlite3
import time

import streamlit as st
from streamlit_searchbox import st_searchbox

from src.pipeline import get_or_build_player, get_player_name, has_player, search_players

logger = logging.getLogger(__name__)

# Hide the dropdown arrow and the empty "No options" menu, and make the box
# non-clearable: with a clear action enabled, a Backspace on an already-empty
# box fires react-select's "clear", which streamlit-searchbox answers by
# remounting its iframe (a visible flicker) and snapping back to the default
# player, dropping keyboard focus so the next keystrokes are lost.
SEARCHBOX_STYLE = {
    "clear": {"clearable": "never"},
    "dropdown": {"width": 0, "height": 0},
    "searchbox": {"optionEmpty": "hidden"},
}

# After a live fetch fails (e.g. stats.nba.com blocking the cloud host),
# don't retry the API for this long -- later picks fail instantly instead of
# each waiting out the full timeout/retry budget again.
LIVE_API_COOLDOWN_SECONDS = 300


@st.cache_resource
def _live_api_status() -> dict:
    """Process-wide (shared by all sessions) record of the last API failure."""
    return {"down_until": 0.0}


def player_search(conn: sqlite3.Connection, key: str, label: str, default_id: int) -> int:
    """Player search box; returns the id of the currently selected player.

    The selection lives in session_state rather than being returned by the
    fragment, since a fragment's return value is discarded on fragment-only
    reruns.
    """
    selected_key = f"{key}_selected"
    st.session_state.setdefault(selected_key, default_id)
    _player_search_fragment(conn, key, label, selected_key)
    return st.session_state[selected_key]


@st.fragment
def _player_search_fragment(conn: sqlite3.Connection, key: str, label: str, selected_key: str) -> None:
    """Search box isolated in a fragment: each keystroke reruns only this
    fragment, not the whole page. The full page reruns only once a new player
    has been successfully loaded."""
    toast_key = f"{key}_toast"
    if message := st.session_state.pop(toast_key, None):
        st.toast(message, icon="⚠️")

    current_id = st.session_state[selected_key]
    picked_id = st_searchbox(
        search_players,
        label=label,
        placeholder="Search for a player...",
        default=current_id,
        default_searchterm=get_player_name(current_id),
        style_overrides=SEARCHBOX_STYLE,
        rerun_scope="fragment",
        key=key,
    )
    if picked_id is None or picked_id == current_id:
        return

    if _try_load_player(conn, picked_id):
        st.session_state[selected_key] = picked_id
        st.rerun(scope="app")
    else:
        # Keep the current player on screen; rebuild the box so it shows
        # that player's name again instead of the one that failed.
        st.session_state[toast_key] = (
            f"{get_player_name(picked_id)} isn't available right now: "
            "live NBA stats can't be reached from here. Try an active player."
        )
        del st.session_state[key]
        st.rerun(scope="fragment")


def _try_load_player(conn: sqlite3.Connection, person_id: int) -> bool:
    """Load a player into the cache, returning False instead of raising."""
    if has_player(conn, person_id):
        get_or_build_player(conn, person_id)
        return True

    status = _live_api_status()
    if time.time() < status["down_until"]:
        return False

    try:
        get_or_build_player(conn, person_id)
        return True
    except Exception:
        # UI boundary: any fetch/clean failure becomes a toast, not a crash.
        logger.exception("Live fetch failed for player %s", person_id)
        status["down_until"] = time.time() + LIVE_API_COOLDOWN_SECONDS
        return False
