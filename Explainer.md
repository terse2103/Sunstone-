# PlacementIQ — The Full Story

How we went from an empty page about "the Indian EdTech industry" to a working AI-powered placement readiness suite for Sunstone, and where AI fits both today and in Phase 2.

This document walks through the entire journey — research, synthesis, problem framing, architecture, implementation, and the role AI plays at every layer.

---

## 1. The Approach: Why We Started With Research, Not Code

The temptation with any product brief is to start building immediately. We deliberately did not. The reasoning was simple — Sunstone is a real company with a real business model, real users, and a real set of operational constraints. Building a generic "AI for education" product would have produced something cool-looking but irrelevant. So we structured the journey as a funnel:

```
Industry landscape  →  Sunstone deep-dive  →  Pain points  →  Opportunity map
       ↓
Problem statement  →  Architecture  →  Implementation plan  →  Build  →  Evals
```

Each step narrowed the problem space using evidence from the previous one. By the time we reached "what should we build," the answer was constrained enough that the architecture practically wrote itself.

---

## 2. Step 1 — Understanding the EdTech & LMS Landscape

**Doc:** [`docs/01 edtech lms landscape.md`](./docs/01%20edtech%20lms%20landscape.md)

We started by mapping the Indian EdTech industry: market size ($7.5B in 2024–25, projected to $29–50B by 2030–35), segments (K-12, test prep, higher-ed/upskilling, B2B), and the post-BYJU's reality where investors now reward sustainable unit economics over growth-at-any-cost.

We then dug into what an LMS actually *is*, what traditional LMS platforms get wrong (one-size-fits-all paths, completion-metric obsession, passive content, reactive support, no real personalization), and what AI-driven innovations the industry is racing toward:

- Adaptive learning paths (Absorb, Cornerstone, 360Learning)
- AI tutors & doubt resolution (PhysicsWallah's Alakh AI)
- Predictive analytics & early intervention (D2L Brightspace, upGrad)
- AI-assisted content creation (Intellum, Sana Learn)
- Skills intelligence & gap detection
- Gamification, accessibility, vernacular AI

The takeaway: **AI in LMS is no longer a differentiator — it's table stakes**. 99%+ of education leaders plan to deploy AI within 18 months. The interesting question wasn't "should AI be in the LMS" — it was "what AI problem is so specific to Sunstone that nobody else can solve it as well."

---

## 3. Step 2 — Sunstone Deep Dive

**Doc:** [`docs/02 sunstone deep dive.md`](./docs/02%20sunstone%20deep%20dive.md)

Next we narrowed from "EdTech industry" to "Sunstone specifically." We studied:

- **Business model** — the "Cloud College" pattern: Sunstone partners with existing colleges, handles admissions + academics + placements; the college handles infrastructure + accreditation
- **Three-pillar value prop** — Pay After Placement, industry-aligned curriculum, placement guarantee (1,200+ recruiters)
- **ELQD framework** — English, Logic, Quant, Domain — the four dimensions of Sunstone's parallel academic delivery
- **User segment** — 12th-pass or graduate students at partner colleges in Tier II/III cities; ~60–65% are first-generation corporate jobseekers
- **Current product** — the Sunstone mobile app, which on inspection turned out to be primarily **administrative** (timetable, attendance, fee payment, community) with **no evidence of adaptive learning, AI tutoring, learning analytics, or skill-gap intelligence**
- **Student reviews** — strong positive sentiment on placement and community; consistent complaints about inconsistent learning quality across campuses, slow management response, and broken admin coordination

We then built a confidence-rated pain point inventory — separating *confirmed* pain points (evidence from reviews and product gaps) from *hypothesized* ones (logical inferences from the program design).

The most important insight: Sunstone publicly claims "Leading Innovation in AI-Powered Learning" — but the actual product evidence does not back this up. There is a large, defensible gap between Sunstone's *intent* and Sunstone's *current product*, and that gap is the opportunity space.

---

## 4. Step 3 — Synthesis & Opportunity Mapping

**Doc:** [`docs/03 synthesis opportunity mapping.md`](./docs/03%20synthesis%20opportunity%20mapping.md)

We consolidated 10 pain points (P1–P10) from both the student and the operational perspective, then mapped each one to an opportunity space with an AI-leverage rating. The opportunities clustered into three problem areas:

**Cluster A: Placement Readiness Intelligence** (P1, P5, P7, P9) — students don't know where they stand vs. recruiter expectations; Sunstone doesn't know which students are at risk of not being placed.

**Cluster B: Personalized Learning Experience** (P2, P3, P4, P6) — every student goes through identical content at the same pace; no adaptive feedback.

**Cluster C: Campus Quality Standardization** (P8, P7) — learning outcomes vary widely across 20+ partner campuses.

We then scored each cluster on three dimensions on a 1–5 scale:

| Cluster | User Pain Severity | AI Leverage | Sunstone Strategic Fit | Total |
|---|---|---|---|---|
| **A: Placement Readiness Intelligence** | 5 | 5 | 5 | **15/15** |
| B: Personalized Learning Experience | 4 | 4 | 3 | 11/15 |
| C: Campus Quality Standardization | 3 | 3 | 4 | 10/15 |

**Cluster A scored 15/15** because it's the only cluster where all three dimensions hit maximum alignment. Pay After Placement is the entire financial and reputational core of Sunstone's business — an AI system that protects that promise is existential, not nice-to-have. AI uniquely adds value here because the connection between learning behavior, skill signals, and placement outcomes is exactly the kind of multi-variable pattern no human advisor can detect manually at the scale of 20,000+ students.

We chose Cluster A as the primary build, with hooks left for Cluster B as the natural Phase 2 follow-up.

---

## 5. Step 4 — The Problem Statement

**Doc:** [`docs/04 problem statement.md`](./docs/04%20problem%20statement.md)

This is where the spec crystallised into **PlacementIQ — an AI-Powered Placement Readiness Intelligence Suite** with three pillars:

- **Pillar A: Readiness Score Engine** — a real-time, AI-generated 0–100 placement readiness score, broken down across the four ELQD dimensions, benchmarked against the minimum threshold each career track's recruiters expect.
- **Pillar B: Skill Gap Intelligence Layer** — a radar chart of the student's skill profile vs. recruiter benchmarks, with an AI-generated "Top 3 Priority Gaps" list ranked by impact on placement probability.
- **Pillar C: Early Warning & Counselor Alert System** — a counselor-facing panel listing at-risk students with an AI-generated 3-line intervention brief. The system flags and recommends; the counselor decides and acts (human-in-the-loop).

We also defined three eval suites — Score Calibration, Gap Relevance, Early Warning Reliability — to validate the intelligence before claiming it works. These weren't optional; they were a core deliverable.

---

## 6. Architecture — Designing The System

**Doc:** [`docs/architecture.md`](./docs/architecture.md)

With the problem framed, the architecture made a small set of high-leverage decisions:

### 6.1 The Core Principle: Determinism in Numbers, LLM in Language

The most important architectural decision was the split between **deterministic logic** and **LLM-generated language**:

- **Numerical decisions** (the readiness score, gap rankings, at-risk flags) are computed by **pure Python functions** in `backend/app/core/`. They are reproducible, unit-testable, and exactly the same every time the same inputs go in.
- **Narrative outputs** (the gap rationale sentence, the 3-line intervention brief) are generated by a **live Claude API call** at request time.

This split exists because the three things a counselor or recruiter might dispute — "why is this score 67?", "why is this gap ranked #1?", "why is this student flagged?" — must be auditable and stable. We do not want a counselor to refresh the page and see a different score because the LLM sampled differently. At the same time, the narrative *around* those numbers is genuinely better when an LLM writes it, because it can synthesize multiple input signals into a single tight sentence in a way a template cannot.

A side benefit: because the deterministic engine carries all the load-bearing logic, our three evals test pure functions, not LLM behavior. They are stable, fast, and don't drift with model version changes.

### 6.2 The Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Vite + TypeScript + Tailwind | Mobile-first responsive; fast dev loop |
| Backend | FastAPI (Python 3.11+) | Typed routes, OpenAPI auto-docs, async for parallel LLM calls |
| AI | Anthropic Claude API (`claude-haiku-4-5`) | Sub-second latency, cheap, sufficient for 1–3 line text |
| Charts | Recharts | Lightweight radar chart, mobile-friendly |
| Data | JSON seed → in-memory dicts | Stateless prototype per spec |
| Hosting | Vercel (single project) | SPA + Python serverless function under one URL |

### 6.3 The Linear Model Decision

The scoring engine is a **hand-tuned linear model** — `0.6·assessments + 0.2·attendance + 0.2·time_on_task`, blended via per-track dimension weights. We deliberately did *not* train a model for the prototype because we had ~12 synthetic students and no outcome labels. A "trained" model on that data would only memorise the data generator's assumptions and look more impressive than it actually is. The Phase 2 roadmap documents the swap path to a logistic regression once real Sunstone outcome data is available — and the architecture is designed so the swap is a single-file change in `core/scoring.py`.

### 6.4 Explainability is Non-Negotiable

Every score, gap, and flag the system produces exposes the input signals that produced it. The UI surfaces both the deterministic signal and the LLM line so users see the full trail. No black-box outputs ever reach a student or counselor.

---

## 7. Implementation Plan — Ten Phases

**Doc:** [`docs/ImplementationPlan.md`](./docs/ImplementationPlan.md)

The build was sequenced horizontally — backend → frontend → evals → deploy — over ten phases totalling roughly 35 hours of focused work.

| Phase | Focus | Effort |
|---|---|---|
| 0 — Setup | Repo, tooling, scaffolds | 1h |
| 1 — Backend Foundations | Pydantic models, seed data, benchmark loader, boot-time validation | 3h |
| 2 — Core Engine | `scoring.py`, `gaps.py`, `at_risk.py` + unit tests | 5h |
| 3 — LLM Layer | Anthropic client with cache, timeout, fallback; two prompt templates | 2h |
| 4 — API Routes | FastAPI routes for student, counselor, evals + OpenAPI docs | 3h |
| 5 — Frontend Foundations | Routing, API client, auth context, layout | 2h |
| 6 — Student Dashboard | Login, readiness score card, ELQD radar, top 3 gaps | 5h |
| 7 — Counselor + Evals UI | At-risk table, intervention brief card, evals viewer | 4h |
| 8 — Evals System | 3 golden datasets, runner, committed results | 4h |
| 9 — Deployment | Single Vercel deploy: SPA at `/`, FastAPI at `/api/*` | 3h |
| 10 — Polish | README, Phase 2 roadmap doc, demo video, final cleanup | 3h |

As of writing this is at 97% complete — the engine, UI, evals, and deployment all live.

---

## 8. Where AI Sits In The Prototype Today

This is the part worth being explicit about, because at first glance a "hand-tuned linear model + Claude calls" prototype can look like it isn't really an AI product. It is — but in a very specific, defensible way. Here's the full picture:

### 8.1 The LLM does two narrative jobs

1. **Gap Rationale.** For each of the top 3 priority gaps shown to a student, Claude generates a single-sentence "why this matters" that cites a specific deterministic signal — the recruiter JD frequency for that sub-skill, or a recent mock interview rejection reason. The student sees both the number (`Data Interpretation — gap of 24 points, required in 73% of Analytics JDs`) and the LLM line tying it to their context.
2. **Intervention Brief.** For each at-risk student, Claude generates the 3-line counselor brief in the format specified in the problem statement: *Score → Primary gap + risk → Recent signal + recommended action*. The counselor reads it, decides whether to intervene, and marks the action taken.

Both prompts include a guard against instructions embedded in user-data fields, so a malicious student record can't subvert the LLM. The Anthropic client wrapper handles caching (same inputs return cached output, drastically reducing demo cost), an 8-second timeout, one-shot backoff on rate limits, and a deterministic templated fallback if the API call fails — so the demo never breaks because of LLM issues.

### 8.2 The "intelligence" is in the scoring engine, even though it isn't a neural net

The deterministic engine is a **linear model** — and a linear model is still machine learning, even when the weights are declared from domain knowledge instead of fitted from data. Specifically:

- `compute_readiness()` is a weighted blend of multiple signals (assessment scores, attendance, time-on-task) across multiple dimensions (E, L, Q, D), weighted differently per career track (BFSI vs. Analytics vs. Digital Marketing). That's a multi-feature regression problem; we're just declaring the coefficients from Sunstone's domain logic rather than fitting them from data we don't have.
- `top_n_gaps()` ranks gaps by `gap_size × dimension_weight` — a feature-importance ranking, applied to a per-student profile against a recruiter benchmark.
- `assess_at_risk()` combines a current-state signal (readiness score), a derivative signal (linear regression slope across the last 3 assessment cycles), and a time-window signal (days to placement) into a flag. That's a small ensemble.

The reason we chose this over a trained model — see Phase 2 below — is that you cannot honestly train a model on 12 synthetic students with no outcome labels. Any fitted model on that data would be curve-fitting the data generator. The hand-tuned model is the most rigorous, explainable, evaluable thing you can ship at prototype scale. And it is designed for the trained-model swap.

### 8.3 The evals are AI quality evaluation, done properly

The three eval suites — Score Calibration, Gap Relevance, Early Warning — are not unit tests. They are **dataset-driven quality evaluations**, the same discipline used in modern AI model validation:

- **Score Calibration** runs 10 golden student profiles with known outcome labels (placed / not placed) through the scoring engine and checks directional accuracy and sensitivity-to-input-change.
- **Gap Relevance** uses 5 manually-graded profiles where the "correct" top 3 gaps are pre-defined, then measures precision and ranking accuracy of the engine's output.
- **Early Warning** uses 8 trajectories (4 at-risk, 4 on-track) and measures recall and false-positive rate of the at-risk flagging.

These tests pass before deploy and are surfaced in the app at `/evals` for full transparency.

### 8.4 The full AI stack of the prototype, summarised

| Component | Type | What's "AI" About It |
|---|---|---|
| Readiness Score | Hand-tuned linear model | Multi-feature regression; per-track weight blending |
| Gap Ranking | Weighted feature scoring | Priority = gap × dimension importance |
| At-Risk Detection | Rule-based + trend regression | Slope across assessment cycles + multi-condition trigger |
| Gap Rationale | Live Claude Haiku call | Synthesises numerical signal into 1-sentence reasoning |
| Intervention Brief | Live Claude Haiku call | Synthesises at-risk signals into a 3-line counselor brief |
| Evals | Golden-dataset evaluations | Precision, recall, sensitivity — same discipline as ML model validation |

This is an AI product. It just happens to use the *right amount* of AI for the problem and data available — not more, not less.

---

## 9. How AI Expands In Phase 2

**Doc:** [`docs/phase-2-roadmap.md`](./docs/phase-2-roadmap.md)

Phase 2 is where the AI surface area grows significantly. The architecture was designed for exactly this — each AI layer below plugs into the existing engine without touching the rest of the system.

### 9.1 Trained scoring model (highest leverage)

Once Sunstone has real placed/not-placed outcome data for ~100+ students per track, the hand-tuned linear model in `core/scoring.py` gets swapped for a **logistic regression** trained on those labels. We chose logistic over gradient-boosted trees for the first version because:

- **Explainability stays cheap** — coefficients × feature values give a per-signal sentence, same shape as today's per-dimension breakdown
- **Calibration is well-understood** — logistic gives probabilities natively, which we already display as a 0–100 score
- **Sample-efficient** — works at the volumes Sunstone realistically has in year one

Gradient-boosted models (XGBoost / LightGBM) become worth it at ~500+ rows per track and stakeholder buy-in for SHAP-based explainability.

What stays the same: the API contracts, the LLM rationale layer, the frontend, **and especially the eval suite** — the existing score-calibration eval becomes the regression test that refuses to ship a trained model worse than the hand-tuned baseline.

### 9.2 Cluster B — adaptive content sequencing

Given a student's gaps + readiness trajectory, recommend the next module/exercise. Built on top of `top_n_gaps()`:

```
gap → mapping → curated module library → AI recommendation
```

The LLM picks among matched modules with rationale rather than free-generating recommendations — keeping content vetted.

### 9.3 Cluster B — AI doubt resolution

A chat surface where students ask questions about their dashboard ("why did my Quant score drop?", "what should I work on first?"). The system context is the same data the dashboard already shows — readiness, gaps, recent signals. One Claude call per turn, browser-held conversation state, the same prompt-injection guard as today's prompts, and every answer cites the deterministic signals it's grounded in.

### 9.4 Career-track recommender

Currently students declare their career track. Phase 2: an AI-suggested track from the student's ELQD profile. Two-step:

1. Deterministic: `best_track = argmax(sum(student.dim_score × track.weights[dim]))` per track
2. LLM: 2-sentence narrative explaining why, citing the contributing dimensions

### 9.5 Observability + safety

- **LLM cost/latency dashboard** — Redis-backed cache + per-route latency + cost-per-request metrics
- **Drift detection** — PSI / KS monitoring on the trained model's input distribution
- **Counselor feedback loop** — thumbs-up/down on intervention briefs, then train on the feedback once volume permits
- **Privacy-aware LLM routing** — Anthropic via AWS Bedrock or a self-hosted gateway for tenants with data-residency requirements

### 9.6 The shape of the Phase 2 AI stack

| Layer | Phase 1 (today) | Phase 2 |
|---|---|---|
| Scoring | Hand-tuned linear model | Trained logistic regression with calibration + drift monitoring |
| Gap Ranking | Weighted feature scoring | Same engine, fed by trained model outputs |
| At-Risk | Rule-based + trend regression | Probabilistic risk model with confidence intervals |
| Narrative | Live Claude (2 prompts) | Live Claude (4–6 prompts: rationale, brief, content rec, doubt resolution, track recommender) |
| Student-facing AI | Read-only dashboard | Conversational doubt-resolution + adaptive content |
| Eval discipline | 3 dataset-driven suites | Same 3 suites + trained-model regression tests + counselor feedback loop |

---

## 10. Closing — Why This Build Is Defensible

If someone glances at PlacementIQ and asks *"is this really an AI product?"*, the answer is yes — but the more interesting answer is *"it is the exact right amount of AI for the problem we framed and the data we had."*

We did not build a "GPT-wrapper" that calls Claude for everything and hopes the demo looks impressive. We did not pretend to train a neural network on 12 synthetic students. We built:

- A deterministic, auditable, explainable engine that does the load-bearing intelligence
- An LLM narrative layer that does what LLMs are genuinely best at — synthesizing numerical signals into human-readable language
- Three evaluation suites that prove the intelligence works on a golden dataset
- A Phase 2 roadmap that grows the AI surface area in the order that's both technically defensible and business-aligned (auth + DB → trained scoring → Cluster B)

The journey — industry research → company deep-dive → opportunity mapping → problem statement → architecture → implementation → evals — is what made this possible. We didn't start with "let's add AI to an LMS." We started with "what is the single most painful, AI-shaped problem in Sunstone's business," and then we built exactly that.

---

*Document map: [`01 edtech lms landscape.md`](./docs/01%20edtech%20lms%20landscape.md) → [`02 sunstone deep dive.md`](./docs/02%20sunstone%20deep%20dive.md) → [`03 synthesis opportunity mapping.md`](./docs/03%20synthesis%20opportunity%20mapping.md) → [`04 problem statement.md`](./docs/04%20problem%20statement.md) → [`architecture.md`](./docs/architecture.md) → [`ImplementationPlan.md`](./docs/ImplementationPlan.md) → [`phase-2-roadmap.md`](./docs/phase-2-roadmap.md)*
