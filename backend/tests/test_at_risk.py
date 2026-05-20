"""Unit tests for core/at_risk.py.

These exercise the at-risk decision rule and every boundary in EdgeCases §4
plus the trajectory-slope edge cases in §1.1 and §2.3.
"""

from __future__ import annotations

import pytest

from app.core.at_risk import assess_at_risk
from app.models import (
    Assessment,
    Dimension,
    Student,
    SubSkillBenchmark,
    TrackBenchmark,
)


def _track(
    *,
    weights: dict[Dimension, float] | None = None,
    subskills: dict[str, tuple[Dimension, float]] | None = None,
) -> TrackBenchmark:
    return TrackBenchmark(
        name="TestTrack",
        weights=weights or {"E": 0.25, "L": 0.25, "Q": 0.25, "D": 0.25},
        subskills={
            name: SubSkillBenchmark(dimension=dim, benchmark=bench)
            for name, (dim, bench) in (
                subskills
                or {
                    "english_basic": ("E", 80),
                    "logic_basic": ("L", 80),
                    "quant_basic": ("Q", 80),
                    "domain_basic": ("D", 80),
                }
            ).items()
        },
    )


def _student(
    *,
    cycles_per_subskill: dict[str, list[float]] | None = None,
    attendance: float = 80,
    time_on_task_hrs: float = 20,
    days_to_placement: int = 120,
    recent_signals: list[str] | None = None,
) -> Student:
    """Build a uniform student: same attendance / time for every dimension."""
    assessments: list[Assessment] = []
    for subskill, scores in (cycles_per_subskill or {}).items():
        for i, s in enumerate(scores, start=1):
            assessments.append(Assessment(subskill=subskill, score=s, cycle=i))
    return Student(
        id="STU_A",
        name="Test Student",
        program="MBA",
        campus="Pune",
        career_track="TestTrack",
        days_to_placement=days_to_placement,
        assessments=assessments,
        attendance_pct={"E": attendance, "L": attendance, "Q": attendance, "D": attendance},
        time_on_task_hrs={
            "E": time_on_task_hrs,
            "L": time_on_task_hrs,
            "Q": time_on_task_hrs,
            "D": time_on_task_hrs,
        },
        recent_signals=recent_signals or [],
    )


def _uniform_cycles(scores: list[float]) -> dict[str, list[float]]:
    """One sub-skill per dimension, all with the same cycle sequence."""
    return {
        "english_basic": list(scores),
        "logic_basic": list(scores),
        "quant_basic": list(scores),
        "domain_basic": list(scores),
    }


# --- newly enrolled (§4.4) --------------------------------------------------


def test_newly_enrolled_returns_unknown_not_flagged() -> None:
    """EdgeCases §4.4: no assessments → risk_level=unknown, never flagged."""
    track = _track()
    s = _student(cycles_per_subskill={}, days_to_placement=200)
    out = assess_at_risk(s, track)
    assert out.risk_level == "unknown"
    assert out.flagged is False
    assert out.trajectory_slope is None
    assert "newly_enrolled" in out.contributing_signals
    assert out.primary_gap is None


# --- readiness boundary (§4.1) ----------------------------------------------


def test_readiness_exactly_55_not_flagged() -> None:
    """EdgeCases §4.1: rule is strict ``< 55``. Equal-to-55 is NOT flagged."""
    track = _track()
    # cycles [60,55,50] per dim → assess_avg = 55. Combined with attendance=55
    # and time_on_task=13.75h (55% of the 25h cap) → dim_score = 0.6*55 +
    # 0.2*55 + 0.2*55 = 55. Track weights are uniform → overall = 55 exactly.
    s = _student(
        cycles_per_subskill=_uniform_cycles([60, 55, 50]),
        attendance=55,
        time_on_task_hrs=13.75,
    )
    out = assess_at_risk(s, track)
    assert out.readiness == pytest.approx(55.0)
    assert out.trajectory_slope is not None and out.trajectory_slope < 0  # declining
    assert out.days_to_placement >= 60
    assert out.flagged is False  # 55 is NOT below the threshold
    assert out.risk_level == "low"  # 55 >= 55 → low (not medium)


# --- slope boundary (§4.2) --------------------------------------------------


def test_slope_exactly_zero_still_flag_eligible() -> None:
    """EdgeCases §4.2: slope == 0 counts as non-improving."""
    track = _track()
    # Flat trajectory at 50 → slope == 0. Readiness will be < 55.
    s = _student(
        cycles_per_subskill=_uniform_cycles([50, 50, 50]),
        attendance=55,
        time_on_task_hrs=13.75,  # 55%
    )
    out = assess_at_risk(s, track)
    assert out.trajectory_slope == pytest.approx(0.0)
    assert out.readiness < 55
    assert out.flagged is True


# --- days_to_placement boundary (§4.3) --------------------------------------


def test_days_to_placement_exactly_60_eligible() -> None:
    """EdgeCases §4.3: rule is ``days_to_placement >= 60``."""
    track = _track()
    s = _student(
        cycles_per_subskill=_uniform_cycles([55, 50, 50]),
        attendance=55,
        time_on_task_hrs=13.75,
        days_to_placement=60,
    )
    out = assess_at_risk(s, track)
    assert out.readiness < 55
    assert out.flagged is True


def test_days_to_placement_below_60_not_flagged() -> None:
    """``days_to_placement = 59`` is below the floor → never flagged."""
    track = _track()
    s = _student(
        cycles_per_subskill=_uniform_cycles([40, 35, 30]),  # very low + declining
        attendance=40,
        time_on_task_hrs=5,
        days_to_placement=59,
    )
    out = assess_at_risk(s, track)
    assert out.readiness < 55
    assert out.flagged is False  # close to placement → intervention not meaningful


# --- improving trajectory not flagged ---------------------------------------


def test_improving_low_score_not_flagged() -> None:
    """Positive slope → not flagged even with low readiness."""
    track = _track()
    s = _student(
        cycles_per_subskill=_uniform_cycles([35, 40, 50]),  # +7.5 per cycle
        attendance=50,
        time_on_task_hrs=10,
    )
    out = assess_at_risk(s, track)
    assert out.trajectory_slope is not None and out.trajectory_slope > 0
    assert out.flagged is False


# --- truly at-risk profile, full flag --------------------------------------


def test_high_risk_profile_flagged_and_high() -> None:
    """At-risk student is flagged with risk_level=high when readiness < 45."""
    track = _track()
    s = _student(
        cycles_per_subskill=_uniform_cycles([30, 25, 20]),
        attendance=50,
        time_on_task_hrs=10,
        recent_signals=["Missed 4 of last 6 sessions"],
    )
    out = assess_at_risk(s, track)
    assert out.flagged is True
    assert out.risk_level == "high"
    assert out.readiness < 45
    assert out.primary_gap is not None
    assert "Missed 4 of last 6 sessions" in out.contributing_signals


def test_on_track_profile_not_flagged_low_risk() -> None:
    track = _track()
    s = _student(
        cycles_per_subskill=_uniform_cycles([80, 82, 85]),
        attendance=90,
        time_on_task_hrs=25,
    )
    out = assess_at_risk(s, track)
    assert out.flagged is False
    assert out.risk_level == "low"
    assert out.readiness > 70


# --- risk_level mapping at boundaries ---------------------------------------


def test_risk_level_high_below_45() -> None:
    track = _track()
    s = _student(
        cycles_per_subskill=_uniform_cycles([20, 20, 20]),
        attendance=20,
        time_on_task_hrs=2,
    )
    assert assess_at_risk(s, track).risk_level == "high"


def test_risk_level_medium_between_45_and_55() -> None:
    """45 <= readiness < 55 → medium."""
    track = _track()
    # Calibrated: 50 avg + 50 attendance + 50% time → dim = 30+10+10 = 50 → overall 50.
    s = _student(
        cycles_per_subskill=_uniform_cycles([50, 50, 50]),
        attendance=50,
        time_on_task_hrs=12.5,
    )
    out = assess_at_risk(s, track)
    assert out.readiness == pytest.approx(50.0)
    assert out.risk_level == "medium"


def test_risk_level_low_at_or_above_55() -> None:
    track = _track()
    s = _student(
        cycles_per_subskill=_uniform_cycles([60, 60, 60]),
        attendance=60,
        time_on_task_hrs=15,
    )
    out = assess_at_risk(s, track)
    assert out.readiness >= 55
    assert out.risk_level == "low"


# --- trajectory slope edge cases (§1.1, §2.3) -------------------------------


def test_single_cycle_yields_no_slope_signal() -> None:
    """EdgeCases §2.3: one data point → slope None, signal emitted."""
    track = _track()
    s = _student(
        cycles_per_subskill=_uniform_cycles([40]),  # one cycle
        attendance=50,
        time_on_task_hrs=5,
    )
    out = assess_at_risk(s, track)
    assert out.trajectory_slope is None
    assert "insufficient_trajectory_data" in out.contributing_signals
    # readiness < 55, days >= 60 → flagged (None slope treated as non-improving).
    assert out.flagged is True


def test_two_cycle_slope_computed_with_warning_signal() -> None:
    """EdgeCases §1.1: < 3 cycles → slope still computable but flagged in signals."""
    track = _track()
    s = _student(
        cycles_per_subskill=_uniform_cycles([60, 50]),
        attendance=55,
        time_on_task_hrs=13.75,
    )
    out = assess_at_risk(s, track)
    assert out.trajectory_slope is not None
    assert out.trajectory_slope == pytest.approx(-10.0)
    assert "insufficient_trajectory_data" in out.contributing_signals


def test_three_or_more_cycles_no_insufficient_signal() -> None:
    track = _track()
    s = _student(cycles_per_subskill=_uniform_cycles([70, 72, 74]))
    out = assess_at_risk(s, track)
    assert "insufficient_trajectory_data" not in out.contributing_signals


def test_uses_last_three_cycles_not_first_three() -> None:
    """Slope reflects the recent direction, not the whole history."""
    track = _track()
    # Earlier cycles improve sharply, recent cycles decline.
    s = _student(
        cycles_per_subskill=_uniform_cycles([10, 30, 50, 45, 40]),
        attendance=50,
        time_on_task_hrs=10,
    )
    out = assess_at_risk(s, track)
    # Last 3 cycles = [50, 45, 40] → slope = -5.
    assert out.trajectory_slope == pytest.approx(-5.0)


# --- contributing signals shape --------------------------------------------


def test_contributing_signals_surface_decision_inputs() -> None:
    track = _track()
    s = _student(
        cycles_per_subskill=_uniform_cycles([30, 25, 20]),
        attendance=50,
        time_on_task_hrs=10,
        days_to_placement=120,
        recent_signals=["Missed mock interview"],
    )
    out = assess_at_risk(s, track)
    sigs = " ".join(out.contributing_signals)
    assert "readiness_below_55" in sigs
    assert "flat_or_declining_trajectory" in sigs
    assert "placement_window:120d" in sigs
    assert "Missed mock interview" in out.contributing_signals


def test_primary_gap_is_top_priority_gap() -> None:
    """Primary gap should be the same as top_n_gaps(..., n=1)[0]."""
    track = _track(
        weights={"E": 0.1, "L": 0.1, "Q": 0.7, "D": 0.1},
        subskills={
            "english_basic": ("E", 80),
            "logic_basic": ("L", 80),
            "quant_basic": ("Q", 80),  # heavily weighted dim
            "domain_basic": ("D", 80),
        },
    )
    s = _student(
        cycles_per_subskill={
            "english_basic": [30, 30, 30],
            "logic_basic": [70, 70, 70],
            "quant_basic": [50, 50, 50],
            "domain_basic": [70, 70, 70],
        },
        attendance=60,
        time_on_task_hrs=12,
    )
    out = assess_at_risk(s, track)
    assert out.primary_gap is not None
    # quant has the highest priority because dim weight is 0.7
    assert out.primary_gap.subskill == "quant_basic"
