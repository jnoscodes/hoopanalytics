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
- Root cause documented in the notebook: `stats.nba.com` sits behind
  bot-protection that silently stalls/drops requests from datacenter and
  cloud IP ranges — this is an IP-reputation issue (confirmed by testing
  with `nba_api`'s own headers, which made no difference), not a missing
  header or a code bug. Expected to work from a normal home network.
- Added `requirements-dev.txt` (jupyter, ipykernel) as a dev-only
  dependency, kept separate from the app's runtime `requirements.txt`.

## Decisions made (1.2)
- Selected endpoints for V1: static `players`/`teams` for id lookup,
  `CommonPlayerInfo` + `PlayerCareerStats` for the profile/comparison
  pages (1.6/1.7). `LeagueGameLog` explored but not used until V2.
- `fetch.py` (task 1.3) will need to: throttle calls (~0.6-1s delay),
  fail fast on timeout instead of hanging, cache raw responses to
  `data/raw/`, and must be run from a normal network — not CI/cloud.
  No proxy/VPN workaround chosen; deemed disproportionate for a
  portfolio project when running locally solves it.

## Next task
1.3 Data pipeline — fetch.py