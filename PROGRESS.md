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

## Last session: 2026-09-21 (cont'd)
Completed task: 1.8 Complete v1 README

- Rewrote `README.md` from a bare-bones setup guide into a complete v1
  README: overview/motivation, a features list, an architecture diagram
  (fetch → clean → database → pipeline → app, in ASCII), two embedded
  screenshots, a "known limitations" section (the `stats.nba.com`/VPN
  investigation, the unofficial headshot CDN, no tests yet), an updated
  project structure (now includes `app.py`, `pages/`, `src/pipeline.py`),
  and an unofficial-project/NBA disclaimer.
- Added real screenshots at `docs/images/profile.png` and
  `docs/images/comparison.png` — the first binary assets committed to
  the repo.
- Small fix while producing the screenshots: `app.py`'s headshot was
  missing the explicit `width=150` that the comparison page already had
  — added for consistency between the two pages.
- **Screenshot capture had a real complication worth logging:** headless
  Chrome (and headless Edge) could not load the external NBA headshot
  CDN image when driven via CLI (`ERR_HTTP2_PROTOCOL_ERROR`), even
  though the same URL works fine in interactive browser testing and via
  plain `curl`/`requests` from this machine — narrowed down through
  several tests (disabling HTTP/2, legacy headless mode, no-sandbox, a
  standard user-agent — none fixed it) to a headless-Chromium-specific
  networking quirk on this machine, unrelated to the app. Worked around
  it by downloading the real headshot images directly via Python
  `requests` (which has no such issue) and compositing them onto the
  headless-captured page screenshots with Pillow, positioned and sized
  to fit the actual reserved layout space without disturbing the rest
  of the page.

## Decisions made (1.8)
- Screenshots included (per explicit go-ahead) rather than text-only —
  judged worth the added repo complexity (first binary assets) for a
  portfolio README's first impression.
- Kept the headless-Chrome + Pillow-composite approach documented here
  as a one-off doc-generation step, not as tooling — it's not something
  the app or its tests depend on, so it isn't captured in any script
  checked into the repo.

## Roadmap change — 2026-09-22
Inserted a new task, 1.9 "Deploy to Streamlit Community Cloud," before
the release tag (now renumbered 1.9 -> 1.10). Prompted by a question
about whether a recruiter could actually see the app running, not just
read the code — right now the repo has no live link.

Discussed and ruled out a false shortcut: this isn't something V4's
planned Docker + Render/Fly.io deployment would avoid either — the
underlying risk (`stats.nba.com` blocking datacenter/cloud IP ranges,
separately documented per the 1.2 investigation) applies to any cloud
host, not something specific to Streamlit Community Cloud. Waiting for
V4 would only delay the same decision, not avoid it.

Decided to deploy bare first (no pre-seeded data) and empirically test
whether an uncached player search actually fails from the live host,
rather than assume a failure and add defensive seeding for an
unconfirmed risk — consistent with how the 1.2 VPN root cause was
established (test, don't theorize).

## Decisions made (roadmap change)
- Pinned `requirements.txt` to the exact locally-verified versions
  (`nba_api==1.11.4`, `pandas==3.0.6`, `streamlit==1.64.0`,
  `plotly==7.1.0`) instead of unpinned bare names — a fresh cloud
  deploy installing latest-at-deploy-time versions would be an
  unnecessary reproducibility risk, unrelated to the actual thing being
  tested (cloud-IP blocking).
- No `runtime.txt` added — Streamlit Community Cloud's Python version
  is chosen via its own UI at deploy time, and `runtime.txt` support is
  inconsistent/deprecated there; nothing in this codebase requires a
  specific Python version above 3.10 (the newest syntax used is PEP
  604 `X | Y` unions and built-in generic type hints like `tuple[...]`).

## Investigation — 2026-09-22/23: cloud-IP blocking, confirmed

Deployed bare to Streamlit Community Cloud as planned and tested a fresh
(uncached) player search live. It failed. The full investigation:

1. **First test, in-app error (redacted):** the app's own error display
   redacts exception details for anyone who isn't the app owner (a
   Streamlit Cloud privacy feature, not a bug). The redacted traceback
   bottomed out in `http.client._read_status()`, which I initially (and
   wrongly) read as evidence of a connection being reset/interfered with
   mid-response.
2. **Correction:** the user pulled the real unredacted log from "Manage
   app". The actual root exception was a plain
   `ReadTimeout: ... Read timed out. (read timeout=10)` — identical in
   shape to every timeout seen throughout this project (1.2, and local
   VPN testing). My "connection reset" reading was an overreach from
   incomplete (redacted) evidence; flagged and corrected in-session.
3. **Diagnostic test:** a plain read timeout can't distinguish "NBA is
   blocking this IP" from "the path is just slower than 10s." Bumped
   `REQUEST_TIMEOUT` 10s -> 30s (task branch
   `experiment/longer-fetch-timeout`) as a controlled test. Result: it
   still failed, but took ~90s instead of ~20s -- roughly proportional to
   the 3x longer timeout, using the *entire* budget on all 3 attempts
   every time. That pattern (never succeeding early, always using the
   full budget) is much stronger evidence of a silent drop (no response
   ever arrives) than of a merely-slow connection. Reverted the timeout
   back to 10s afterward -- 30s didn't help and only made failures 3x
   slower to report.
4. **Research confirmed this is a known, industry-wide problem, not
   specific to Streamlit Community Cloud:** `stats.nba.com` sits behind
   Akamai bot protection that blocks by IP range and TLS fingerprint, and
   specifically blacklists **AWS, GCP, and Azure** datacenter ranges.
   Nearly every popular PaaS (Render, Fly.io, Railway, Streamlit Cloud,
   Heroku) runs its compute on top of one of those three hyperscalers, so
   this was never going to be fixable by switching cloud hosts, including
   V4's originally planned Render/Fly.io.
5. **Considered and ruled out an alternative data source
   (`balldontlie.io`):** commonly suggested specifically because it
   doesn't have this blocking problem. Checked its docs directly: the
   free tier only covers Teams/Players/Games -- season/career stats
   require a paid plan ($9.99+/mo). Not a real free fix; ruled out rather
   than recommended on the strength of its reputation alone.

## Decision — pre-seed now, real fix (relay) deferred for cost

The actual documented community fix is a small relay/proxy server hosted
*outside* AWS/GCP/Azure IP ranges, with the cloud app routing its
`stats.nba.com` calls through it. This is the right long-term fix (cheap,
~$4-5/mo on a non-hyperscaler VPS like Hetzner/OVH/Linode, and reusable
for V4) but a real recurring cost, so it's deferred until there's budget
for it -- **this is a goal for a future session, not abandoned.**

For now: pre-seed the deployed database with every currently active NBA
player (`nba_api.stats.static.players.get_active_players()`, 530 people)
via a new `src/seed.py`, committed as `data/seed/hoopanalytics_seed.db`.
`database.init_db()` bootstraps a fresh runtime database from this seed
file if one doesn't exist yet (first deploy, or any environment with an
empty `data/processed/`), while leaving the regular runtime db gitignored
and regenerable as before -- this is a deliberate, documented exception
to "the cache is regenerable, not committed," not a quiet departure from
it.

"Active players" was chosen over an arbitrary season cutoff (e.g. "1990s
onward") because it's a principled, self-relevant, self-updating
criterion -- it covers who a visitor is actually likely to search for --
rather than an arbitrary date that would need to be revisited every
season regardless.

Two real bugs hit and fixed while building the seeding script:
- Backgrounded/redirected Python processes on this machine default stdout
  to `cp1252` on Windows, which can't encode non-ASCII characters in
  player names (e.g. Jokić) -- crashed the run partway through. Fixed
  with `sys.stdout.reconfigure(encoding="utf-8")`.
- Made the seeding script resumable (skips players already present in the
  seed db) after the above crash lost an otherwise-clean run partway
  through -- valuable independent of that specific bug, since a
  ~500-player run against a real, sometimes-flaky API will hit transient
  failures.
- Separately, mid-session, `pandas` stopped importing entirely (a Windows
  Application Control policy had quarantined/blocked one of its compiled
  files) -- unrelated to this project's code, resolved by the user
  re-enabling Windows Security.

## Decision — add a getting-started tutorial

This project is going on a CV/resume, and a GitHub repo alone isn't
enough for a recruiter or anyone non-technical to actually *use* it, not
just read about it. Added `docs/GETTING_STARTED.md`: a beginner-level,
step-by-step guide (installing Python/Git, downloading the project,
running it) with real screenshots of each external page involved (Python
downloads, Git downloads, the GitHub repo's Code button), assuming no
prior command-line experience. Linked from the main README.

## Seeding results and a real bug it surfaced

Ran `src/seed.py` against all 530 active players (locally, off the VPN
confirmed clean back in the 1.2 investigation). Final seed:
**530 players, 2,937 career-stats rows, ~385KB.**

Two players (Eli John Ndiaye, Nikola Đurišić — both very recent
international signees with minimal bio data on record) crashed
`_height_to_inches()` with an empty `HEIGHT` string: exactly the gap
flagged as a known risk back in task 1.4 ("no error handling added for
missing/malformed HEIGHT values... flagged here as a known gap if it
surfaces later"). It surfaced. Fixed in `src/clean.py` (returns `None`
for an empty/missing height instead of crashing) and added
`pipeline.format_height()` so the UI shows "Unknown" instead of "None
in". Both players re-seeded successfully afterward.

Same two players also have blank `WEIGHT` and a literal `"Undrafted"`
`DRAFT_YEAR`/`ROUND`/`NUMBER` (a real, valid API value, not a bug) —
displays a little unpolished (blank weight, truncated "Undrafted" text)
but doesn't crash. Left as-is: a genuinely rare long-tail case (2 of
530, both zero-career-games players) not worth further engineering time
against right now.

## Task 1.9 complete: live demo deployed, pre-seeded, documented, tutorial added

Summary of everything above: deployed to
[hoopanalytics.streamlit.app](https://hoopanalytics.streamlit.app/),
diagnosed and confirmed a real cloud-IP-blocking limitation (not
worked around blindly), pre-seeded the deployed database with all 530
active NBA players so the live demo is reliable in practice, fixed a
real bug the seeding run surfaced, and added a full getting-started
tutorial so the project is actually usable by a non-technical visitor,
not just readable.

## Last session: 2026-09-23 (cont'd)
Completed task: 1.10 GitHub release tagged v1.0.0

- Tagged the current `main` (annotated tag `v1.0.0`) and published a
  [GitHub Release](https://github.com/jnoscodes/hoopanalytics/releases/tag/v1.0.0)
  from it, closing out the V1 milestone.
- Release notes summarize the feature set and, per an explicit request
  to make the "notable engineering" section both technically precise
  and legible to a non-engineer reviewer, each notable bug/investigation
  is written as issue -> diagnosis -> fix -> why it matters: the VPN
  root-cause correction (1.2), the cloud-IP-blocking diagnosis and
  pre-seeding fix (1.9), and the SQLite cross-thread concurrency bug
  (1.6).
- This completion log itself is a separate commit from the tag/release,
  not part of the tagged snapshot — project-tracking metadata isn't
  part of the product being released.

## V1 milestone complete

All of 1.1-1.10 are done: fetch -> clean -> database pipeline, two
Streamlit pages, a live pre-seeded deployment, a getting-started
tutorial, and a tagged v1.0.0 release. Next up per ROADMAP.md is V2
(machine learning: feature engineering, a similarity model, a
performance prediction model) -- a substantially different kind of
work from V1's data engineering, worth starting as its own session
rather than folding into this one.

## Bug fix — 2026-09-24: career trend charts silently dropping seasons

User-reported while exploring the app locally: the "points per game over
career" line chart (both the profile page and the comparison page's
calendar-season mode) stopped partway through a player's career, and for
Michael Jordan looked compressed/wrong rather than just short.

**Root cause:** Plotly auto-detects a trace's x-axis type from the data.
`SEASON_ID` strings like `"2001-02"` happen to match a valid `YYYY-MM`
date pattern (February 2001), so Plotly inferred a **date** axis. Season
strings whose second half isn't a valid month (`"1984-85"`, `"2012-13"`,
etc.) silently fail to parse as dates and vanish from the chart -- only
seasons shaped like `"20XX-01"` through `"20XX-12"` survived. This
explains both symptoms with one cause: LeBron's chart "stopping at 2012"
(his last valid-month-shaped season was 2011-12) and Jordan's looking
compressed (most of his 15 seasons got dropped, leaving only the handful
that happened to parse).

This also corrects an earlier mistake: during 1.6/1.7 testing, a similar
"chart looks cut off" observation was checked via JS (confirming the
trace's raw x-array had the full season range) and concluded to be a
screenshot-cropping illusion. That check only confirmed the data was
present, not how Plotly was *typing* the axis -- it was actually this
same bug, just not caught at the time because the verification wasn't
deep enough.

**Fix:** `fig.update_xaxes(type="category")` on every chart that plots
`SEASON_ID` (`app.py`, `pages/1_Player_Comparison.py`) -- season labels
are categorical/ordinal, never meant to be parsed as dates. Verified via
the actual Plotly figure object (not screenshots) that both LeBron's and
Jordan's charts now render the full season range, including career gaps
(e.g. Jordan's 1994/1998-2001 retirements) as honestly-omitted
categories rather than a fake interpolated line across them.

## Noted for later: UI/UX needs real design attention

Flagged directly: the app currently uses Streamlit's default component
styling throughout and looks plain. This is intentional for now -- V1-V2
priority is function and learning the underlying mechanics, not visual
design -- but a real UI/UX pass (custom styling, layout, visual
identity, possibly moving beyond default Streamlit widgets) is wanted as
a dedicated future effort, not a footnote squeezed into a feature task.
Not scheduled yet; revisit once V2 (or whichever version) is far enough
along that it's worth the investment.

## Feature — 2026-09-24: typo-tolerant player search with live suggestions

User-requested while exploring the app: the plain text input had no
suggestions and no typo tolerance (a search for "michael" with any
misspelling just failed outright, or silently returned whichever player
`find_players_by_full_name` fuzzy-matched, invisibly).

Replaced `st.text_input` with `st_searchbox` (new dependency,
`streamlit-searchbox`) on both pages -- a real dropdown-as-you-type
component, not Streamlit's native `st.selectbox` (whose filtering
happens client-side and can't run custom Python typo-tolerance logic).

**Search design -- two-tier, not pure fuzzy matching:**
1. Substring match first (fast, case-insensitive, ranks `startswith`
   results first). Handles the overwhelmingly common case: typing a
   correct partial name.
2. Fuzzy match (`difflib.SequenceMatcher`, against both the full name
   and each name token) only when no substring match exists at all.
   Catches actual typos.

This order matters and was arrived at empirically, not assumed: pure
fuzzy matching (`difflib.get_close_matches`) was tried first and
**failed on the most common case** -- short correct prefixes like "leb"
or "jok" scored too low against full names ("LeBron James", "Nikola
Jokić") to surface at all, since `SequenceMatcher`'s ratio penalizes
large length differences between a 3-character query and a full name.
Substring-first fixes this while still catching genuine typos like
"micheal jordn" -> Michael Jordan or "giannis antetokunmpo" -> Giannis
Antetokounmpo (correctly ranked above his brothers) via the fallback
tier. Benchmarked against all ~5,100 players (active + historical, not
just the 530 seeded ones, since the app can already look up anyone):
substring hits are sub-millisecond; the fuzzy fallback (only reached on
a real typo) takes ~100-230ms, still well within a usable search-as-
you-type feel.

`search_players()` returns `(display_name, person_id)` pairs, so a
selection resolves directly to an ID -- `get_or_build_player()` was
changed to take `person_id` instead of `name`, removing the
name -> ID lookup (and the `ValueError`/`st.error` path for "no player
found") entirely, since a selection can now only ever be a valid player.

Also refreshed `docs/images/profile.png` and `comparison.png` (the new
search UI looks different) -- same headless-Chrome + Pillow-composite
process as task 1.8, and a nice side confirmation that the season-axis
chart fix above actually shows the full career range in a real capture,
not just a live-tested one.

## Bug fix — 2026-09-24: shooting percentages shown as raw decimals

User-reported while testing the new search feature: FG%/3P%/FT% showed
as "0.515" instead of "51.5%" (the underlying `FG_PCT` etc. columns are
genuinely 0-1 floats, just never formatted for display). Fixed with
`st.column_config.NumberColumn(format="percent")` on the season table
and manual `*100` formatting on the comparison page's metric tiles.

## Next task
2.1 Feature engineering for the similarity model (V2 start)
