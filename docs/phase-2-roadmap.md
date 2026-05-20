# PlacementIQ — Phase 2 Roadmap

Where the prototype goes once real Sunstone data is available.

**Related:** [`architecture.md`](./architecture.md) · [`04 problem statement.md`](./04%20problem%20statement.md) · [`ImplementationPlan.md`](./ImplementationPlan.md)

---

## 1. Trained scoring model (highest leverage)

The prototype's scoring engine is a **hand-tuned linear model** — declared weights × declared signals (see `architecture.md` §4.2). It's deliberately the simplest defensible model that fits the prototype constraints: no outcome labels, ~12 synthetic students, full explainability needed for counselors.

### 1.1 Why a trained model — and why later, not now

A trained model needs three things the prototype doesn't have:
1. **Outcome labels** — historical placed / not-placed (or offer-amount, time-to-placement) per student
2. **Volume** — enough rows that learned weights beat declared ones (rule of thumb: ≥10× rows per feature, so ≥100 placed-student records for the current 10-ish signals)
3. **Validation infrastructure** — train/test/holdout splits, calibration plots, drift monitoring

Without these, a fitted model is curve-fitting to whatever the synthetic generator implied. Worse, it would look more impressive than it actually is — the kind of bug a prototype shouldn't ship.

### 1.2 The swap, when ready

The architecture is designed so the model swap is a single-file change. `core/scoring.py` exposes:

```python
def compute_readiness(student: Student, track: TrackBenchmark) -> ReadinessResult: ...
```

Today, that function blends declared signal weights. The Phase 2 version loads coefficients from a fitted estimator:

```python
# Phase 2 sketch — core/scoring.py
_MODEL = joblib.load("models/readiness_v1.joblib")   # fitted at training time

def compute_readiness(student, track):
    features = _featurize(student, track)            # same signals as today
    overall = float(_MODEL.predict_proba(features)[0, 1] * 100)
    ...                                              # rest unchanged
```

**Recommended estimator family:** start with **logistic regression** on placed / not-placed labels. Reasons:
- **Explainability stays cheap.** Coefficients × feature values = a sentence per signal, like today's per-dimension breakdown. SHAP isn't required.
- **Calibration is well-understood.** Logistic gives probabilities natively, which we already display as a 0–100 score.
- **Sample-efficient.** Works at the volumes Sunstone is likely to have for a single track in year one.

**Gradient-boosted trees (XGBoost / LightGBM)** become worth it once we have:
- Enough rows that learning non-linearities pays off (~500+ per track)
- Stakeholder buy-in to use SHAP / partial dependence for explainability

### 1.3 What stays the same

Everything outside `core/scoring.py`:
- API contracts (`ReadinessResult`, `Gap`, `AtRiskAssessment`) — unchanged
- The LLM narrative + rationale layer — unchanged
- The frontend — unchanged
- The eval suites — **especially** the score calibration suite, which now becomes the trained-model's regression test set

### 1.4 What needs to be built around the swap

- **Feature store:** `app/ml/features.py` mirroring today's signal extraction so training and inference share code
- **Training script:** `ml/train.py` — fits, calibrates, writes the joblib + a model card with metrics
- **Model registry:** version the joblib + the feature schema. A schema mismatch at boot must fail fast (parallel to today's `seed.load()` validation)
- **Calibration check in evals:** the existing score-calibration eval becomes the regression test — refuses to ship a model that scores worse than the hand-tuned baseline on the golden profiles

---

## 2. Cluster B — features the spec lists as Phase 2

The four-pillar spec puts these explicitly out of scope for Phase 1, but they're the strongest Phase 2 candidates because the existing engine already feeds them.

### 2.1 Adaptive content sequencing

Given a student's gaps + readiness trajectory, recommend the next module / exercise. Built on top of `top_n_gaps()`:

```
gap → mapping → curated module library → recommendation
```

Curation lives in `app/data/content_library.json`. The LLM picks among matched modules (with rationale) rather than free-generating recommendations — keeps recommendations vetted.

### 2.2 AI doubt resolution

A chat surface where students ask questions about their dashboard ("why did my Quant score drop?" "what should I work on first?"). The system context is the same data the dashboard already shows — readiness, gaps, recent signals. Architectural notes:
- One Claude call per turn, conversation state in the browser (no DB needed for v1)
- Strict guard against prompt injection via student input (same delimiter pattern as today's `llm/prompts.py`)
- Cite the deterministic signals in every answer — same rule as the rest of the system

### 2.3 Career-track recommender

Currently students declare their `career_track`. Phase 2: suggest a track from the student's ELQD profile. Two-step:
1. Deterministic: best track = `argmax(sum(student.dim_score * track.weights[dim]))` per track
2. LLM: 2-sentence narrative explaining why, citing the contributing dimensions

---

## 3. Production-grade plumbing

### 3.1 Real authentication
Replace the mock login (`/api/auth/login`) with Sunstone SSO (Google Workspace / Microsoft Entra, depending on what they use). Tokens are JWTs; counselor vs. student is a role claim. No password storage in our system.

### 3.2 Persistent database
The in-memory student dict + counselor-actions set become Postgres tables. Schema sketch:
- `students` — current seed JSON, normalised
- `assessments` — append-only per cycle
- `attendance_events` — append-only per session
- `engagement_events` — append-only per LMS activity
- `counselor_actions` — `(counselor_id, student_id, action_kind, notes, taken_at)`
- `intervention_briefs` — cached LLM outputs by `(student_id, content_hash)`

Readiness becomes a materialized view refreshed nightly + on-demand for the counselor flow.

### 3.3 Counselor action audit log
`counselor_actions` table + a `/counselor/students/{id}/history` route + a panel on the intervention detail page showing prior counselor touchpoints with timestamps and notes. Solves `EdgeCases.md` §11.1 properly.

### 3.4 Multi-tenant
Sunstone runs many campuses. Adding a `tenant_id` to every table and a tenant claim to the JWT is the standard pattern. Track benchmarks become tenant-scoped (a tenant can override or add tracks).

### 3.5 Notifications
The intervention brief currently ends with a recommended action. Phase 2 can fire the nudge: WhatsApp / email to the student, slack ping to the counselor. Human-in-the-loop stays (counselor approves the message before it goes out — `architecture.md` §9.1 Principle 3).

---

## 4. Observability + safety

- **LLM cost/latency dashboard.** Today the LLM cache is in-memory; Phase 2 needs Redis-backed cache + per-route latency + cost-per-request metrics.
- **Drift detection.** Once trained, the readiness model needs PSI / KS monitoring against the training distribution. Alert if input distributions shift enough that the model is extrapolating.
- **Counselor feedback loop.** Add a "was this brief useful?" thumbs-up/down on `InterventionBriefCard`. Train on the feedback once we have volume.
- **Privacy-aware LLM routing.** If a tenant has data-residency or no-logging requirements, route those requests to an Anthropic AWS Bedrock or self-hosted gateway with appropriate retention settings.

---

## 5. What's explicitly NOT in Phase 2

Worth naming so the roadmap stays focused:
- Real-time / streaming features. Daily refresh is enough.
- A native mobile app. The web app is mobile-first; PWA is the cheaper next step if needed.
- Generative content (auto-creating practice questions). The risk/reward is poor compared to the items above.

---

## 6. Effort sketch

| Track | Effort | Unlocks |
|---|---|---|
| Trained scoring model + feature store | ~3 weeks | Better predictions, model card, drift monitoring |
| Adaptive content sequencing | ~2 weeks | Closes the "what should I do next?" loop |
| AI doubt resolution | ~2 weeks | Student self-service, reduces counselor load |
| Real auth + DB + audit log | ~2 weeks | Production deploy-readiness |
| Multi-tenant | ~1 week | Sunstone-wide rollout |

Suggested order: **auth + DB first** (unblocks everything else), **then trained scoring** (largest correctness leverage), **then Cluster B** (largest student-facing leverage).
