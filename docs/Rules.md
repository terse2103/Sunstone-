# PlacementIQ — Implementation Rules

Rules to follow during implementation. These exist to keep the architecture intact, the demo reliable, and progress visible. Not suggestions.

---

## Process Rules

1. **Update `To-doList.md` as you work.** Move tasks from `[ ]` to `[x]` immediately on completion — don't batch. Update the overall and per-phase progress percentages.
2. **Consult `EdgeCases.md` before implementing any module.** Each phase in `ImplementationPlan.md` lists relevant edge-case sections; verify handling for each before marking the phase complete.
3. **Don't deviate from `architecture.md` silently.** If implementation reveals a needed change, update `architecture.md` first, then code. Architecture is the contract.
4. **Don't expand scope.** If a task tempts a "while I'm here" refactor, stop. Note it for Phase 2 instead.
5. **Run `pytest backend/` after every change to `core/` or `models/`.** No commit with red tests.
6. **Run `python evals/run.py` after changes to `core/scoring.py`, `core/gaps.py`, or `core/at_risk.py`.** Investigate eval failures — never suppress.
7. **Verify mobile responsiveness after every frontend feature.** Use browser devtools at 360px width.

## Code Rules

1. **`core/` is pure.** No network, no I/O, no LLM, no env-var reads. Imports allowed: `models/`, stdlib only.
2. **`llm/` never imports `core/` or `routes/`.** Allowed imports: `models/`, Anthropic SDK, stdlib.
3. **`routes/` is thin.** Each route should be readable in ~20 lines — compose `core` + `llm` + `data`, return Pydantic models.
4. **All API responses are typed with Pydantic models.** No untyped dicts in route returns.
5. **All `core/` public functions have type hints and a short docstring** naming the inputs by source (e.g., "assessment scores from `Student.assessments`").
6. **No mocking the LLM in `core/` tests.** `core/` doesn't depend on the LLM; tests prove this by importing only `core` + `models`.
7. **LLM failures fall back deterministically.** Never let an LLM error bubble up as 500.
8. **Every narrative output cites a deterministic signal.** Frontend renders the signal alongside the LLM line.

## Data Rules

1. **Synthetic data only.** No real student names, IDs, or campus rosters. Names drawn from a diverse synthetic pool.
2. **Seed validation runs at boot.** `data/seed.py` validates schema, weight sums, and track references. Fail fast on bad data.
3. **`evals/datasets/` and `evals/results/` are version-controlled.** `report.json` is read by `/api/evals/results` in production, so it must be committed. `report.md` is the spec deliverable.

## Style Rules

1. **Default to no comments.** Add a comment only when the WHY is non-obvious. Don't restate what the code says.
2. **One module = one responsibility.** Split before files grow past ~150 lines.
3. **Use absolute imports** within the app package (e.g., `from app.core.scoring import ...`), not relative.
4. **Frontend components are functional, with hooks.** No class components.

## Git Rules

1. **Commit per completed sub-task.** Atomic, reversible commits.
2. **Commit message format:** `[P<phase>.<sub>] short imperative description` — e.g., `[P2.3] add gap ranking with priority score`.
3. **Never commit `.env`.** `.env.example` is committed; real `.env` is gitignored.
4. **Commit `evals/results/report.json` and `report.md`** after each successful eval run — the deployed app reads them.
5. **No `--no-verify` or hook skips.** If a pre-commit hook fails, fix the cause.

## Demo Rules

1. **Test the full demo flow after each phase that touches a user-facing path.**
2. **Demo flow:** Login as Student → view dashboard (score / radar / gaps) → logout → Login as Counselor → see at-risk list → open a brief → mark action → view `/evals` page.
3. **Document any rough edges in `EdgeCases.md` as you discover them.**

## When Something Breaks

1. **Test fails:** Investigate root cause; do not disable the test.
2. **Eval fails:** Investigate the engine; do not lower the threshold.
3. **Deployment breaks:** Roll back to last green commit; debug locally before re-deploying.
4. **Demo breaks:** Check fallback paths (LLM, missing data) — these should keep the demo running. If they don't, that's a bug.
