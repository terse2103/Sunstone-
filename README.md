# PlacementIQ

AI-powered placement readiness intelligence for Sunstone Edtech students and counselors.

- **Student view** (Pillars A + B): readiness score, ELQD skill radar, AI-generated top 3 priority gaps
- **Counselor view** (Pillar C): at-risk student panel with AI-generated intervention briefs
- **Evals view**: read-only results of the three required eval suites

See [`docs/architecture.md`](./docs/architecture.md) for the full system design.

---

## Demo

_Live URLs will be filled in during Phase 9._

- Frontend: _TBD_
- Backend (Swagger): _TBD_
- Backend health: _TBD_

> First request after idle may be slow due to free-tier cold start (~30s).

---

## Local setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- An Anthropic API key (optional — the backend falls back to templated strings if missing)

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS / Linux
pip install -r requirements.txt
cp .env.example .env             # then fill in ANTHROPIC_API_KEY
uvicorn app.main:app --reload
```
The API boots at <http://localhost:8000>. Swagger UI at `/docs`. Health check at `/healthz`.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
The app boots at <http://localhost:5173>.

### Evals
```bash
cd backend
python ../evals/run.py
```
Writes `evals/results/report.json` + `report.md`. Exits non-zero if any eval fails.

---

## Environment variables

| Variable | Where | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | backend | Live LLM rationale + intervention briefs. Optional — fallback strings used if missing. |
| `ALLOWED_ORIGINS` | backend | Comma-separated CORS allow-list. Default: `http://localhost:5173` |
| `VITE_API_BASE_URL` | frontend | Backend URL. Default: `http://localhost:8000` |

---

## Repo layout

```
backend/    FastAPI app (routes, core engine, LLM layer, seed data)
frontend/   Vite + React + TypeScript SPA
evals/      Golden datasets, runner, committed results
docs/       Architecture, implementation plan, edge cases, rules
```

---

## Troubleshooting

- **CORS error in browser console** — confirm `ALLOWED_ORIGINS` on the backend includes the frontend URL exactly (no trailing slash).
- **Backend cold start** — free-tier hosting sleeps after idle; first request after sleep takes ~30s.
- **Empty / templated LLM output** — `ANTHROPIC_API_KEY` is unset, invalid, or rate-limited; the backend intentionally falls back to a deterministic string.
