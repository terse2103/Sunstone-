# The "PlacementIQ — Student Readiness Intelligence Suite"

---

## 1. Project Vision

Sunstone Edtech's core promise to its students is simple: get placed in a corporate job, or don't pay. Yet today, a Sunstone student — often a first-generation corporate aspirant from a Tier II or III city — has no real-time visibility into whether they are actually on track to be placed. Skill gaps are discovered at placement season, not 6 months before it. By the time the gap is visible, there is no time to close it.

**PlacementIQ** is an AI-powered Placement Readiness Intelligence Suite that solves this. It is a unified, student-facing and counselor-facing dashboard that continuously tracks each student's placement readiness across Sunstone's ELQD framework (English, Logic, Quant, Domain), benchmarks it against real recruiter expectations, and surfaces gaps early enough to act on.

This is not a reporting tool. It is an early intervention system — built for students who don't yet know what "placement-ready" looks like, and for counselors who cannot manually track 20,000+ students across 20+ campuses.

**Who it is built for:**
- **Primary User:** Sunstone students (12th pass → UG, or Graduate → PG) enrolled at partner colleges
- **Secondary User:** Sunstone placement counselors and academic coordinators

---

## 2. The Product Architecture

PlacementIQ is a single integrated dashboard featuring three interconnected pillars:

---

### Pillar A: The Readiness Score Engine

- **What it does:** Computes a real-time, AI-generated **Placement Readiness Score (0–100)** for each student, broken down across the four ELQD dimensions (English, Logic, Quant, Domain).
- **The Feature:** A student logs into the dashboard and sees their overall readiness score alongside a per-dimension breakdown. Each dimension score is benchmarked against the **minimum threshold required by Sunstone's recruiter network** for their chosen career track (e.g., BFSI, Digital Marketing, Analytics).
  - *Example: "Your Domain score is 61/100. Recruiters in Analytics typically expect 75+. You have a 14-point gap with 4 months to placement season."*
- **The Intelligence Layer:** The score is not static. It updates based on assessment results, attendance signals, assignment submissions, and time-on-task data. A student who completes a module and scores well sees their score improve in real time.
- **Constraint:** The score must always show its component inputs transparently — students must be able to see *why* their score is what it is, not just the number.

---

### Pillar B: The Skill Gap Intelligence Layer

- **What it does:** Translates the readiness score into a **prioritized gap map** — a visual breakdown of which specific skills the student is weak in, ranked by how much each gap affects their probability of placement.
- **The Feature:** A radar/spider chart showing the student's current skill profile vs. the recruiter benchmark for their target career track. Below the chart, an AI-generated **"Top 3 Priority Gaps"** list tells the student exactly what to focus on this month.
  - *Example: "1. Business Communication (English) — Gap: High. Most common rejection reason in mock interviews. 2. Data Interpretation (Quant) — Gap: Medium. Required in 73% of Analytics JDs. 3. Financial Modelling Basics (Domain) — Gap: Medium."*
- **The Integration:** Gap priorities are dynamically re-ranked as the student's score changes (from Pillar A), and as recruiter demand data is refreshed.
- **Constraint:** Every gap recommendation must cite its source signal — assessment score, attendance record, or recruiter JD data — so the student trusts the output.

---

### Pillar C: The Early Warning & Counselor Alert System

- **What it does:** Identifies students who are **at risk of not being placed** at their current trajectory — and surfaces them to placement counselors with enough lead time to intervene.
- **The Feature:** A counselor-facing panel that lists at-risk students, their current readiness score, the primary gap driving their risk, and an AI-generated **intervention brief** — a 3-line context note the counselor can read before reaching out.
  - *Example: "Priya Sharma — Score: 44/100 — Risk: High. Primary gap: English (score: 38). Has not attended 3 of the last 5 Communication sessions. Recommended action: 1:1 check-in + remedial content assignment."*
- **The Human-in-the-Loop:** The system flags and recommends; it does not auto-message students. The counselor reviews the brief, decides on the intervention, and marks the action taken. This keeps a human accountable for every at-risk student interaction.
- **Constraint:** At-risk flags must trigger with a minimum of **60 days before placement season** to ensure interventions are meaningful, not cosmetic.

---

## 3. Performance & Quality Evals

Because this system influences real student outcomes and counselor decisions, we cannot guess if it works. An Evaluation Suite is required to validate the core intelligence before deployment.

---

### Score Calibration Eval (Readiness Score Eval)
- Build a **Simulated Golden Dataset** of 10 student profiles with known outcome labels (placed / not placed) based on realistic ELQD score distributions and attendance patterns.
- **Metric — Directional Accuracy:** Does a student with a score below 50 consistently land in the "not placed" bucket and above 70 in the "placed" bucket? Measure the score's directional reliability across all 10 profiles.
- **Metric — Sensitivity to Change:** If a student improves their Domain assessment score by 15 points, does the overall readiness score update meaningfully within the same session?

---

### Gap Relevance Eval (Recommendation Quality Eval)
- Create 5 student gap profiles and manually define what the correct Top 3 Priority Gaps *should* be for each, based on recruiter JD data.
- **Metric — Precision:** What % of the AI-generated Top 3 gaps match the manually defined ground truth? Target: 3/3 match on at least 4 of 5 profiles.
- **Metric — Ranking Accuracy:** Is the highest-priority gap always ranked #1? A correctly identified but mis-ranked gap is a partial failure.

---

### Early Warning Reliability Eval (At-Risk Detection Eval)
- Simulate 8 student trajectories: 4 students who are genuinely at risk (low scores, poor attendance, declining trend) and 4 who are on track.
- **Metric — Recall:** Does the system flag all 4 at-risk students? Missing a genuinely at-risk student is the worst failure mode. Target: 4/4 flagged.
- **Metric — Precision:** Does the system avoid false positives (flagging on-track students as at-risk)? Target: no more than 1 false positive across 4 on-track profiles.

---

## 4. Technical Constraints

- **Single Entry Point:** One unified dashboard UI with role-based views — student view (Pillars A + B) and counselor view (Pillar C). Login role determines what is shown.
- **Simulated Data Only:** No real student PII is used in the prototype. All student profiles are synthetically generated. Use `[STUDENT_ID]` format for any student identifiers.
- **Score Explainability:** Every AI-generated score, gap, or flag must surface its input signals. Black-box outputs are not acceptable in a system that affects student careers.
- **Mobile-Responsive UI:** Sunstone students are mobile-first. The student-facing view (Pillars A + B) must be fully functional on a mobile viewport.
- **Stateless Prototype:** For the prototype, data can be hardcoded or seeded from a JSON file. No live database integration is required.

---

## 5. Deliverables

- **GitHub Repository** with clean folder structure, README, and setup instructions.
- **PlacementIQ Demo** — a walkthrough showing:
  - A student logging in and viewing their Readiness Score with ELQD breakdown (Pillar A)
  - The Skill Gap radar chart with AI-generated Top 3 Priority Gaps (Pillar B)
  - A counselor viewing the at-risk panel and reading an AI-generated intervention brief for a flagged student (Pillar C)
- **Evals Report** — a Markdown file documenting:
  - The 10-profile Golden Dataset used for Score Calibration
  - The 5-profile Gap Relevance test and precision scores
  - The 8-trajectory Early Warning test with recall and precision results
- **Phase 2 Roadmap Note** — a brief section outlining how Cluster B (Personalized Learning Experience: adaptive content, doubt resolution) connects to this foundation as the natural next build.

---

*Research trail: `01_edtech_lms_landscape.md` → `02_sunstone_deep_dive.md` → `03_synthesis_opportunity_mapping.md` → this document*