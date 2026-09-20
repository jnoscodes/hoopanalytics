# Progress Log

## Last session: 2026-09-20
Completed task: 1.1 Repo setup

- Created folder skeleton: `data/raw/`, `data/processed/`, `notebooks/`,
  `src/`, `docs/`, `tests/`.
- Added minimal `README.md` (stack, setup steps, structure overview).
- Added `requirements.txt` pinning the V1 stack: nba_api, pandas,
  streamlit, plotly.
- Created a local `.venv` and installed dependencies — verified all four
  import correctly (nba_api 1.11.4, pandas 3.0.6, streamlit 1.64.0,
  plotly 7.1.0).
- Added `docs/methodology.md` stub (to be filled in once an ML/data
  decision is made, per CLAUDE.md working rule 7).
- Committed CLAUDE.md, ROADMAP.md, and PROGRESS.md themselves to the repo
  (previously only local drafts, untracked by git).
- Reused the existing `.gitignore` as-is — it already covers `.venv/`,
  `__pycache__/`, `*.db`, and `.streamlit/secrets.toml`.

## Decisions made
- Chose a flat `src/` package (not `src/hoopanalytics/`) to keep the
  structure simple for a portfolio-sized project; pipeline modules
  (fetch.py, clean.py, database.py) will live directly under `src/` in
  tasks 1.3–1.5.
- No `app.py`/Streamlit entry point yet — deferred to tasks 1.6–1.7 to
  avoid scope creep beyond 1.1.

## Last session: 2026-09-20 (cont'd)
Completed task: 1.2 API exploration in a notebook

- Added `notebooks/api_exploration.ipynb`, executed with real outputs:
  static player/team lookups (`nba_api.stats.static`) work instantly,
  offline; three live `stats.nba.com` endpoints (`CommonPlayerInfo`,
  `PlayerCareerStats`, `LeagueGameLog`) all `ReadTimeout` after 15s.
- Initial root-cause hypothesis (since corrected, see below): attributed
  the timeouts to `stats.nba.com` blocking the cloud sandbox's
  datacenter IP specifically.

## Correction — 2026-09-20
The cloud-IP-blocking hypothesis above was tested and disproved: the
same `CommonPlayerInfo` call was re-run from a home network (residential
IP), outside the sandbox, and produced an identical `ReadTimeout` on the
same timeout window. The static endpoints again worked instantly. This
rules out IP origin as the cause.

Corrected explanation, sourced from `nba_api`'s issue tracker: the live
`stats.nba.com` endpoints are independently known to hang/timeout
unpredictably regardless of where the request comes from — a
long-running, widely reported pattern
([#633](https://github.com/swar/nba_api/issues/633),
[#176](https://github.com/swar/nba_api/issues/176),
[#125](https://github.com/swar/nba_api/issues/125),
[#320](https://github.com/swar/nba_api/issues/320)), not a sandbox
artifact. Cloud-IP blocking is a real, separately documented issue for
this API, it just isn't what caused this particular timeout. Full
writeup in `notebooks/api_exploration.ipynb`, "Findings" section.
- Added `requirements-dev.txt` (jupyter, ipykernel) as a dev-only
  dependency, kept separate from the app's runtime `requirements.txt`.

## Decisions made (1.2)
- Selected endpoints for V1: static `players`/`teams` for id lookup,
  `CommonPlayerInfo` + `PlayerCareerStats` for the profile/comparison
  pages (1.6/1.7). `LeagueGameLog` explored but not used until V2.
- `fetch.py` (task 1.3) will need to: throttle calls (~0.6-1s delay),
  retry + fail fast on timeout instead of hanging indefinitely, and
  cache raw responses to `data/raw/` so a flaky endpoint doesn't have to
  be re-hit on every pipeline run.
- No IP/network workaround (proxy, VPN, alternate hosting) adopted —
  since the timeouts aren't IP-specific, none would reliably fix it.
  VPN specifically has mixed evidence in the community: it helps with
  the *separate* cloud-IP-blocking issue, but
  [#30](https://github.com/swar/nba_api/issues/30) reports a VPN
  *causing* hangs. Documented as a manual fallback to try if `fetch.py`
  proves consistently unusable, not built into the project.

## Correction #2 — 2026-09-20
The correction above ("not IP/VPN-related, `stats.nba.com` just hangs
regardless of origin") was itself built on a confounded test. The
"home network, residential IP, outside the sandbox" retest that led to
that conclusion was run on this same local machine, which had a US VPN
active by default — so that retest was never actually off-VPN either.

Retested properly this session: same three endpoints
(`CommonPlayerInfo`, `PlayerCareerStats`, `LeagueGameLog`), same
machine. First with the VPN on: all three `ReadTimeout` again,
consistent with every prior attempt. Then the VPN was disabled,
confirmed via a public-IP check (`ifconfig.me` returned a French
residential IP, not the VPN's US exit node), and the three endpoints
were re-run in a fresh Python process: all three succeeded in 2-4s
each, no retry needed.

**Corrected root cause: the US VPN was breaking these endpoints.**
`stats.nba.com` is not inherently flaky in general — it responds
quickly on a direct connection. This matches a separately known
community report ([#30](https://github.com/swar/nba_api/issues/30))
that a VPN can *cause* hangs on these endpoints, rather than being a
workaround for cloud-IP blocking as originally assumed. Both prior
explanations (cloud-IP blocking, then "hangs unpredictably regardless
of origin") are superseded by this one.

## Decisions made (correction #2)
- `fetch.py` (1.3) no longer needs to assume the API is fundamentally
  unreliable by design — but timeout + bounded retry + raw-response
  caching are kept anyway as standard defensive practice for any
  network pipeline (protects against genuine transient blips, not just
  this specific VPN issue).
- Documented for future reference: if live endpoints hang again during
  development, check VPN status before assuming an API-side problem.

## Last session: 2026-09-20 (cont'd)
Completed task: 1.3 Data pipeline — fetch.py

- Added `src/fetch.py`: `get_player_id()` (offline static lookup),
  `fetch_player_info()` and `fetch_player_career_stats()` (live
  `CommonPlayerInfo` / `PlayerCareerStats`, the two endpoints selected
  in 1.2).
- Each live fetch: checks `data/raw/` for a cached raw JSON response
  first; on a miss, calls the endpoint with a 10s timeout and up to 3
  retries (fails loudly with a clear error after exhausting retries,
  instead of hanging); throttles with a 0.7s sleep between live calls;
  saves the raw response to `data/raw/` on success.
- Verified end-to-end against the live API: first run fetched both
  endpoints live and wrote 2 cache files; second run completed in
  ~1.6s (python startup only) by reading from cache, confirming no
  redundant network calls.
- Added `data/raw/*` (except `.gitkeep`) to `.gitignore` — cached raw
  API responses are regenerable and shouldn't be committed.

## Decisions made (1.3)
- Retry/timeout/caching logic kept in `fetch.py` even though the root
  cause turned out to be the VPN (see correction #2) — this is
  standard defensive practice for any network-dependent pipeline stage,
  not a workaround for one specific bug.
- Raw responses cached as one JSON file per endpoint+player_id in
  `data/raw/`, matching the fetch → clean → database pipeline split:
  this stage only stores the untouched API response; parsing into
  clean tabular data is `clean.py`'s job (task 1.4).
- Fixed 0.7s throttle between live calls (not adaptive rate-limiting)
  — simple and sufficient at this project's scale, though an adaptive
  approach would be more robust to real rate limits if traffic grew.

## Last session: 2026-09-20 (cont'd)
Completed task: 1.4 Data pipeline — clean.py

- Added `src/clean.py`: `clean_player_bio()` and `clean_career_stats()`,
  reshaping the raw JSON from `fetch.py` (headers + rowSet arrays) into
  typed pandas DataFrames, selecting only the fields relevant to V1's
  profile/comparison pages.
- `HEIGHT` converted from the API's `"6-9"` string to total inches
  (the one real cleaning transformation); `BIRTHDATE` coerced to
  datetime; everything else is column selection.
- `clean_career_stats()` uses `SeasonTotalsRegularSeason` only —
  postseason/all-star/college/showcase and the separate rankings/highs
  result sets are left unused, matching the 1.2 endpoint-selection
  decision.
- Verified against the live cached data (LeBron James, 23 seasons):
  bio row and full season-by-season table both render with correct
  values and dtypes.
- Logged the field-selection scope and the deferred per-game-average
  decision in `docs/methodology.md`, since it's relevant again for V2
  feature engineering (2.1).

## Decisions made (1.4)
- Went with option (A) from the two presented: `clean.py` stays limited
  to reshaping/typing the API's own fields — no derived stats. Season
  totals (not per-game averages) are what's returned; PPG/RPG/APG are
  genuinely the more interesting display data and will need to be
  computed eventually, but deliberately deferred to `database.py` or
  the Streamlit layer, not decided unilaterally to add here.
- No error handling added for missing/malformed `HEIGHT` values (e.g.
  a hypothetical player with no height on record) — not something the
  selected endpoints have been observed to return, and speculative
  handling for an unconfirmed case isn't worth the complexity at this
  stage. Flagged here as a known gap if it surfaces later.

## Last session: 2026-09-20 (cont'd)
Completed task: 1.5 Data pipeline — database.py (SQLite schema + insertion)

- Added `src/database.py`: `init_db()` creates two tables —
  `players` (PK `PERSON_ID`) and `career_stats` (composite PK
  `PLAYER_ID, SEASON_ID`, FK `PLAYER_ID` -> `players.PERSON_ID`) —
  modeling the real one-player-to-many-seasons relationship.
  `insert_player_bio()` / `insert_career_stats()` write a cleaned
  DataFrame from `clean.py` into the matching table via
  `INSERT OR REPLACE`, so re-running the pipeline for a player updates
  their rows instead of duplicating or erroring.
- Hit and fixed a real bug while verifying: `sqlite3` can't bind a
  pandas `Timestamp` directly (`clean_player_bio()`'s `BIRTHDATE`
  column) — added `_row_for_sqlite()` to convert it to an ISO string
  at insertion time, keeping the `datetime` dtype in `clean.py`'s
  output (useful for pandas/Streamlit) while satisfying `sqlite3`'s
  driver.
- Verified end-to-end: first run created `data/processed/hoopanalytics.db`
  with 1 player row and 23 season rows; second run against the same
  player left both counts unchanged, confirming `INSERT OR REPLACE`
  works as intended.
- **Correction to the 1.1 log:** that entry claimed `.gitignore`
  "already covers ... `*.db`" — checked while verifying this task, and
  that's inaccurate; only Django's `db.sqlite3` was covered, not a
  general `*.db`/`data/processed/` pattern. Added
  `data/processed/*` (except `.gitkeep`) to `.gitignore` now that
  `database.py` actually produces a `.db` file there.

## Decisions made (1.5)
- Chose explicit `sqlite3` + hand-written `CREATE TABLE` schema over
  `DataFrame.to_sql()` (option A over B, as discussed) — more code, but
  a real, explainable schema with primary/foreign keys, matching what
  the roadmap task ("SQLite schema + insertion") implies is wanted.
- `INSERT OR REPLACE` chosen for idempotency over a plain `INSERT`
  (which would error on re-running the pipeline for an existing
  player/season) or a manual check-then-update — SQLite's built-in
  conflict resolution is simpler and the primary key already enforces
  uniqueness correctly.

## Last session: 2026-09-21
Completed task: 1.6 Streamlit — player profile page

- Added `app.py` (repo root, Streamlit's entry point — deferred since
  task 1.1). Text input to search a player by name; resolves via
  `get_player_id()`, checks the SQLite DB first, and on a cache miss
  runs the full `fetch -> clean -> insert` pipeline before reading
  back. Displays bio metrics and a season-by-season table.
- Resolved the 1.4 deferred decision here: per-game averages
  (PPG/RPG/APG) are computed from season totals at display time in
  `app.py` (`with_per_game_averages()`), not pushed back into
  `clean.py`/`database.py`.
- Added a Plotly line chart of points-per-game across a player's
  career.
- Added `.claude/launch.json` (Streamlit dev server config) to make
  the app previewable/testable going forward.
- Tested live in a browser (not just import-checked): verified a
  cache-hit search (LeBron James, already in the DB), a cache-miss
  search (Nikola Jokic — triggers a live fetch, insert, then display),
  and an invalid name (shows a clean `st.error`, not a raw traceback).
- **Bug found and fixed during testing:** `sqlite3.ProgrammingError:
  SQLite objects created in a thread can only be used in that same
  thread`. Streamlit reruns scripts on a thread pool, not one fixed
  thread, so the `st.cache_resource`-cached connection from
  `database.init_db()` broke on the second rerun. Fixed in
  `src/database.py` by opening the connection with
  `check_same_thread=False` — safe here since the app never issues
  concurrent writes against it, only one query/insert at a time.
- Updated `README.md` with a "Running the app" section (first
  user-facing feature, per working rule 7).

## Decisions made (1.6)
- DB-first, pipeline-on-miss strategy: `database.py` is used as a real
  cache by the app (fast path for repeat searches), not left idle —
  first search for any given player is slower (live API + insert),
  every later search for that player is a local read.
- `st.cache_data` on the fetch-or-load function and `st.cache_resource`
  on the DB connection — idiomatic Streamlit, avoids re-running the
  whole lookup (or reopening the DB) on every widget interaction, not
  just on a new search.
- No shared "orchestration" module extracted yet for the
  fetch-or-load-from-DB logic, even though 1.7 (comparison page) will
  likely need the same thing — kept inline in `app.py` for now rather
  than guessing at the right shared shape before a second caller
  exists; revisit extraction when writing 1.7.

## Last session: 2026-09-21 (cont'd)
Completed task: 1.7 Streamlit — player comparison page

- Extracted the shared `get_connection()`, `get_or_build_player()`, and
  `with_per_game_averages()` logic out of `app.py` into `src/pipeline.py`
  (the extraction flagged as deferred back in 1.6) — now used by both
  `app.py` and the new comparison page. Also added
  `get_headshot_url(person_id)` to the shared module.
- Added `pages/1_Player_Comparison.py` (Streamlit's `pages/` convention
  auto-adds it to the sidebar nav). Two independent player pickers, each
  with its own season dropdown (defaulting to that player's most recent
  season) — e.g. LeBron's 2025-26 vs. LaMelo's 2020-21 rookie season is
  a valid, deliberate combination, not just "both latest."
- Added a grouped bar chart (PTS/REB/AST) for the two selected
  player-seasons, and a full-career PPG line chart overlaying both
  players, with a radio toggle between two x-axis alignments: actual
  calendar season, or season number within each player's own career
  (see `docs/methodology.md` for why both are kept).
- Added player headshots (NBA CDN, unofficial but verified stable
  pattern) to both the profile page and the comparison page.
- Tested live in a browser: verified both pages render correctly, the
  headshot images load for an active star, a young player, and a
  retired legend; independent season selection updates only the
  affected player's metrics and the shared bar chart; one invalid name
  in the comparison page shows a clean error in that column only,
  while the other column and its data still render, and the combined
  charts correctly don't appear (short-circuited on the missing
  player). Verified chart data directly via the browser's JS console
  (not just screenshots) after an earlier task's screenshot crop had
  been misleading about how much data was actually plotted.
- Updated `README.md` and `docs/methodology.md`.

## Decisions made (1.7)
- Season-level head-to-head (pick a specific season per player) instead
  of a single aggregate "career average" comparison — matches what was
  actually asked for, and is more interesting: it lets you compare
  specific moments (peak season vs. peak season, rookie year vs. rookie
  year, or any other combination) rather than flattening a career into
  one number.
- Both chart-alignment modes (calendar season and career season #) kept
  as a user-facing toggle rather than picking one — see
  `docs/methodology.md`.
- Known, deliberately deferred polish item: the sidebar nav label for
  the profile page reads "app" (Streamlit derives it from the
  filename). Fixing this properly means switching to the
  `st.navigation`/`st.Page` API, a bigger structural change than this
  task's scope — not done now to avoid scope creep beyond 1.7.

## Next task
1.8 Complete v1 README
