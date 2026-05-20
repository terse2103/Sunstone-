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
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.core.gaps import top_n_gaps
from app.core.scoring import compute_readiness
from app.models import (
    Assessment,
    AtRiskAssessment,
    Student,
    TrackBenchmark,
)
from app.models.at_risk import RiskLevel

READINESS_FLAG_THRESHOLD = 55.0
READINESS_HIGH_RISK_THRESHOLD = 45.0
PLACEMENT_WINDOW_MIN_DAYS = 60
RECENT_CYCLES_FOR_SLOPE = 3


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
        )

    slope, slope_signals = _trajectory_slope(student.assessments)

    in_placement_window = student.days_to_placement >= PLACEMENT_WINDOW_MIN_DAYS
    # None slope means insufficient data — treat as "not improving" per §1.1.
    non_improving = slope is None or slope <= 0
    below_threshold = overall < READINESS_FLAG_THRESHOLD
    flagged = below_threshold and non_improving and in_placement_window

    risk_level = _risk_level(overall)

    top = top_n_gaps(student, track, n=1)
    primary_gap = top[0] if top else None

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
    )


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
