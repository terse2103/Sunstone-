"""At-risk flagging.

Combines the deterministic readiness score with a linear-regression trajectory
slope over the last 3 assessment cycles to decide whether a student should be
flagged for counselor intervention.

Rule (architecture §4.2):
    flagged = readiness < 55 AND trajectory_slope <= 0 AND days_to_placement >= 60

Risk level (always reported even when not flagged):
    high   if readiness < 45
    medium if 45 <= readiness < 55
    low    if readiness >= 55
    unknown if the student has no assessment history (EdgeCases §4.4)

The assessment also carries pre-computed signals that drive the intervention
brief + UI:
    - primary_lever: assessment_scores / attendance / time_on_task — the
      single biggest weighted shortfall on the primary-gap dimension.
    - trajectory_outlook: where the current slope is taking them vs the
      55-point threshold and the placement window.
    - top_struggling_subskills: top 3 priority-ranked sub-skill names.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.core.gaps import compute_gaps
from app.core.scoring import TIME_ON_TASK_CAP_HRS, compute_readiness
from app.models import (
    Assessment,
    AtRiskAssessment,
    DimensionScore,
    Student,
    TrackBenchmark,
)
from app.models.at_risk import PrimaryLever, RiskLevel, TrajectoryOutlook

READINESS_FLAG_THRESHOLD = 55.0
READINESS_HIGH_RISK_THRESHOLD = 45.0
PLACEMENT_WINDOW_MIN_DAYS = 60
RECENT_CYCLES_FOR_SLOPE = 3

# Rough working assumption for projecting "will the current slope reach 55
# before placement?". Assessment cycles aren't tied to wall-clock days in the
# data model, but a ~30-day cadence is consistent with the typical placement
# preparation pulse and lets us turn `days_to_placement` into "cycles left".
ASSUMED_CYCLE_DAYS = 30

TOP_STRUGGLING_N = 3

_DIMENSION_LABELS = {"E": "English", "L": "Logic", "Q": "Quant", "D": "Domain"}


def assess_at_risk(student: Student, track: TrackBenchmark) -> AtRiskAssessment:
    """Score the student, derive trajectory, return the at-risk decision."""
    readiness = compute_readiness(student, track)
    overall = readiness.overall

    # EdgeCases §4.4: no assessment history → cannot assess; never flagged.
    if not student.assessments:
        return AtRiskAssessment(
            student_id=student.id,
            risk_level="unknown",
            flagged=False,
            readiness=overall,
            trajectory_slope=None,
            days_to_placement=student.days_to_placement,
            primary_gap=None,
            contributing_signals=["newly_enrolled"],
            primary_lever=None,
            trajectory_outlook="unknown",
            top_struggling_subskills=[],
            severity_ranked_dimensions=[],
        )

    slope, slope_signals = _trajectory_slope(student.assessments)

    in_placement_window = student.days_to_placement >= PLACEMENT_WINDOW_MIN_DAYS
    # None slope means insufficient data — treat as "not improving" per §1.1.
    non_improving = slope is None or slope <= 0
    below_threshold = overall < READINESS_FLAG_THRESHOLD
    flagged = below_threshold and non_improving and in_placement_window

    risk_level = _risk_level(overall)

    all_gaps = compute_gaps(student, track)
    primary_gap = all_gaps[0] if all_gaps else None
    top_struggling_subskills = [g.subskill for g in all_gaps[:TOP_STRUGGLING_N]]

    seen_dims: list[str] = []
    for g in all_gaps:
        if g.dimension not in seen_dims:
            seen_dims.append(g.dimension)
    severity_ranked_dimensions = [_DIMENSION_LABELS[d] for d in seen_dims]

    primary_lever = _primary_lever(readiness.dimensions, primary_gap)
    trajectory_outlook = _trajectory_outlook(
        readiness=overall,
        slope=slope,
        days_to_placement=student.days_to_placement,
    )

    contributing: list[str] = list(slope_signals)
    if below_threshold:
        contributing.append(f"readiness_below_55:{overall:.1f}")
    if slope is not None and slope <= 0:
        contributing.append(f"flat_or_declining_trajectory:slope={slope:.2f}")
    if in_placement_window:
        contributing.append(f"placement_window:{student.days_to_placement}d")
    contributing.extend(student.recent_signals)

    return AtRiskAssessment(
        student_id=student.id,
        risk_level=risk_level,
        flagged=flagged,
        readiness=overall,
        trajectory_slope=slope,
        days_to_placement=student.days_to_placement,
        primary_gap=primary_gap,
        contributing_signals=contributing,
        primary_lever=primary_lever,
        trajectory_outlook=trajectory_outlook,
        top_struggling_subskills=top_struggling_subskills,
        severity_ranked_dimensions=severity_ranked_dimensions,
    )


def _primary_lever(
    dimensions: list[DimensionScore],
    primary_gap,
) -> PrimaryLever | None:
    """Of the three signals that feed the primary gap's dimension score
    (assessment_avg, attendance, time_on_task), return whichever has the
    biggest weighted shortfall — i.e. the lever a counselor should attack
    first to move that dimension's score.

    Weights mirror ``compute_dimension_score``: 0.6 / 0.2 / 0.2.
    Returns ``None`` when there's no primary gap to anchor on.
    """
    if primary_gap is None:
        return None
    dim_score = next(
        (d for d in dimensions if d.dimension == primary_gap.dimension), None
    )
    if dim_score is None:
        return None

    time_pct = min(dim_score.time_on_task_hrs / TIME_ON_TASK_CAP_HRS, 1.0) * 100.0
    rooms = {
        "assessment_scores": 0.6 * (100.0 - dim_score.assessment_avg),
        "attendance": 0.2 * (100.0 - dim_score.attendance_pct),
        "time_on_task": 0.2 * (100.0 - time_pct),
    }
    # Deterministic tiebreak: assessment > attendance > time_on_task — matches
    # the 60/20/20 weighting in the score formula.
    order = ("assessment_scores", "attendance", "time_on_task")
    return max(order, key=lambda k: rooms[k])  # type: ignore[return-value]


def _trajectory_outlook(
    *,
    readiness: float,
    slope: float | None,
    days_to_placement: int,
) -> TrajectoryOutlook:
    """Where the current slope would land the student against the readiness
    threshold by the placement deadline.

    Projection assumes one assessment cycle ≈ ``ASSUMED_CYCLE_DAYS`` days
    (see module docstring) — this is a working heuristic for the prototype,
    not a guarantee. The model exposes this as a coded value so the LLM
    prompt can phrase it consistently across runs.
    """
    if slope is None:
        return "unknown"
    if readiness >= READINESS_FLAG_THRESHOLD:
        return "on_track_above"
    if slope < 0:
        return "declining"
    if slope == 0:
        return "flat_below"
    # slope > 0
    cycles_remaining = max(1, days_to_placement // ASSUMED_CYCLE_DAYS)
    projected = readiness + slope * cycles_remaining
    if projected >= READINESS_FLAG_THRESHOLD:
        return "improving_in_reach"
    return "improving_too_slow"


def _risk_level(readiness: float) -> RiskLevel:
    if readiness < READINESS_HIGH_RISK_THRESHOLD:
        return "high"
    if readiness < READINESS_FLAG_THRESHOLD:
        return "medium"
    return "low"


def _trajectory_slope(
    assessments: Iterable[Assessment],
) -> tuple[float | None, list[str]]:
    """Linear regression slope over the last 3 cycles' average scores.

    Returns ``(slope, signals)``. Slope is ``None`` when fewer than 2 cycles
    are available — EdgeCases §1.1 / §2.3 require us to flag this in signals
    and let the caller treat None as non-improving.
    """
    by_cycle: dict[int, list[float]] = defaultdict(list)
    for a in assessments:
        by_cycle[a.cycle].append(a.score)

    cycle_avgs = sorted(
        ((cycle, sum(scores) / len(scores)) for cycle, scores in by_cycle.items()),
        key=lambda item: item[0],
    )[-RECENT_CYCLES_FOR_SLOPE:]

    if len(cycle_avgs) < 2:
        return None, ["insufficient_trajectory_data"]

    signals: list[str] = []
    if len(cycle_avgs) < RECENT_CYCLES_FOR_SLOPE:
        signals.append("insufficient_trajectory_data")

    xs = [c for c, _ in cycle_avgs]
    ys = [v for _, v in cycle_avgs]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    # Cycle numbers are distinct integers, so den is always > 0 here.
    slope = num / den
    return slope, signals
