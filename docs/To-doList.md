# PlacementIQ — Implementation Tracker

**Overall Progress: 97%** (58 of 60 tasks)
**Last updated:** 2026-05-20

Update protocol: see [`Rules.md`](./Rules.md). Mark `[x]` immediately on completion, update the overall and per-phase percentages, and bump the "Last updated" date.

**Related:** [`architecture.md`](./architecture.md) · [`ImplementationPlan.md`](./ImplementationPlan.md) · [`EdgeCases.md`](./EdgeCases.md) · [`Rules.md`](./Rules.md) · [`ManualSetup.md`](./ManualSetup.md) · [`phase-2-roadmap.md`](./phase-2-roadmap.md)

---

## Phase 0 — Repo & Tooling Setup — 100% (7 of 7)

- [x] Initialize git repo at project root
- [x] Create folder structure per architecture.md §10
- [x] Backend: pyproject.toml/requirements.txt + pytest config + .env.example
- [x] Frontend: scaffold Vite + React + TypeScript
- [x] Install frontend deps (Tailwind, react-router-dom, @tanstack/react-query, recharts)
- [x] Root README.md skeleton
- [x] .gitignore (both stacks + .env + __pycache__ + node_modules)

---

## Phase 1 — Backend Foundations — 100% (6 of 6)

- [x] Pydantic models (Student, Assessment, ReadinessResult, DimensionScore, Gap, AtRiskAssessment, InterventionBrief, TrackBenchmark, EvalResult)
- [x] data/benchmarks.json — 3 tracks (BFSI, Analytics, Digital Marketing) with weights, sub-skills, jd_frequency
- [x] data/students.json — ~12 synthetic students (4 on-track / 4 borderline / 4 at-risk, spread across tracks)
- [x] data/seed.py — JSON loader with boot validation (schema, weight sums, track refs)
- [x] core/benchmarks.py — get_track()
- [x] Unit tests for benchmark loading + seed validation

---

## Phase 2 — Backend Core Engine — 100% (6 of 6)

- [x] core/scoring.py — compute_dimension_score + compute_readiness
- [x] Unit tests for scoring (on-track / borderline / at-risk + boundary cases)
- [x] core/gaps.py — compute_gaps + top_n_gaps with stable tiebreak
- [x] Unit tests for gaps (tied priorities, zero gaps, fewer-than-n)
- [x] core/at_risk.py — assess_at_risk with trajectory slope + risk levels
- [x] Unit tests for at_risk (boundary cases §4.1–4.4)

---

## Phase 3 — Backend LLM Layer — 100% (3 of 3)

- [x] llm/prompts.py — GAP_RATIONALE_PROMPT + INTERVENTION_BRIEF_PROMPT (with §5.6 guard)
- [x] llm/client.py — AnthropicClient with cache, timeout, backoff, fallback strings
- [x] Manual smoke test: valid key + missing-key fallback verified

---

## Phase 4 — Backend API Routes — 100% (6 of 6)

- [x] main.py — FastAPI app, CORS, lifespan, /healthz
- [x] routes/auth.py — POST /api/auth/login
- [x] routes/student.py — GET /students, /students/{id}, /readiness, /gaps
- [x] routes/counselor.py — GET /at-risk, /brief, POST /action
- [x] routes/evals.py — GET /api/evals/results (handles not-run state)
- [x] Manual verification via /api/docs (Swagger)

---

## Phase 5 — Frontend Foundations — 100% (5 of 5)

- [x] Tailwind config + base styles + color tokens
- [x] src/api/ — typed fetch wrapper with error handling
- [x] AuthContext with localStorage persistence
- [x] App.tsx with react-router placeholder routes
- [x] Header/layout + TanStack Query provider

---

## Phase 6 — Frontend Login + Student Dashboard — 100% (6 of 6)

- [x] LoginPage with role chooser + student picker
- [x] StudentDashboard fetching readiness + gaps in parallel
- [x] ReadinessScoreCard component (overall + per-ELQD bars)
- [x] SkillRadarChart component (Recharts) with student vs benchmark
- [x] TopGapsList component (signal + LLM rationale per gap)
- [x] Loading skeletons + error states + mobile (360px) verification

---

## Phase 7 — Frontend Counselor + Evals Page — 100% (5 of 5)

- [x] CounselorDashboard with sortable AtRiskTable
- [x] InterventionDetail page
- [x] InterventionBriefCard with "mark action taken"
- [x] EvalsPage fetching /api/evals/results
- [x] EvalsResultsViewer with pass/fail badges + "not run" empty state

---

## Phase 8 — Evals System — 100% (5 of 5)

- [x] evals/datasets/score_calibration.json (10 profiles + sensitivity pair)
- [x] evals/datasets/gap_relevance.json (5 profiles with manual top-3)
- [x] evals/datasets/early_warning.json (8 trajectories)
- [x] evals/run.py — runs all three, writes report.json + report.md, exit code reflects pass/fail
- [x] Run evals, commit results, verify in-app /evals page renders

---

## Phase 9 — Deployment (Vercel, single project) — 100% (6 of 6)

- [x] api/index.py — Vercel Python function entry that re-exports app.main:app
- [x] vercel.json — explicit builds + routes (static-build for SPA, @vercel/python for api/index.py, /assets remapped under /frontend prefix, SPA fallback to index.html)
- [x] Root requirements.txt (or symlink) so Vercel's Python builder picks up backend deps
- [x] Switch frontend default to relative /api/* (VITE_API_BASE_URL="" in prod); keep localhost:8000 for dev
- [x] Vercel project created, ANTHROPIC_API_KEY set, deployed to https://sunstone-amber.vercel.app/
- [x] Verified /api/healthz + /api/evals/results + /api/students + LLM-backed /api/gaps on live URL; cold-start ~900ms, warm ~335ms — captured in README

---

## Phase 10 — Polish, Docs, Demo — 60% (3 of 5)

- [x] README finalized (setup, live URLs, Swagger link, env vars, troubleshooting, privacy + roadmap pointer)
- [x] docs/phase-2-roadmap.md (Cluster B connection) *(written during Phase 1; reviewed against final state in Phase 10)*
- [ ] Demo walkthrough video recorded *(user action — Pillar A+B + Pillar C + Evals page)*
- [x] Final docs pass (architecture, edge cases, plan, rules, todo) — Swagger references updated to /api/docs, no Render/Fly/Dockerfile leftovers, no `/healthz` (root) leftovers
- [ ] Cleanup pass (dead code, unused deps, leftover TODOs) *(partially done — deleted scaffold frontend/README.md + unreferenced public/icons.svg; screenshots in `docs/screenshots/` still pending — user action)*
