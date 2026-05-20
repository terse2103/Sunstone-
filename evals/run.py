"""PlacementIQ — Evals Runner.

Runs the three eval suites required by the spec and architecture.md §7.1:

    1. Score Calibration — directional accuracy + sensitivity to a 15-pt input shift
    2. Gap Relevance     — top-3 precision with #1 always correct
    3. Early Warning     — recall over at-risk trajectories + false-positive cap

The runner imports app.core directly — no logic duplication. It writes
``evals/results/report.json`` (machine-readable, consumed by the in-app
/evals page) and ``evals/results/report.md`` (the human-readable spec
deliverable). Exit code reflects pass/fail so this slots into CI.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make app.* importable without requiring the user to set PYTHONPATH.
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from pydantic import ValidationError

from app.core.at_risk import assess_at_risk
from app.core.gaps import top_n_gaps
from app.core.scoring import compute_readiness
from app.data import seed
from app.models import Student, TrackBenchmark

DATASETS_DIR = Path(__file__).parent / "datasets"
RESULTS_DIR = Path(__file__).parent / "results"

# Thresholds derive from architecture.md §7.1.
SCORE_PLACED_THRESHOLD = 70.0
SCORE_NOT_PLACED_THRESHOLD = 50.0
SCORE_DIRECTIONAL_MIN_ACCURACY = 0.9
SCORE_SENSITIVITY_MIN_DELTA = 1.0

GAP_TOP_N = 3
GAP_FULL_MATCH_MIN_PROFILES = 4  # 3/3 match on ≥4 of 5
GAP_FIRST_CORRECT_MIN_PROFILES = 5  # #1 always correct

EARLY_WARNING_MIN_RECALL = 1.0  # 4/4 — non-negotiable per spec
EARLY_WARNING_MAX_FALSE_POSITIVES = 1


class DatasetError(RuntimeError):
    """Raised when a dataset file is missing or malformed (EdgeCases §8.2)."""


def main() -> int:
    seed.load()
    tracks = seed.BENCHMARKS

    suites = [
        run_score_calibration(tracks),
        run_gap_relevance(tracks),
        run_early_warning(tracks),
    ]

    overall_status = "pass" if all(s["status"] == "pass" for s in suites) else "fail"
    report = {
        "status": overall_status,
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "suites": suites,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (RESULTS_DIR / "report.md").write_text(render_markdown(report), encoding="utf-8")

    print(f"\nOverall status: {overall_status.upper()}")
    print(f"Wrote: {(RESULTS_DIR / 'report.json').relative_to(REPO_ROOT)}")
    print(f"Wrote: {(RESULTS_DIR / 'report.md').relative_to(REPO_ROOT)}")
    return 0 if overall_status == "pass" else 1


# ---------------------------------------------------------------------------
# Suite 1: Score Calibration
# ---------------------------------------------------------------------------

def run_score_calibration(tracks: dict[str, TrackBenchmark]) -> dict[str, Any]:
    raw = _load_dataset("score_calibration.json")
    case_inputs = _load_cases(raw, key="cases")
    sensitivity = raw.get("sensitivity_pair") or {}

    cases: list[dict[str, Any]] = []
    correct = 0
    overalls: dict[str, float] = {}

    for case in case_inputs:
        student = _build_student(case["student"])
        track = _track_for(student, tracks)
        label = case.get("label")
        if label not in {"placed", "not_placed", "borderline"}:
            raise DatasetError(
                f"score_calibration: case {case.get('id')!r} has invalid label {label!r}"
            )

        readiness = compute_readiness(student, track)
        actual_overall = round(readiness.overall, 2)
        overalls[case["id"]] = actual_overall
        predicted = _bucket_for_score(actual_overall)
        passed = predicted == label
        if passed:
            correct += 1

        cases.append(
            {
                "name": case["id"],
                "passed": passed,
                "expected": label,
                "actual": {"overall": actual_overall, "bucket": predicted},
                "note": case.get("note"),
            }
        )

    total_cases = len(case_inputs)
    directional_accuracy = correct / total_cases if total_cases else 0.0

    sens_delta: float | None = None
    sens_pass = True
    sens_required = float(
        sensitivity.get("min_overall_delta", SCORE_SENSITIVITY_MIN_DELTA)
    )
    if sensitivity:
        baseline_id = sensitivity.get("baseline_id")
        perturbed_id = sensitivity.get("perturbed_id")
        if baseline_id not in overalls or perturbed_id not in overalls:
            raise DatasetError(
                "score_calibration: sensitivity_pair references missing case id(s)"
            )
        sens_delta = round(overalls[perturbed_id] - overalls[baseline_id], 2)
        sens_pass = sens_delta >= sens_required
        cases.append(
            {
                "name": f"sensitivity[{baseline_id}→{perturbed_id}]",
                "passed": sens_pass,
                "expected": {
                    "min_overall_delta": sens_required,
                    "perturbation": sensitivity.get("note", ""),
                },
                "actual": {"overall_delta": sens_delta},
                "note": sensitivity.get("note"),
            }
        )

    suite_pass = (
        directional_accuracy >= SCORE_DIRECTIONAL_MIN_ACCURACY and sens_pass
    )
    metrics: dict[str, float] = {
        "directional_accuracy": round(directional_accuracy, 3),
        "correct": float(correct),
        "total": float(total_cases),
        "min_accuracy": SCORE_DIRECTIONAL_MIN_ACCURACY,
    }
    if sens_delta is not None:
        metrics["sensitivity_delta"] = sens_delta
        metrics["sensitivity_min_delta"] = sens_required

    return {
        "name": "score_calibration",
        "status": "pass" if suite_pass else "fail",
        "metrics": metrics,
        "cases": cases,
    }


def _bucket_for_score(overall: float) -> str:
    if overall > SCORE_PLACED_THRESHOLD:
        return "placed"
    if overall < SCORE_NOT_PLACED_THRESHOLD:
        return "not_placed"
    return "borderline"


# ---------------------------------------------------------------------------
# Suite 2: Gap Relevance
# ---------------------------------------------------------------------------

def run_gap_relevance(tracks: dict[str, TrackBenchmark]) -> dict[str, Any]:
    raw = _load_dataset("gap_relevance.json")
    case_inputs = _load_cases(raw, key="cases")

    cases: list[dict[str, Any]] = []
    full_matches = 0
    first_correct = 0

    for case in case_inputs:
        student = _build_student(case["student"])
        track = _track_for(student, tracks)
        expected = list(case.get("expected_top3") or [])
        if len(expected) != GAP_TOP_N:
            raise DatasetError(
                f"gap_relevance: case {case.get('id')!r} expected_top3 must have {GAP_TOP_N} entries"
            )

        actual_gaps = top_n_gaps(student, track, n=GAP_TOP_N)
        actual = [g.subskill for g in actual_gaps]

        set_match = set(actual) == set(expected)
        head_match = bool(actual and actual[0] == expected[0])
        if set_match:
            full_matches += 1
        if head_match:
            first_correct += 1

        cases.append(
            {
                "name": case["id"],
                "passed": set_match and head_match,
                "expected": expected,
                "actual": actual,
                "note": case.get("note"),
            }
        )

    total = len(case_inputs)
    suite_pass = (
        full_matches >= GAP_FULL_MATCH_MIN_PROFILES
        and first_correct >= GAP_FIRST_CORRECT_MIN_PROFILES
    )
    return {
        "name": "gap_relevance",
        "status": "pass" if suite_pass else "fail",
        "metrics": {
            "profiles_full_match": float(full_matches),
            "profiles_first_correct": float(first_correct),
            "profiles_total": float(total),
            "full_match_required": float(GAP_FULL_MATCH_MIN_PROFILES),
            "first_correct_required": float(GAP_FIRST_CORRECT_MIN_PROFILES),
        },
        "cases": cases,
    }


# ---------------------------------------------------------------------------
# Suite 3: Early Warning
# ---------------------------------------------------------------------------

def run_early_warning(tracks: dict[str, TrackBenchmark]) -> dict[str, Any]:
    raw = _load_dataset("early_warning.json")
    case_inputs = _load_cases(raw, key="cases")

    cases: list[dict[str, Any]] = []
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    total_at_risk = 0

    for case in case_inputs:
        student = _build_student(case["student"])
        track = _track_for(student, tracks)
        expected = bool(case.get("expected_at_risk"))

        assessment = assess_at_risk(student, track)
        actual = assessment.flagged

        if expected:
            total_at_risk += 1
        if expected and actual:
            true_positives += 1
        elif expected and not actual:
            false_negatives += 1
        elif not expected and actual:
            false_positives += 1

        cases.append(
            {
                "name": case["id"],
                "passed": expected == actual,
                "expected": {"at_risk": expected},
                "actual": {
                    "at_risk": actual,
                    "readiness": round(assessment.readiness, 2),
                    "trajectory_slope": (
                        None
                        if assessment.trajectory_slope is None
                        else round(assessment.trajectory_slope, 3)
                    ),
                    "days_to_placement": assessment.days_to_placement,
                    "risk_level": assessment.risk_level,
                },
                "note": case.get("note"),
            }
        )

    recall = (true_positives / total_at_risk) if total_at_risk else 0.0
    not_at_risk_total = len(case_inputs) - total_at_risk
    fp_rate = (false_positives / not_at_risk_total) if not_at_risk_total else 0.0

    suite_pass = (
        recall >= EARLY_WARNING_MIN_RECALL
        and false_positives <= EARLY_WARNING_MAX_FALSE_POSITIVES
    )
    return {
        "name": "early_warning",
        "status": "pass" if suite_pass else "fail",
        "metrics": {
            "recall": round(recall, 3),
            "true_positives": float(true_positives),
            "false_negatives": float(false_negatives),
            "false_positives": float(false_positives),
            "false_positive_rate": round(fp_rate, 3),
            "min_recall": EARLY_WARNING_MIN_RECALL,
            "max_false_positives": float(EARLY_WARNING_MAX_FALSE_POSITIVES),
        },
        "cases": cases,
    }


# ---------------------------------------------------------------------------
# Dataset loading helpers (fail fast per EdgeCases §8.2)
# ---------------------------------------------------------------------------

def _load_dataset(filename: str) -> dict[str, Any]:
    path = DATASETS_DIR / filename
    if not path.exists():
        raise DatasetError(f"dataset missing: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetError(f"{path}: invalid JSON — {exc}") from exc
    if not isinstance(raw, dict):
        raise DatasetError(f"{path}: top-level must be an object")
    return raw


def _load_cases(raw: dict[str, Any], *, key: str) -> list[dict[str, Any]]:
    cases = raw.get(key)
    if not isinstance(cases, list) or not cases:
        raise DatasetError(f"dataset has no non-empty {key!r} list")
    for case in cases:
        if not isinstance(case, dict) or "student" not in case or "id" not in case:
            raise DatasetError(f"case missing required fields (id/student): {case!r}")
    return cases


def _build_student(payload: dict[str, Any]) -> Student:
    try:
        return Student(**payload)
    except ValidationError as exc:
        raise DatasetError(
            f"student {payload.get('id', '?')!r} failed schema: {exc}"
        ) from exc


def _track_for(student: Student, tracks: dict[str, TrackBenchmark]) -> TrackBenchmark:
    if student.career_track not in tracks:
        raise DatasetError(
            f"student {student.id!r} references unknown track {student.career_track!r}"
        )
    return tracks[student.career_track]


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    overall = report["status"].upper()
    lines.append("# PlacementIQ — Evals Report")
    lines.append("")
    lines.append(f"**Overall:** {_badge(report['status'])} **{overall}**  ")
    lines.append(f"**Ran at:** {report['ran_at']}")
    lines.append("")
    lines.append("| Suite | Status | Key metrics |")
    lines.append("|---|---|---|")
    for suite in report["suites"]:
        lines.append(
            f"| {suite['name']} | {_badge(suite['status'])} {suite['status']} "
            f"| {_summary_metrics(suite)} |"
        )
    lines.append("")

    for suite in report["suites"]:
        lines.append(f"## {suite['name']} — {_badge(suite['status'])} {suite['status']}")
        lines.append("")
        if suite["metrics"]:
            lines.append("| Metric | Value |")
            lines.append("|---|---|")
            for metric_name, value in suite["metrics"].items():
                lines.append(f"| {metric_name} | {_fmt_metric(value)} |")
            lines.append("")

        failed = [c for c in suite["cases"] if not c["passed"]]
        if failed:
            lines.append("### Failed cases")
            lines.append("")
            for case in failed:
                lines.append(f"- **{case['name']}**")
                if case.get("note"):
                    lines.append(f"  - note: {case['note']}")
                lines.append(f"  - expected: `{_fmt_value(case.get('expected'))}`")
                lines.append(f"  - actual: `{_fmt_value(case.get('actual'))}`")
            lines.append("")

        lines.append("<details><summary>All cases</summary>")
        lines.append("")
        lines.append("| Case | Result | Expected | Actual | Note |")
        lines.append("|---|---|---|---|---|")
        for case in suite["cases"]:
            lines.append(
                "| {name} | {result} | `{expected}` | `{actual}` | {note} |".format(
                    name=case["name"],
                    result="✅ pass" if case["passed"] else "❌ fail",
                    expected=_fmt_value(case.get("expected")),
                    actual=_fmt_value(case.get("actual")),
                    note=(case.get("note") or "").replace("|", "\\|"),
                )
            )
        lines.append("")
        lines.append("</details>")
        lines.append("")
    return "\n".join(lines) + "\n"


def _badge(status: str) -> str:
    return {"pass": "🟢", "fail": "🔴", "not_run": "⚪"}.get(status, "•")


def _summary_metrics(suite: dict[str, Any]) -> str:
    metrics = suite["metrics"]
    if suite["name"] == "score_calibration":
        return (
            f"accuracy {metrics['directional_accuracy']:.2f}"
            f" (≥ {metrics['min_accuracy']}), "
            f"sensitivity Δ {metrics.get('sensitivity_delta', 0):.2f}"
            f" (≥ {metrics.get('sensitivity_min_delta', 0)})"
        )
    if suite["name"] == "gap_relevance":
        return (
            f"full-match {int(metrics['profiles_full_match'])}/"
            f"{int(metrics['profiles_total'])}, "
            f"#1 correct {int(metrics['profiles_first_correct'])}/"
            f"{int(metrics['profiles_total'])}"
        )
    if suite["name"] == "early_warning":
        return (
            f"recall {metrics['recall']:.2f}, "
            f"false positives {int(metrics['false_positives'])}"
            f" (≤ {int(metrics['max_false_positives'])})"
        )
    return ""


def _fmt_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".") if value % 1 else f"{int(value)}"
    return str(value)


def _fmt_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(", ", ": "))
    return str(value)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DatasetError as exc:
        print(f"DATASET ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
