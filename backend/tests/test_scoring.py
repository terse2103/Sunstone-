"""Unit tests for core/scoring.py.

These tests build Student and TrackBenchmark instances directly — they do NOT
load the JSON seed. That keeps scoring tests independent of seed drift and
proves core/ is pure (Rules §Code/1, §Code/6).
"""

from __future__ import annotations

import pytest

from app.core.scoring import (
    ASSESSMENT_WEIGHT,
    TIME_ON_TASK_CAP_HRS,
    compute_dimension_score,
    compute_readiness,
)
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
                    "english_basic": ("E", 70),
                    "logic_basic": ("L", 70),
                    "quant_basic": ("Q", 70),
                    "domain_basic": ("D", 70),
                }
            ).items()
        },
    )


def _student(
    *,
    sid: str = "STU_T",
    assessments: list[Assessment] | None = None,
    attendance: dict[Dimension, float] | None = None,
    time_on_task: dict[Dimension, float] | None = None,
    days_to_placement: int = 120,
    career_track: str = "TestTrack",
) -> Student:
    return Student(
        id=sid,
        name="Test Student",
        program="MBA",
        campus="Pune",
        career_track=career_track,
        days_to_placement=days_to_placement,
        assessments=assessments or [],
        attendance_pct=attendance
        if attendance is not None
        else {"E": 80, "L": 80, "Q": 80, "D": 80},
        time_on_task_hrs=time_on_task
        if time_on_task is not None
        else {"E": 25, "L": 25, "Q": 25, "D": 25},
    )


def _flat_assessments(scores_by_subskill: dict[str, list[float]]) -> list[Assessment]:
    out: list[Assessment] = []
    for subskill, scores in scores_by_subskill.items():
        for i, s in enumerate(scores, start=1):
            out.append(Assessment(subskill=subskill, score=s, cycle=i))
    return out


# --- compute_dimension_score ------------------------------------------------


def test_dimension_score_full_signals() -> None:
    """Happy path: assessment avg + attendance + saturated time → weighted blend."""
    ds = compute_dimension_score(
        dimension="Q",
        assessment_scores_by_subskill={"quant_basic": [80, 90]},  # avg 85
        attendance_pct=80,
        time_on_task_hrs=TIME_ON_TASK_CAP_HRS,  # saturates to 100
    )
    # 0.6 * 85 + 0.2 * 80 + 0.2 * 100 = 51 + 16 + 20 = 87
    assert ds.score == pytest.approx(87.0)
    assert ds.assessment_avg == pytest.approx(85.0)
    assert ds.signals == []


def test_dimension_score_time_below_cap_scales_linearly() -> None:
    """Time-on-task normalises against TIME_ON_TASK_CAP_HRS (25h = 100)."""
    ds = compute_dimension_score(
        dimension="E",
        assessment_scores_by_subskill={"english": [60]},
        attendance_pct=60,
        time_on_task_hrs=12.5,  # half of cap → 50
    )
    # 0.6 * 60 + 0.2 * 60 + 0.2 * 50 = 36 + 12 + 10 = 58
    assert ds.score == pytest.approx(58.0)


def test_dimension_score_time_above_cap_clamps_to_100() -> None:
    """Hours past the cap don't reward further (avoid runaway scores)."""
    ds = compute_dimension_score(
        dimension="E",
        assessment_scores_by_subskill={"english": [100]},
        attendance_pct=100,
        time_on_task_hrs=TIME_ON_TASK_CAP_HRS * 5,
    )
    assert ds.score == pytest.approx(100.0)


def test_dimension_score_no_data_subskill_flags_signal() -> None:
    """EdgeCases §1.2 + §1.4: missing sub-skill data → score=0 + no_data signal."""
    ds = compute_dimension_score(
        dimension="D",
        assessment_scores_by_subskill={
            "domain_a": [80],  # has data
            "domain_b": [],  # no data → 0, signal
        },
        attendance_pct=80,
        time_on_task_hrs=TIME_ON_TASK_CAP_HRS,
    )
    # assessment_avg = mean(80, 0) = 40
    # 0.6 * 40 + 0.2 * 80 + 0.2 * 100 = 24 + 16 + 20 = 60
    assert ds.score == pytest.approx(60.0)
    assert "no_data:domain_b" in ds.signals


def test_dimension_score_missing_attendance_capped_at_60() -> None:
    """EdgeCases §1.6: missing attendance → assessment-only, max 60."""
    ds = compute_dimension_score(
        dimension="E",
        assessment_scores_by_subskill={"english": [100]},
        attendance_pct=None,
        time_on_task_hrs=TIME_ON_TASK_CAP_HRS,
    )
    assert ds.score == pytest.approx(60.0)
    assert ds.score <= 60.0
    assert "missing_signal:E:attendance" in ds.signals


def test_dimension_score_missing_time_on_task_capped_at_60() -> None:
    ds = compute_dimension_score(
        dimension="E",
        assessment_scores_by_subskill={"english": [100]},
        attendance_pct=100,
        time_on_task_hrs=None,
    )
    assert ds.score == pytest.approx(60.0)
    assert "missing_signal:E:time_on_task" in ds.signals


def test_dimension_score_both_missing_signals_emitted() -> None:
    ds = compute_dimension_score(
        dimension="L",
        assessment_scores_by_subskill={"logic": [80]},
        attendance_pct=None,
        time_on_task_hrs=None,
    )
    assert ds.score == pytest.approx(ASSESSMENT_WEIGHT * 80)
    assert "missing_signal:L:attendance" in ds.signals
    assert "missing_signal:L:time_on_task" in ds.signals


def test_dimension_score_subskill_avg_then_dim_avg_not_global_avg() -> None:
    """Per architecture §4.2: average per sub-skill first, then across sub-skills.

    Without this, a sub-skill with many cycles would dominate one with few.
    """
    ds = compute_dimension_score(
        dimension="D",
        assessment_scores_by_subskill={
            "domain_a": [40, 40, 40, 40],  # avg 40
            "domain_b": [80],  # avg 80
        },
        attendance_pct=0,
        time_on_task_hrs=0,
    )
    # subskill_avgs = [40, 80] → dim avg = 60
    # 0.6 * 60 + 0 + 0 = 36
    assert ds.score == pytest.approx(36.0)


# --- compute_readiness — boundary + profile cases ---------------------------


def test_readiness_all_zero_inputs_yields_zero() -> None:
    """EdgeCases §2.1: all-zero inputs → overall = 0, no NaN, no crash."""
    track = _track()
    s = _student(
        assessments=_flat_assessments(
            {"english_basic": [0], "logic_basic": [0], "quant_basic": [0], "domain_basic": [0]}
        ),
        attendance={"E": 0, "L": 0, "Q": 0, "D": 0},
        time_on_task={"E": 0, "L": 0, "Q": 0, "D": 0},
    )
    result = compute_readiness(s, track)
    assert result.overall == pytest.approx(0.0)
    assert all(ds.score == pytest.approx(0.0) for ds in result.dimensions)


def test_readiness_all_max_inputs_yields_100() -> None:
    """EdgeCases §2.1: all-100 inputs → overall = 100."""
    track = _track()
    s = _student(
        assessments=_flat_assessments(
            {
                "english_basic": [100],
                "logic_basic": [100],
                "quant_basic": [100],
                "domain_basic": [100],
            }
        ),
        attendance={"E": 100, "L": 100, "Q": 100, "D": 100},
        time_on_task={"E": 25, "L": 25, "Q": 25, "D": 25},
    )
    result = compute_readiness(s, track)
    assert result.overall == pytest.approx(100.0)


def test_readiness_on_track_profile() -> None:
    """On-track student should score > 70."""
    track = _track()
    s = _student(
        assessments=_flat_assessments(
            {
                "english_basic": [78, 80, 82],
                "logic_basic": [80, 82, 84],
                "quant_basic": [82, 84, 86],
                "domain_basic": [78, 80, 82],
            }
        ),
        attendance={"E": 90, "L": 90, "Q": 92, "D": 88},
        time_on_task={"E": 20, "L": 22, "Q": 25, "D": 24},
    )
    result = compute_readiness(s, track)
    assert result.overall > 70


def test_readiness_at_risk_profile() -> None:
    """At-risk student should score < 55."""
    track = _track()
    s = _student(
        assessments=_flat_assessments(
            {
                "english_basic": [45, 42, 40],
                "logic_basic": [50, 48, 45],
                "quant_basic": [42, 40, 38],
                "domain_basic": [50, 48, 45],
            }
        ),
        attendance={"E": 55, "L": 60, "Q": 50, "D": 55},
        time_on_task={"E": 6, "L": 8, "Q": 7, "D": 8},
    )
    result = compute_readiness(s, track)
    assert result.overall < 55


def test_readiness_borderline_profile() -> None:
    track = _track()
    s = _student(
        assessments=_flat_assessments(
            {
                "english_basic": [60, 62, 65],
                "logic_basic": [62, 64, 66],
                "quant_basic": [60, 62, 64],
                "domain_basic": [60, 62, 64],
            }
        ),
        attendance={"E": 75, "L": 78, "Q": 78, "D": 75},
        time_on_task={"E": 14, "L": 16, "Q": 15, "D": 15},
    )
    result = compute_readiness(s, track)
    assert 55 <= result.overall <= 70


def test_readiness_track_weights_drive_overall() -> None:
    """Overall is the weighted sum of dimension scores using TrackBenchmark.weights.

    Hand trace: Q-heavy track (0.7 on Q, others 0.1). Student maxes Q only,
    others at 0 → overall ≈ 0.7 * Q_dim_score.
    """
    track = _track(
        weights={"E": 0.1, "L": 0.1, "Q": 0.7, "D": 0.1},
    )
    s = _student(
        assessments=_flat_assessments(
            {
                "english_basic": [0],
                "logic_basic": [0],
                "quant_basic": [100],
                "domain_basic": [0],
            }
        ),
        attendance={"E": 0, "L": 0, "Q": 100, "D": 0},
        time_on_task={"E": 0, "L": 0, "Q": 25, "D": 0},
    )
    result = compute_readiness(s, track)
    assert result.overall == pytest.approx(0.7 * 100.0)


def test_readiness_missing_subskill_in_student_treated_as_zero() -> None:
    """EdgeCases §1.2 / §1.4 surfaced via the dimension signal list."""
    track = _track()
    # Only one sub-skill assessed; the other 3 dimensions have no data.
    s = _student(
        assessments=_flat_assessments({"english_basic": [80, 80]}),
    )
    result = compute_readiness(s, track)
    q_dim = next(d for d in result.dimensions if d.dimension == "Q")
    assert "no_data:quant_basic" in q_dim.signals
    assert q_dim.assessment_avg == pytest.approx(0.0)


def test_readiness_missing_dimension_signals_uses_assessment_only_path() -> None:
    """EdgeCases §1.6: dimension missing from attendance_pct → capped contribution."""
    track = _track()
    s = _student(
        assessments=_flat_assessments(
            {"english_basic": [100], "logic_basic": [0], "quant_basic": [0], "domain_basic": [0]}
        ),
        attendance={"L": 0, "Q": 0, "D": 0},  # E missing
        time_on_task={"E": 25, "L": 0, "Q": 0, "D": 0},
    )
    result = compute_readiness(s, track)
    e_dim = next(d for d in result.dimensions if d.dimension == "E")
    assert "missing_signal:E:attendance" in e_dim.signals
    assert e_dim.score == pytest.approx(60.0)  # capped at 0.6 * 100


def test_readiness_handles_missing_cycles_uses_available(
) -> None:
    """EdgeCases §1.1: scoring uses available cycles for sub-skills with < 3 cycles."""
    track = _track()
    s = _student(
        assessments=_flat_assessments(
            {
                "english_basic": [80],  # single cycle
                "logic_basic": [80, 80],  # two cycles
                "quant_basic": [80, 80, 80],
                "domain_basic": [80, 80, 80],
            }
        ),
    )
    result = compute_readiness(s, track)
    # All sub-skill averages are 80 → no special signal at scoring layer.
    for d in result.dimensions:
        assert d.assessment_avg == pytest.approx(80.0)
        assert not any(sig.startswith("no_data:") for sig in d.signals)


def test_readiness_output_shape() -> None:
    track = _track()
    s = _student(assessments=_flat_assessments({"english_basic": [70]}))
    result = compute_readiness(s, track)
    assert result.student_id == s.id
    assert result.track == track.name
    assert {d.dimension for d in result.dimensions} == {"E", "L", "Q", "D"}
    assert 0.0 <= result.overall <= 100.0
