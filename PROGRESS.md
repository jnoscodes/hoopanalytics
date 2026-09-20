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

## Next task
1.2 API exploration in a notebook (nba_api endpoints, limitations, rate
limiting)