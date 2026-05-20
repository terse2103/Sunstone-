"""Hand-tuned linear scoring model.

Pure functions over Student data and TrackBenchmark. No I/O, no LLM, no env reads
(Rules §Code/1). This is a linear model with *declared* weights:

    dimension_score = 0.6 * assessment_avg + 0.2 * attendance + 0.2 * time_pct
    overall         = sum(dim_score * track.weights[dim] for each dimension)

``assessment_avg`` is the mean of per-sub-skill averages within the dimension
(per architecture.md §4.2). Time-on-task hours are normalised against
``TIME_ON_TASK_CAP_HRS`` (25h) — this is the engagement ceiling that maps to 100.

We use declared weights rather than fitted ones because the prototype has no
outcome-labelled training data. With ~12 synthetic students a trained model
would only re-memorise the data generator. The function signature is designed
so the upgrade path — replacing constants with weights loaded from a fitted
estimator — is a single-file change. See ``docs/phase-2-roadmap.md``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.models import (
    Assessment,
    Dimension,
    DimensionScore,
    ReadinessResult,
    Student,
    TrackBenchmark,
)

# A pragmatic engagement ceiling: 25 hours per dimension over the assessment
# window saturates the time-on-task signal. Chosen to roughly match the upper
# range of on-track students in the seed (~20–28h). Keep as a constant so evals
# can reason about it.
TIME_ON_TASK_CAP_HRS = 25.0

DIMENSIONS: tuple[Dimension, ...] = ("E", "L", "Q", "D")

ASSESSMENT_WEIGHT = 0.6
ATTENDANCE_WEIGHT = 0.2
TIME_WEIGHT = 0.2


def compute_dimension_score(
    dimension: Dimension,
    assessment_scores_by_subskill: dict[str, list[float]],
    attendance_pct: float | None,
    time_on_task_hrs: float | None,
    benchmark: float = 0.0,
) -> DimensionScore:
    """Compute the 0–100 score for a single ELQD dimension.

    Inputs (all sourced from ``Student`` + ``TrackBenchmark`` by the caller):
    - ``assessment_scores_by_subskill``: every sub-skill that belongs to this
      dimension under the student's track, mapped to the list of cycle scores
      the student has. Sub-skills with no assessments must still appear with an
      empty list — they signal ``no_data:<subskill>`` per EdgeCases §1.2 / §1.4.
    - ``attendance_pct``: 0–100 attendance % for the dimension, or ``None`` if
      the student data has no entry for this dimension (EdgeCases §1.6).
    - ``time_on_task_hrs``: raw hours, or ``None`` if missing (EdgeCases §1.6).
    - ``benchmark``: mean of the dimension's sub-skill benchmarks (0–100). The
      frontend radar chart overlays this against ``score``.
    """
    signals: list[str] = []

    subskill_avgs: list[float] = []
    for subskill, scores in assessment_scores_by_subskill.items():
        if not scores:
            subskill_avgs.append(0.0)
            signals.append(f"no_data:{subskill}")
        else:
            subskill_avgs.append(sum(scores) / len(scores))

    assessment_avg = (
        sum(subskill_avgs) / len(subskill_avgs) if subskill_avgs else 0.0
    )

    # EdgeCases §1.6: missing attendance or time-on-task → assessment-only
    # contribution, capped at 60 (the natural ceiling of 0.6 * 100).
    if attendance_pct is None or time_on_task_hrs is None:
        if attendance_pct is None:
            signals.append(f"missing_signal:{dimension}:attendance")
        if time_on_task_hrs is None:
            signals.append(f"missing_signal:{dimension}:time_on_task")
        score = ASSESSMENT_WEIGHT * assessment_avg
        return DimensionScore(
            dimension=dimension,
            score=_clamp(score),
            benchmark=_clamp(benchmark),
            assessment_avg=_clamp(assessment_avg),
            attendance_pct=attendance_pct or 0.0,
            time_on_task_hrs=time_on_task_hrs or 0.0,
            signals=signals,
        )

    time_pct = min(time_on_task_hrs / TIME_ON_TASK_CAP_HRS, 1.0) * 100.0
    score = (
        ASSESSMENT_WEIGHT * assessment_avg
        + ATTENDANCE_WEIGHT * attendance_pct
        + TIME_WEIGHT * time_pct
    )
    return DimensionScore(
        dimension=dimension,
        score=_clamp(score),
        benchmark=_clamp(benchmark),
        assessment_avg=_clamp(assessment_avg),
        attendance_pct=attendance_pct,
        time_on_task_hrs=time_on_task_hrs,
        signals=signals,
    )


def compute_readiness(student: Student, track: TrackBenchmark) -> ReadinessResult:
    """Compute the full readiness picture for a student against their track."""
    grouped = _group_assessments_by_dimension(student.assessments, track)
    benchmarks = _dimension_benchmarks(track)

    dim_scores: list[DimensionScore] = []
    for dim in DIMENSIONS:
        scores_by_subskill = grouped.get(dim, {})
        dim_scores.append(
            compute_dimension_score(
                dimension=dim,
                assessment_scores_by_subskill=scores_by_subskill,
                attendance_pct=student.attendance_pct.get(dim),
                time_on_task_hrs=student.time_on_task_hrs.get(dim),
                benchmark=benchmarks[dim],
            )
        )

    overall = sum(ds.score * track.weights[ds.dimension] for ds in dim_scores)
    return ReadinessResult(
        student_id=student.id,
        track=track.name,
        overall=_clamp(overall),
        dimensions=dim_scores,
    )


def _group_assessments_by_dimension(
    assessments: Iterable[Assessment],
    track: TrackBenchmark,
) -> dict[Dimension, dict[str, list[float]]]:
    """Bucket assessment scores by dimension → sub-skill → [scores].

    Every sub-skill declared in the track appears in the output even with no
    student data, so the caller can emit the ``no_data:<subskill>`` signal.
    Sub-skills the student has scores for but which aren't in the track are
    ignored — the track is the source of truth for what counts.
    """
    out: dict[Dimension, dict[str, list[float]]] = {dim: {} for dim in DIMENSIONS}
    for subskill, bench in track.subskills.items():
        out[bench.dimension].setdefault(subskill, [])

    by_subskill: dict[str, list[float]] = defaultdict(list)
    for a in assessments:
        by_subskill[a.subskill].append(a.score)

    for subskill, bench in track.subskills.items():
        out[bench.dimension][subskill] = by_subskill.get(subskill, [])

    return out


def _dimension_benchmarks(track: TrackBenchmark) -> dict[Dimension, float]:
    """Mean of sub-skill benchmarks bucketed by dimension.

    Surfaced on ``DimensionScore.benchmark`` so the frontend radar chart can
    overlay the student's score against the track target without a separate
    benchmarks endpoint. Dimensions with no sub-skills (a degenerate seed)
    fall back to 0.0.
    """
    buckets: dict[Dimension, list[float]] = {dim: [] for dim in DIMENSIONS}
    for bench in track.subskills.values():
        buckets[bench.dimension].append(bench.benchmark)
    return {
        dim: (sum(values) / len(values)) if values else 0.0
        for dim, values in buckets.items()
    }


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))
