# PlacementIQ — Implementation Tracker

**Overall Progress: 22%** (13 of 59 tasks)
**Last updated:** 2026-05-20

Update protocol: see [`Rules.md`](./Rules.md). Mark `[x]` immediately on completion, update the overall and per-phase percentages, and bump the "Last updated" date.

**Related:** [`architecture.md`](./architecture.md) · [`ImplementationPlan.md`](./ImplementationPlan.md) · [`EdgeCases.md`](./EdgeCases.md) · [`Rules.md`](./Rules.md)

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

## Phase 2 — Backend Core Engine — 0% (0 of 6)

- [ ] core/scoring.py — compute_dimension_score + compute_readiness
- [ ] Unit tests for scoring (on-track / borderline / at-risk + boundary cases)
- [ ] core/gaps.py — compute_gaps + top_n_gaps with stable tiebreak
- [ ] Unit tests for gaps (tied priorities, zero gaps, fewer-than-n)
- [ ] core/at_risk.py — assess_at_risk with trajectory slope + risk levels
- [ ] Unit tests for at_risk (boundary cases §4.1–4.4)

---

## Phase 3 — Backend LLM Layer — 0% (0 of 3)

- [ ] llm/prompts.py — GAP_RATIONALE_PROMPT + INTERVENTION_BRIEF_PROMPT (with §5.6 guard)
- [ ] llm/client.py — AnthropicClient with cache, timeout, backoff, fallback strings
- [ ] Manual smoke test: valid key + missing-key fallback verified

---

## Phase 4 — Backend API Routes — 0% (0 of 6)

- [ ] main.py — FastAPI app, CORS, lifespan, /healthz
- [ ] routes/auth.py — POST /api/auth/login
- [ ] routes/student.py — GET /students, /students/{id}, /readiness, /gaps
- [ ] routes/counselor.py — GET /at-risk, /brief, POST /action
- [ ] routes/evals.py — GET /api/evals/results (handles not-run state)
- [ ] Manual verification via /docs (Swagger)

---

## Phase 5 — Frontend Foundations — 0% (0 of 5)

- [ ] Tailwind config + base styles + color tokens
- [ ] src/api/ — typed fetch wrapper with error handling
- [ ] AuthContext with localStorage persistence
- [ ] App.tsx with react-router placeholder routes
- [ ] Header/layout + TanStack Query provider

---

## Phase 6 — Frontend Login + Student Dashboard — 0% (0 of 6)

- [ ] LoginPage with role chooser + student picker
- [ ] StudentDashboard fetching readiness + gaps in parallel
- [ ] ReadinessScoreCard component (overall + per-ELQD bars)
- [ ] SkillRadarChart component (Recharts) with student vs benchmark
- [ ] TopGapsList component (signal + LLM rationale per gap)
- [ ] Loading skeletons + error states + mobile (360px) verification

---

## Phase 7 — Frontend Counselor + Evals Page — 0% (0 of 5)

- [ ] CounselorDashboard with sortable AtRiskTable
- [ ] InterventionDetail page
- [ ] InterventionBriefCard with "mark action taken"
- [ ] EvalsPage fetching /api/evals/results
- [ ] EvalsResultsViewer with pass/fail badges + "not run" empty state

---

## Phase 8 — Evals System — 0% (0 of 5)

- [ ] evals/datasets/score_calibration.json (10 profiles + sensitivity pair)
- [ ] evals/datasets/gap_relevance.json (5 profiles with manual top-3)
- [ ] evals/datasets/early_warning.json (8 trajectories)
- [ ] evals/run.py — runs all three, writes report.json + report.md, exit code reflects pass/fail
- [ ] Run evals, commit results, verify in-app /evals page renders

---

## Phase 9 — Deployment — 0% (0 of 5)

- [ ] Backend Dockerfile
- [ ] Deploy backend to Render or Fly.io with env vars
- [ ] Deploy frontend to Vercel with VITE_API_BASE_URL
- [ ] Verify CORS + /healthz + full demo flow on live URLs
- [ ] Document URLs + cold-start note in README

---

## Phase 10 — Polish, Docs, Demo — 0% (0 of 5)

- [ ] README finalized (setup, URLs, screenshots, env vars, troubleshooting)
- [ ] docs/phase-2-roadmap.md (Cluster B connection)
- [ ] Demo walkthrough video recorded
- [ ] Final docs pass (architecture, edge cases, plan, rules, todo)
- [ ] Cleanup pass (dead code, unused deps, leftover TODOs)
