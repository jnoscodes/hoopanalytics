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

## Next task
1.3 Data pipeline — fetch.py