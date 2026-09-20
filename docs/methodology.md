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
