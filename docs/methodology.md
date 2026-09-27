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

## Task 1.9 — pre-seed criterion: active players, not a season cutoff

`stats.nba.com` blocks requests from AWS/GCP/Azure datacenter IP ranges
(confirmed via the Streamlit Community Cloud deploy investigation, see
`PROGRESS.md`), which nearly every cloud host runs on top of. Until a
relay/proxy fix is affordable, the deployed app's database is pre-seeded
via `src/seed.py` so it works reliably without depending on a live call
for every new search.

Considered seeding by an arbitrary season cutoff (e.g. "players active
since 1996-97, dropping any of their stats from before that"), but chose
`nba_api`'s `get_active_players()` instead -- every player on a current
NBA roster (530 people). Reasoning: an arbitrary date cutoff needs manual
revisiting every season and would produce oddly truncated career stats
for players whose careers straddle the cutoff (a player who debuted in
1994 would show only their post-1996 seasons, which reads as a data bug,
not a deliberate scope choice). "Currently active" is self-updating in
spirit (re-running `src/seed.py` each season naturally tracks the current
roster) and matches who a visitor is actually likely to search for, with
full, untruncated career stats for everyone included.

## Bug fix (2026-09-27) — traded seasons: one "TOT" row per player-season

`PlayerCareerStats` returns, for a player traded mid-season, one row per
team **plus** a `TOT` (total) row for that season. `clean_career_stats()`
now keeps only the `TOT` row for those seasons, so the cleaned data has
exactly one row per `(PLAYER_ID, SEASON_ID)` -- the table's primary key.

- Before this, the database happened to end up with the `TOT` row anyway
  (it is always the last row returned, so `INSERT OR REPLACE` kept it), but
  a freshly fetched player was displayed straight from `clean.py` with every
  per-team row too: 189 of 531 cached players had duplicate seasons.
  Checked against the full cache before relying on it: every multi-row
  season has exactly one `TOT` row.
- Why `TOT` rather than the per-team rows: the season-level question
  ("how many points per game did he score in 2025-26?") is answered by the
  whole season, not one stint. This matters again for V2 (2.1): per-game
  rate features must be computed on season totals, or a traded player's
  season would be split into several small-sample rows.
- Trade-off: the per-team split is discarded, so team-level analysis
  (e.g. "performance per team") isn't possible from this table. Not needed
  by any current or planned V1/V2 feature.
- Related display-only change: `HEIGHT` stays stored in total inches (a
  number, the useful form for any future modeling) and is formatted as
  feet-inches (`6'9"`) only at display time.
