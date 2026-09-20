# Methodology

This document tracks data and modeling decisions as they are made: feature
engineering choices, metrics used, validation strategy, and known
limitations. Updated whenever an ML/data choice is introduced (see
CLAUDE.md, working rule 7).

## Task 1.4 — clean.py: field selection and scope

`clean_player_bio()` and `clean_career_stats()` (src/clean.py) tidy the raw
API responses from `fetch.py` into DataFrames, keeping only the fields
relevant to V1's profile/comparison pages (1.6/1.7) rather than every field
the API returns (e.g. team logo codes, roster-status flags are dropped).

- `HEIGHT` is converted from the API's `"6-9"` (feet-inches) string to
  total inches — the only cleaning transformation applied; everything else
  is column selection and dtype coercion (`BIRTHDATE` to datetime).
- `clean_career_stats()` uses only `SeasonTotalsRegularSeason` — season
  *totals* (e.g. total points, total rebounds), not per-game averages.
  Per-game stats (PPG/RPG/APG) are the more commonly displayed form and
  will need to be computed eventually, but deliberately deferred out of
  `clean.py` (either to `database.py` or the Streamlit layer) to keep this
  stage limited to tidying the API's own fields, not adding derived
  business logic. Relevant again in V2: per-game rate stats, not raw
  totals, are the natural inputs for the similarity/clustering features
  (2.1), so this decision will need revisiting there.

## Task 1.7 — comparing players across different career lengths/eras

The comparison page (`pages/1_Player_Comparison.py`) plots two players' full
career PPG trends on one chart, with a toggle between two ways to align the
x-axis: actual calendar season (`SEASON_ID`), or season number within each
player's own career (1st season, 2nd season, ...). Calendar alignment
answers "who was better in the same real-world year"; career-number
alignment answers "how did their trajectories compare at the same career
stage," which is the only fair comparison when two players' careers don't
overlap in time at all (e.g. a player who retired before the other
debuted). Both are kept, switchable, rather than picking one — relevant
again for any future model that compares players across eras (a V2
similarity model would face the same "raw season vs. career stage"
alignment question when building features).
