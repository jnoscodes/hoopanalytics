"""Fetch raw data from the NBA Stats API, with caching, timeouts and retries.

Endpoints selected in the 1.2 exploration notebook:
  - static players/teams: offline lookup, no network call needed.
  - CommonPlayerInfo: player bio data (profile page, task 1.6).
  - PlayerCareerStats: season-by-season stats (profile + comparison, 1.6/1.7).

Live stats.nba.com endpoints can time out (see PROGRESS.md correction #2 —
in this project's case it was a VPN issue, not the API itself, but timeouts
are still handled defensively since any network call can fail transiently).
"""

import json
import time
from pathlib import Path

from nba_api.stats.endpoints import commonplayerinfo, playercareerstats
from nba_api.stats.static import players

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
THROTTLE_SECONDS = 0.7


def get_player_id(full_name: str) -> int:
    """Look up a player's NBA Stats ID by full name (offline, no network call)."""
    matches = players.find_players_by_full_name(full_name)
    if not matches:
        raise ValueError(f"No player found matching '{full_name}'")
    return matches[0]["id"]


def _fetch_with_retry(endpoint_name: str, build_endpoint):
    """Call an nba_api endpoint constructor with a bounded timeout and retries.

    `build_endpoint` is a zero-arg callable that constructs and returns the
    endpoint object (making the network call). Raises the last exception if
    every attempt fails, instead of letting a hung request block forever.
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return build_endpoint()
        except Exception as exc:
            last_error = exc
            print(f"{endpoint_name}: attempt {attempt}/{MAX_RETRIES} failed "
                  f"({type(exc).__name__}: {exc})")
    raise RuntimeError(
        f"{endpoint_name} failed after {MAX_RETRIES} attempts"
    ) from last_error


def _cache_path(endpoint_name: str, player_id: int) -> Path:
    return RAW_DATA_DIR / f"{endpoint_name}_{player_id}.json"


def _load_cache(cache_path: Path) -> dict | None:
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    return None


def _save_cache(cache_path: Path, raw_json: dict) -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(raw_json), encoding="utf-8")


def fetch_player_info(player_id: int, use_cache: bool = True) -> dict:
    """Fetch CommonPlayerInfo (bio data) for a player, as raw API JSON."""
    cache_path = _cache_path("common_player_info", player_id)

    if use_cache:
        cached = _load_cache(cache_path)
        if cached is not None:
            return cached

    endpoint = _fetch_with_retry(
        "CommonPlayerInfo",
        lambda: commonplayerinfo.CommonPlayerInfo(
            player_id=player_id, timeout=REQUEST_TIMEOUT
        ),
    )
    time.sleep(THROTTLE_SECONDS)

    raw_json = endpoint.get_dict()
    _save_cache(cache_path, raw_json)
    return raw_json


def fetch_player_career_stats(player_id: int, use_cache: bool = True) -> dict:
    """Fetch PlayerCareerStats (season-by-season stats) for a player, as raw API JSON."""
    cache_path = _cache_path("player_career_stats", player_id)

    if use_cache:
        cached = _load_cache(cache_path)
        if cached is not None:
            return cached

    endpoint = _fetch_with_retry(
        "PlayerCareerStats",
        lambda: playercareerstats.PlayerCareerStats(
            player_id=player_id, timeout=REQUEST_TIMEOUT
        ),
    )
    time.sleep(THROTTLE_SECONDS)

    raw_json = endpoint.get_dict()
    _save_cache(cache_path, raw_json)
    return raw_json


if __name__ == "__main__":
    lebron_id = get_player_id("LeBron James")
    print(f"player_id: {lebron_id}")

    info = fetch_player_info(lebron_id)
    print(f"fetched CommonPlayerInfo, {len(info['resultSets'][0]['rowSet'])} row(s)")

    career = fetch_player_career_stats(lebron_id)
    print(f"fetched PlayerCareerStats, {len(career['resultSets'])} result set(s)")
