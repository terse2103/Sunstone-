# PlacementIQ — Manual Setup

Things only **you** can do — credentials, accounts, recordings, and human-in-the-loop actions Claude cannot perform.

Tick `[x]` as you finish each step. Claude maintains this file: whenever implementation work reveals a new manual step, it gets appended here as an unchecked box (see [`Rules.md`](./Rules.md) §Process/8).

**Related:** [`ImplementationPlan.md`](./ImplementationPlan.md) · [`architecture.md`](./architecture.md) · [`Rules.md`](./Rules.md)

---

## 1. Local development (needed to run + demo locally)

### 1.1 Anthropic API key
- [x] Create an Anthropic account at `https://console.anthropic.com`
- [x] Generate an API key under **Settings → API Keys** (the `sk-ant-...` value)
- [x] Add at least a few dollars of credit if your account is new
- [x] Copy `backend/.env.example` to `backend/.env`
- [x] Paste the key into `ANTHROPIC_API_KEY=` in `backend/.env`

> **Note:** the backend already falls back to deterministic templated strings if the key is missing (`EdgeCases.md` §5.1), so the demo runs without one — but the LLM rationale + intervention briefs are much richer with a live key.

### 1.2 Frontend env (optional locally)
- [x] ~~Copy `frontend/.env.example` to `frontend/.env`~~ — N/A, default `http://localhost:8000` works for your setup.

### 1.3 First-run sanity check
- [x] `cd backend && ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload` — confirm `/healthz` returns `ok` *(Claude verified: backend boots clean, `.env` loaded, `/healthz` → `{"status":"ok"}`. Required `load_dotenv()` to be wired in `app/main.py` — fixed.)*
- [x] `cd frontend && npm run dev` — confirm Vite serves on `http://localhost:5173` and the underlying API chain works *(Claude verified: login (student + counselor), `/api/students` (12), `/readiness` (with `benchmark` field), `/gaps` (live LLM rationales), `/at-risk` (4 flagged), `/brief` (live), mark-action → `204`, `/evals` → `not_run`, unknown id → `404`.)*
- [x] **You still need to:** open `http://localhost:5173` in a browser and walk the visual demo flow (Student → score, radar, gaps → logout → Counselor → at-risk list → brief → mark action → `/evals`). Verify mobile (360px) at the same time.

---

## 2. Evals (Phase 8 prerequisite)

- [x] Once `evals/run.py` exists, run `python evals/run.py` from the project root
- [x] Inspect `evals/results/report.md` — confirm all three suites pass thresholds
- [x] Commit `evals/results/report.json` *and* `evals/results/report.md` (the deployed app reads `report.json` from disk — see `Rules.md` §Git/4)

---

## 3. Deployment (Phase 9 prerequisites — single Vercel project)

The entire project (frontend SPA + FastAPI backend) ships as one Vercel deployment — see `architecture.md` §8.1.

### 3.1 Vercel account + project
- [ ] Create a Vercel account at `https://vercel.com`
- [ ] **New Project → Import from GitHub** → pick this repo
- [ ] Leave **Root Directory** as the repo root (do *not* set it to `frontend/`) — Vercel needs to see both `frontend/` and `api/` from the root
- [ ] Confirm Vercel auto-detects Vite (frontend) and Python (api/) builders from the committed `vercel.json`

### 3.2 Env vars on Vercel
- [ ] Set `ANTHROPIC_API_KEY=<the key from §1.1>` in **Project Settings → Environment Variables**
- [ ] *(Optional)* leave `VITE_API_BASE_URL` unset — the frontend defaults to relative `/api/*` paths under same-origin
- [ ] **No `ALLOWED_ORIGINS` needed** — frontend and backend share an origin in production, so CORS is bypassed (still required for local dev; see `backend/.env.example`)

### 3.3 First deploy + verification
- [ ] Trigger the first deploy (Vercel does this automatically on import)
- [ ] Note the live URL (e.g. `https://placementiq.vercel.app`)
- [ ] Verify `https://<live-url>/api/healthz` returns `{"status":"ok"}`
- [ ] Verify `https://<live-url>/api/evals/results` returns the committed `report.json` (status `pass`, not `not_run`)
- [ ] Walk the full demo flow on the live URL (Student dashboard → Counselor flow → Evals page) on both desktop and mobile (360px)
- [ ] Capture the cold-start latency (~1–2s expected for the first request after idle) for the README troubleshooting section

---

## 4. Phase 10 — submission deliverables

- [ ] Take screenshots of: Student dashboard, Counselor at-risk list, Intervention brief, Evals page (mobile + desktop)
- [ ] Drop screenshots into `docs/screenshots/` and reference them in `README.md`
- [ ] Record the demo walkthrough video (Pillars A + B + C + evals page) — store the link in `README.md`
- [ ] Final README review: setup steps reproduce a working local demo from a fresh clone
- [ ] Final pass: ensure all docs (architecture / edge cases / plan / rules / todo / manual-setup) match what was actually built

---

## 5. Privacy & safety

- [ ] Confirm `students.json` contains no real-person names before any public demo (see `EdgeCases.md` §10.1)
- [ ] README explicitly notes that all data is synthetic and Anthropic's logging policy applies (`EdgeCases.md` §10.2, §10.3)

---

## How this file gets maintained

Claude updates this checklist whenever implementation surfaces a new manual step — new env var, new account, new credential, new human-only action. Steps land here as unchecked boxes *before* Claude asks you to do them, so nothing slips through the cracks. You tick them off as you finish; Claude won't tick them for you.
