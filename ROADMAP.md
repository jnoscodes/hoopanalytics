# Roadmap — HoopAnalytics

## V1 — Data + analysis foundation (minimum viable portfolio project)
**Stack:** Python, nba_api, pandas, SQLite, Streamlit, Plotly
- [x] 1.1 Repo setup (folder structure, venv, .gitignore, minimal README)
- [x] 1.2 API exploration in a notebook (nba_api endpoints, limitations, rate limiting)
- [x] 1.3 Data pipeline — fetch.py
- [x] 1.4 Data pipeline — clean.py
- [x] 1.5 Data pipeline — database.py (SQLite schema + insertion)
- [x] 1.6 Streamlit — player profile page
- [x] 1.7 Streamlit — player comparison page
- [x] 1.8 Complete v1 README
- [ ] 1.9 Deploy to Streamlit Community Cloud (live demo link)
- [ ] 1.10 GitHub release tagged v1.0.0

## V2 — Machine Learning
**Stack:** + scikit-learn (clustering, cosine similarity, regression/classification)
- [ ] 2.1 Feature engineering for the similarity model
- [ ] 2.2 Similar players model
- [ ] 2.3 Streamlit — "Find similar players" page
- [ ] 2.4 Performance prediction model (temporal split)
- [ ] 2.5 Rigorous evaluation
- [ ] 2.6 Detailed docs/methodology.md

## V3 — Production architecture
**Stack:** PostgreSQL (replaces SQLite), FastAPI
- [ ] 3.1 SQLite → PostgreSQL migration
- [ ] 3.2 FastAPI backend
- [ ] 3.3 Streamlit consumes the API

## V4 — Optional
**Stack:** Docker, cloud (Render/Fly.io), embeddings + vector database (RAG)
- [ ] 4.1 Dockerization
- [ ] 4.2 Cloud deployment
- [ ] 4.3 RAG assistant ("Ask HoopAnalytics")

## Current status
→ See PROGRESS.md for the exact current task.