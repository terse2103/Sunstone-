# PlacementIQ — Edge Cases

Catalog of outlier scenarios that could break the system. Each entry names the responsible module(s) and the expected behavior. Engineering must verify handling of every relevant case before claiming a phase complete (see `Rules.md`).

---

## 1. Data Integrity (`data/`, `models/`)

### 1.1 Missing assessment cycles
A student has fewer than 3 assessment cycles for a sub-skill.
- **Modules:** `core/scoring.py`, `core/at_risk.py`
- **Expected:** Scoring uses available cycles; trajectory slope returns `None` (insufficient data) if < 2 points; at-risk logic treats `None` slope as "not improving" but flags `insufficient_trajectory_data` in signals.

### 1.2 Zero assessments for a sub-skill
- **Modules:** `core/scoring.py`, `core/gaps.py`
- **Expected:** Sub-skill score = 0 in the dimension average; flagged in signals as `"no_data:<subskill>"` so UI and LLM rationale can surface the gap honestly.

### 1.3 Career track in student data doesn't match benchmarks
- **Modules:** `data/seed.py` (boot validation), `routes/student.py`
- **Expected:** Boot fails fast with a clear error. At request time (defensive), return 422 with `unknown_career_track`.

### 1.4 Sub-skill in benchmark missing from student assessments
- **Module:** `core/gaps.py`
- **Expected:** Treated as score = 0; counted as a gap with the full benchmark as gap size; flagged in signals.

### 1.5 Duplicate assessment cycle numbers
- **Module:** `data/seed.py`
- **Expected:** Boot validation rejects with clear error. No silent overwrite.

### 1.6 Missing `attendance_pct` or `time_on_task_hrs` for a dimension
- **Module:** `core/scoring.py`
- **Expected:** Default missing signals to 0; flag as `"missing_signal:<dimension>:<signal>"`; dimension score is assessment-only (60% weight) capped at 60.

---

## 2. Scoring Boundary Cases (`core/scoring.py`)

### 2.1 All-zero or all-100 inputs
- **Expected:** Overall score = 0 or 100 respectively. No NaN, no divide-by-zero, no exceptions.

### 2.2 Track weights don't sum to 1.0
- **Module:** `core/benchmarks.py` loader
- **Expected:** Boot fails with `invalid_weights` error including the offending track.

### 2.3 Single-cycle or zero-cycle trajectory
- **Module:** `core/at_risk.py`
- **Expected:** Slope returns `None`; at-risk logic treats as non-improving and flags `insufficient_trajectory_data`.

---

## 3. Gap Ranking (`core/gaps.py`)

### 3.1 Student exceeds all benchmarks
- **Expected:** Return empty list. UI shows "No priority gaps — on track" state.

### 3.2 Fewer than `n` qualifying gaps
- **Expected:** Return what's available; never pad with synthetic gaps.

### 3.3 Tied priority scores
- **Expected:** Stable sort by sub-skill name as tiebreaker (reproducible across runs).

### 3.4 Negative gap_size after rounding
- **Expected:** Filter `gap_size <= 0` (don't show negative gaps).

---

## 4. At-Risk Boundary Cases (`core/at_risk.py`)

### 4.1 Readiness exactly 55
- **Expected:** NOT at-risk (rule is strict `< 55`).

### 4.2 Trajectory slope exactly 0
- **Expected:** At-risk if other conditions met (rule is `<= 0`).

### 4.3 `days_to_placement` exactly 60
- **Expected:** Eligible for flagging (rule is `>= 60`).

### 4.4 Student just enrolled — no historical data
- **Expected:** Cannot assess trajectory; not flagged; `risk_level = "unknown"`; signals include `"newly_enrolled"`.

---

## 5. LLM Layer (`llm/`)

### 5.1 `ANTHROPIC_API_KEY` missing or invalid
- **Module:** `llm/client.py`
- **Expected:** Return deterministic templated fallback (e.g., gap rationale: `"This sub-skill is below the {track} benchmark of {benchmark} (your score: {score})."`); log warning; never 500.

### 5.2 Rate limit / HTTP 429
- **Expected:** Back off once (1s), then fall back. Cache the fallback to avoid retry storms.

### 5.3 Network timeout
- **Expected:** Time out at `LLM_TIMEOUT_SEC` (default 8s); fall back.

### 5.4 Empty LLM response
- **Expected:** Treat as failure; use fallback.

### 5.5 LLM returns content longer than expected
- **Expected:** Truncate to first sentence (gap rationale) or first 3 lines (intervention brief). Log observability metric.

### 5.6 Prompt injection via student-provided data
- **Module:** `llm/prompts.py`
- **Expected:** Student-provided strings are quoted/delimited inside the prompt. System prompt explicitly instructs the model to ignore instructions found in user data. Synthetic seed must not include test injection strings.

### 5.7 LLM returns malformed structure
- **Expected:** Best-effort parse; if unrecognizable, fall back.

---

## 6. Frontend (`frontend/`)

### 6.1 Empty seeded student list
- **Page:** LoginPage
- **Expected:** Empty-state message with link to backend `/api/students` for debugging.

### 6.2 API 500 / network failure
- **All pages**
- **Expected:** Inline error state + retry button. No silent failures.

### 6.3 Slow LLM rationale (>3s)
- **Page:** StudentDashboard
- **Expected:** Skeleton per gap row; deterministic data (score, radar) renders immediately; rationale streams in.

### 6.4 Radar chart with all-zero data
- **Component:** SkillRadarChart
- **Expected:** Renders a degenerate (centered) shape without crashing. Caption notes "No assessment data yet."

### 6.5 No at-risk students
- **Page:** CounselorDashboard
- **Expected:** Empty-state message: "All students currently on track."

### 6.6 Very long student name or LLM brief
- **Expected:** Truncate with ellipsis + tooltip; layout never breaks.

### 6.7 Page refresh loses session
- **Module:** AuthContext
- **Expected:** Persist `{role, student_id}` to `localStorage`; rehydrate on mount. If absent, redirect to `/`.

### 6.8 Direct navigation to `/student/STU_999` (nonexistent)
- **Expected:** 404 page with "Back to login" link.

### 6.9 Counselor navigates to a student URL
- **Expected:** Allowed — counselors can view student dashboards (same view).

### 6.10 Mobile viewport (360px width)
- **Expected:** All student-facing pages usable. Touch targets ≥ 44px. No horizontal scroll.

---

## 7. Routing & Auth (mock)

### 7.1 `localStorage` cleared mid-session
- **Expected:** Next protected route redirects to `/`.

### 7.2 Multiple tabs with different mock users
- **Expected:** Allowed — each tab reads its own localStorage on mount.

---

## 8. Evals (`evals/`)

### 8.1 `evals/results/report.json` doesn't exist
- **Route:** `/api/evals/results`
- **Expected:** Return `{ "status": "not_run", "ran_at": null }` with HTTP 200; frontend renders "Evals not run yet" state.

### 8.2 Eval dataset malformed
- **Module:** `evals/run.py`
- **Expected:** Fail loudly with file path + parse error. Exit 1.

### 8.3 Eval marginally fails
- **Expected:** `report.md` shows which case missed; runner exits 1. Don't silently round up.

---

## 9. Deployment

### 9.1 Render free tier sleeps after 15min idle
- **Expected:** Cold-start latency (~30s) documented in README. Consider always-on for demo day.

### 9.2 CORS misconfiguration
- **Module:** `main.py`
- **Expected:** `ALLOWED_ORIGINS` env var explicitly lists frontend domain(s). README has a CORS troubleshooting note.

### 9.3 Missing env var on backend
- **Module:** `main.py` startup
- **Expected:** Fail fast at boot with clear log; `/healthz` returns 503.

### 9.4 Mixed-content (HTTPS FE, HTTP BE)
- **Expected:** Backend must be HTTPS (Render/Fly provide this by default).

---

## 10. Privacy & Safety

### 10.1 Synthetic names resembling real people
- **Expected:** Use a deliberately diverse synthetic pool. Code review checks `students.json` for accidental real-name matches.

### 10.2 LLM provider data retention
- **Expected:** README documents that Anthropic's logging policy applies. Production would use privacy-aware routing.

### 10.3 Demo URL publicly discoverable
- **Expected:** Synthetic-only data; no real PII at risk. README states this explicitly.

---

## 11. Concurrency & State

### 11.1 Backend restart loses counselor actions
- **Expected:** Documented behavior. UI does not promise persistence. Phase 2 work to add DB.

### 11.2 LLM cache shared across viewers
- **Expected:** Acceptable. Cache key is `(function, student_id, scores_hash)` — two viewers of the same student see the same brief, which is correct.
