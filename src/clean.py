"""Clean raw NBA Stats API JSON (from fetch.py) into tidy pandas DataFrames.

Each function takes the raw JSON dict returned by a fetch.py function and
reshapes the relevant result set (headers + rowSet arrays) into a typed
DataFrame. No network calls and no derived/business-logic stats here —
this stage only tidies what the API already returned; e.g. per-game
averages are computed later (database.py or the Streamlit layer), since
season totals aren't the shape needed to display, but computing them is
a display-time concern, not a cleaning one.
"""

import pandas as pd

BIO_COLUMNS = [
    "PERSON_ID",
    "DISPLAY_FIRST_LAST",
    "TEAM_NAME",
    "POSITION",
    "HEIGHT",
    "WEIGHT",
    "BIRTHDATE",
    "COUNTRY",
    "SEASON_EXP",
    "JERSEY",
    "DRAFT_YEAR",
    "DRAFT_ROUND",
    "DRAFT_NUMBER",
]

CAREER_STATS_COLUMNS = [
    "PLAYER_ID",
    "SEASON_ID",
    "TEAM_ABBREVIATION",
    "PLAYER_AGE",
    "GP",
    "GS",
    "MIN",
    "PTS",
    "REB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "FG_PCT",
    "FG3_PCT",
    "FT_PCT",
]


def _result_set_to_df(raw_json: dict, result_set_name: str) -> pd.DataFrame:
    """Extract one named result set from a raw API response into a DataFrame."""
    result_set = next(
        rs for rs in raw_json["resultSets"] if rs["name"] == result_set_name
    )
    return pd.DataFrame(result_set["rowSet"], columns=result_set["headers"])


def _height_to_inches(height: str) -> int | None:
    """Convert a "feet-inches" height string (e.g. "6-9") to total inches.

    Some players (typically recent international draftees without full bio
    data on record yet) have an empty HEIGHT string rather than "F-I" -- a
    gap flagged as a known risk back in task 1.4 and confirmed for real
    while seeding active players (2/530: Eli John Ndiaye, Nikola Đurišić).
    """
    if not height:
        return None
    feet, inches = height.split("-")
    return int(feet) * 12 + int(inches)


def clean_player_bio(raw_json: dict) -> pd.DataFrame:
    """Tidy CommonPlayerInfo into a single-row bio DataFrame."""
    df = _result_set_to_df(raw_json, "CommonPlayerInfo")
    df = df[BIO_COLUMNS].copy()

    df["HEIGHT"] = df["HEIGHT"].apply(_height_to_inches)
    df["BIRTHDATE"] = pd.to_datetime(df["BIRTHDATE"])

    return df


def clean_career_stats(raw_json: dict) -> pd.DataFrame:
    """Tidy PlayerCareerStats' regular-season totals into a per-season DataFrame."""
    df = _result_set_to_df(raw_json, "SeasonTotalsRegularSeason")
    return df[CAREER_STATS_COLUMNS].copy()


if __name__ == "__main__":
    from src.fetch import fetch_player_career_stats, fetch_player_info, get_player_id

    lebron_id = get_player_id("LeBron James")

    bio_df = clean_player_bio(fetch_player_info(lebron_id))
    print(bio_df.to_string(index=False))
    print()

    stats_df = clean_career_stats(fetch_player_career_stats(lebron_id))
    print(stats_df.to_string(index=False))
