# HoopAnalytics

An NBA data analytics project: fetching player/team stats via `nba_api`,
storing them in SQLite, and exploring them through a Streamlit app.

## Stack (V1)

- Python
- [nba_api](https://github.com/swar/nba_api) — NBA stats data source
- pandas — data cleaning and transformation
- SQLite — local storage
- Streamlit + Plotly — interactive analysis app

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Project structure

```
data/
  raw/         # raw data pulled from the API
  processed/   # cleaned data ready for analysis
notebooks/     # exploratory notebooks
src/           # data pipeline and app code
docs/          # methodology notes
tests/         # automated tests
```

## Status

See [PROGRESS.md](PROGRESS.md) for the current task and [ROADMAP.md](ROADMAP.md)
for the full project plan.
