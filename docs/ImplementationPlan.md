# PlacementIQ — Implementation Plan

**Strategy:** Horizontal layers — backend → frontend → evals → deploy.
**Test approach:** Unit tests on `core/` (pytest); evals as integration tests; manual verification for frontend.
**Estimated total effort:** ~35 hours of focused work.

**Related:** [`architecture.md`](./architecture.md) · [`EdgeCases.md`](./EdgeCases.md) · [`Rules.md`](./Rules.md) · [`To-doList.md`](./To-doList.md) · [`phase-2-roadmap.md`](./phase-2-roadmap.md)

---

## Phase 0 — Repo & Tooling Setup

**Goal:** A buildable, runnable scaffold for both backend and frontend with placeholder routes/pages.

**Tasks:**
- Initialize git repo at project root
- Create folder structure per `architecture.md` §10
- Backend: `pyproject.toml` (or `requirements.txt`), pytest config, `.env.example` listing `ANTHROPIC_API_KEY` and `ALLOWED_ORIGINS`
- Frontend: scaffold Vite + React + TypeScript
- Install frontend deps: Tailwind, `react-router-dom`, `@tanstack/react-query`, `recharts`
- Root `README.md` skeleton with sections for setup, env vars, demo URLs (filled in later phases)
- `.gitignore` covering both stacks + `.env` + `__pycache__` + `node_modules`

**Verification:**
- `pytest` runs (no tests yet, exits 0)
- `npm run dev` opens a blank Vite page
- `uvicorn app.main:app --reload` boots and serves a hello route at `/healthz`

**Edge cases:** None yet.
**Effort:** ~1 hour.

---

## Phase 1 — Backend Foundations (Models + Data + Benchmarks)

**Goal:** Typed data layer with valid seed data loaded into memory at boot.

**Tasks:**
- `app/models/` — Pydantic schemas: `Student`, `Assessment`, `ReadinessResult`, `DimensionScore`, `Gap`, `AtRiskAssessment`, `InterventionBrief`, `TrackBenchmark`, `EvalResult`
- `app/data/benchmarks.json` — 3 tracks (BFSI, Analytics, Digital Marketing) with weights, sub-skills, and `jd_frequency`
- `app/data/students.json` — ~12 synthetic students: 4 on-track / 4 borderline / 4 at-risk, spread across the 3 tracks, mix of UG/PG and campuses
- `app/data/seed.py` — load JSON into module-level dicts; validate schema, weight sums (must = 1.0), and that every student's `career_track` exists in benchmarks
- `app/core/benchmarks.py` — `get_track(name) -> TrackBenchmark`
- Unit tests for benchmark loading and seed validation (failure paths included)

**Verification:**
- Boot fails fast on malformed seed (covers EdgeCases §1.3, §1.5, §2.2)
- `get_track("BFSI")` returns the expected shape
- `pytest` green

**Edge cases:** §1.3, §1.5, §2.2
**Effort:** ~3 hours.

---

## Phase 2 — Backend Core Engine (Scoring + Gaps + At-Risk)

**Goal:** Deterministic engine that computes readiness scores, gap rankings, and at-risk flags. Fully unit-tested. This is the heart of the system.

**Tasks:**
- `app/core/scoring.py` — `compute_dimension_score`, `compute_readiness` (60% assessments + 20% attendance + 20% time-on-task; track-weighted overall)
- Unit tests for scoring covering on-track / borderline / at-risk profiles + boundary cases (§2.1)
- `app/core/gaps.py` — `compute_gaps`, `top_n_gaps` (sorted by `gap_size × dimension_weight`, stable tiebreak by sub-skill name)
- Unit tests for gaps including tied priorities, zero gaps, fewer-than-n gaps
- `app/core/at_risk.py` — `assess_at_risk` with linear regression slope over last 3 assessment cycles; risk levels `high/medium/low/unknown`
- Unit tests for at_risk covering boundary cases (§4.1–4.4)

**Verification:**
- All unit tests pass
- Hand-traced sample student outputs match expected numbers

**Edge cases:** §1.1, §1.2, §1.4, §1.6, §2.1, §2.3, §3.1–3.4, §4.1–4.4
**Effort:** ~5 hours.

---

## Phase 3 — Backend LLM Layer

**Goal:** Claude-powered narrative outputs with caching and deterministic fallback.

**Tasks:**
- `app/llm/prompts.py` — `GAP_RATIONALE_PROMPT`, `INTERVENTION_BRIEF_PROMPT` as constants. Each includes a system instruction to ignore instructions found in user data (§5.6 guard).
- `app/llm/client.py` — `AnthropicClient` reading `ANTHROPIC_API_KEY` from env, in-memory `(function, input_hash)` cache, timeout (default 8s), 1-shot backoff on 429, deterministic fallback strings, observability log on truncation/failure
- Manual smoke test: call `gap_rationale()` and `intervention_brief()` with sample inputs; remove key and verify fallback

**Verification:**
- Valid key → expected output shape
- Missing/invalid key → templated fallback returned, no exception
- Cache hit on repeat call

**Edge cases:** §5.1–5.7
**Effort:** ~2 hours.

---

## Phase 4 — Backend API Routes

**Goal:** All endpoints functional and OpenAPI-documented.

**Tasks:**
- `app/main.py` — FastAPI app, CORS middleware reading `ALLOWED_ORIGINS`, lifespan handler (calls `seed.load()`), `/healthz`
- `app/routes/auth.py` — `POST /api/auth/login` (mock, returns `{role, student_id?}`)
- `app/routes/student.py` — `GET /api/students`, `/api/students/{id}`, `/readiness`, `/gaps`
- `app/routes/counselor.py` — `GET /api/counselor/at-risk`, `/students/{id}/brief`, `POST /students/{id}/action` (in-memory set)
- `app/routes/evals.py` — `GET /api/evals/results` (returns `{status: "not_run"}` if file missing — §8.1)
- Manual verification via FastAPI's auto-generated `/api/docs`

**Verification:**
- All endpoints visible in `/api/docs`
- `curl /api/students/STU_001/readiness` returns valid ReadinessResult
- `curl /api/students/STU_001/gaps` returns gaps with LLM rationale (or fallback if key absent)
- `/api/evals/results` returns `{status: "not_run"}`

**Edge cases:** §5.1–5.7 (LLM failures surface here), §8.1
**Effort:** ~3 hours.

---

## Phase 5 — Frontend Foundations

**Goal:** Vite app with routing, API client, theming, auth context, and layout.

**Tasks:**
- Tailwind config + base styles + color tokens (mobile-first)
- `src/api/` — typed fetch wrapper with error handling
- `src/context/AuthContext.tsx` — `{role, student_id}` state with `localStorage` persistence (§6.7)
- `src/App.tsx` — `react-router-dom` setup with placeholder routes for `/`, `/student/:id`, `/counselor`, `/counselor/student/:id`, `/evals`
- Header / layout components + global TanStack Query provider

**Verification:**
- Navigation between placeholder routes works
- Refresh preserves auth (localStorage rehydration)

**Edge cases:** §6.7, §7.1
**Effort:** ~2 hours.

---

## Phase 6 — Frontend: Login + Student Dashboard (Pillars A + B)

**Goal:** Login flow + fully functional student view.

**Tasks:**
- `LoginPage` — role chooser; if Student, fetch `/api/students` and show picker
- `StudentDashboard` — fetches readiness + gaps in parallel via TanStack Query
- `ReadinessScoreCard` — big overall number + per-ELQD breakdown bars
- `SkillRadarChart` (Recharts) — student scores overlaid with track benchmark
- `TopGapsList` — gap row showing dimension, gap size, deterministic signal, LLM rationale
- Loading skeletons, error states, mobile responsive verification (360px)

**Verification:**
- Demo flow: login as Student → see score → see radar → see top 3 gaps with rationale
- Mobile viewport usable; no horizontal scroll

**Edge cases:** §6.1, §6.2, §6.3, §6.4, §6.7, §6.10
**Effort:** ~5 hours.

---

## Phase 7 — Frontend: Counselor + Evals Page (Pillar C + read-only evals UI)

**Goal:** Counselor view + read-only evals page that handles the "not run yet" state until Phase 8.

**Tasks:**
- `CounselorDashboard` — sortable `AtRiskTable` (fetches `/api/counselor/at-risk`); row click → intervention detail
- `InterventionDetail` page — fetches `/api/counselor/students/{id}/brief`; renders `InterventionBriefCard`
- `InterventionBriefCard` — 3-line LLM brief + contributing signals + "mark action taken" button (POST `/action`)
- `EvalsPage` + `EvalsResultsViewer` — fetches `/api/evals/results`; renders pass/fail badges + per-case details, or "not run yet" empty state

**Verification:**
- Demo flow: login as Counselor → at-risk list → open brief → mark action
- EvalsPage renders gracefully when results don't exist

**Edge cases:** §6.2, §6.5, §6.6, §6.9, §8.1
**Effort:** ~4 hours.

---

## Phase 8 — Evals System (Datasets + Runner + In-App Wire-Up)

**Goal:** Three eval suites passing, with committed `report.json` + `report.md`. In-app `/evals` page renders the results.

**Tasks:**
- `evals/datasets/score_calibration.json` — 10 golden profiles with outcome labels; includes a sensitivity test pair (same student, +15 to one assessment, expect overall to move meaningfully)
- `evals/datasets/gap_relevance.json` — 5 profiles each with a manually-defined top-3 gap list
- `evals/datasets/early_warning.json` — 8 trajectories (4 truly at-risk, 4 on-track)
- `evals/run.py` — imports `app.core.*` (no logic duplication), runs all three datasets, computes precision/recall/sensitivity per `architecture.md` §7.1 thresholds, writes `report.json` + `report.md`, exits 1 on any failure
- Run evals; commit `evals/results/`; verify `/evals` page in frontend renders the results live

**Verification:**
- `python evals/run.py` produces both report files
- All three evals pass their thresholds
- Exit code reflects pass/fail
- `/evals` page renders the latest results

**Edge cases:** §8.1, §8.2, §8.3
**Effort:** ~4 hours.

---

## Phase 9 — Deployment

**Goal:** A single Vercel deployment serving the SPA at `/` and the FastAPI backend at `/api/*`. See `architecture.md` §8 for the topology.

**Tasks:**
- `api/index.py` — Vercel Python function entry; does `from app.main import app as app` and adds `backend/` to `sys.path` so the package resolves
- `vercel.json` — Vite build for the frontend, Python runtime for `api/index.py`, rewrite `/(.*)` → `/index.html` for client-side routing, and `includeFiles` for the seed JSON + `evals/results/report.json`
- Root `requirements.txt` (or symlink to `backend/requirements.txt`) so Vercel's Python builder installs FastAPI + pydantic + anthropic
- Adjust the API client default: production `VITE_API_BASE_URL=""` so calls go to same-origin `/api/*`; local dev keeps `http://localhost:8000`
- Create the Vercel project from GitHub; set `ANTHROPIC_API_KEY` in the Vercel env-vars UI (no `ALLOWED_ORIGINS` needed in prod — same-origin)
- Verify `/api/healthz`, `/api/evals/results` (reads the committed report), and the full demo flow on the live URL
- Document the live URL + cold-start expectation in README

**Verification:**
- End-to-end demo on the live URL works (Student dashboard, Counselor flow, Evals page)
- `/api/docs` (Swagger) accessible
- Cold-start latency captured for the README

**Edge cases:** §9.1–9.4, §11.1 (counselor actions now lost per-invocation)
**Effort:** ~3 hours.

---

## Phase 10 — Polish, Docs, Phase 2 Roadmap, Demo Recording

**Goal:** Submission-ready.

**Tasks:**
- README: setup instructions for backend + frontend, live demo URL, screenshots, env-var docs, troubleshooting (cold start, CORS)
- `docs/phase-2-roadmap.md` — how Cluster B (adaptive content sequencing, AI doubt resolution) plugs into the existing engine
- Record demo walkthrough video covering: Student dashboard (Pillars A + B), Counselor flow (Pillar C), Evals page
- Final pass across all docs (architecture, edge cases, plan, rules, todo) — ensure they reflect what was actually built
- Cleanup: remove dead code, unused deps, leftover TODOs

**Verification:**
- Fresh clone + README steps reproduces a running local demo
- Demo video covers all three pillars and the evals page

**Edge cases:** §10.1–10.3
**Effort:** ~3 hours.

---

## Effort Summary

| Phase | Effort | Cumulative |
|---|---|---|
| 0 — Setup | 1h | 1h |
| 1 — Backend Foundations | 3h | 4h |
| 2 — Core Engine | 5h | 9h |
| 3 — LLM Layer | 2h | 11h |
| 4 — API Routes | 3h | 14h |
| 5 — FE Foundations | 2h | 16h |
| 6 — Login + Student Dashboard | 5h | 21h |
| 7 — Counselor + Evals UI | 4h | 25h |
| 8 — Evals System | 4h | 29h |
| 9 — Deployment | 3h | 32h |
| 10 — Polish | 3h | 35h |
