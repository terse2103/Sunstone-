"""Unit tests for core/gaps.py."""

from __future__ import annotations

import pytest

from app.core.gaps import compute_gaps, top_n_gaps
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
    jd_frequency: dict[str, float] | None = None,
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
        jd_frequency=jd_frequency or {},
    )


def _student(
    *,
    assessments: list[Assessment] | None = None,
    career_track: str = "TestTrack",
) -> Student:
    return Student(
        id="STU_G",
        name="Test Student",
        program="MBA",
        campus="Pune",
        career_track=career_track,
        days_to_placement=120,
        assessments=assessments or [],
        attendance_pct={"E": 80, "L": 80, "Q": 80, "D": 80},
        time_on_task_hrs={"E": 20, "L": 20, "Q": 20, "D": 20},
    )


def _flat(scores_by_subskill: dict[str, list[float]]) -> list[Assessment]:
    out: list[Assessment] = []
    for subskill, scores in scores_by_subskill.items():
        for i, s in enumerate(scores, start=1):
            out.append(Assessment(subskill=subskill, score=s, cycle=i))
    return out


# --- compute_gaps -----------------------------------------------------------


def test_gaps_excludes_subskills_at_or_above_benchmark() -> None:
    """EdgeCases §3.4: gap_size <= 0 is filtered."""
    track = _track()
    s = _student(
        assessments=_flat(
            {
                "english_basic": [70],  # exactly at benchmark → excluded
                "logic_basic": [80],  # above benchmark → excluded
                "quant_basic": [50],  # below → gap of 20
                "domain_basic": [60],  # below → gap of 10
            }
        ),
    )
    gaps = compute_gaps(s, track)
    names = [g.subskill for g in gaps]
    assert "english_basic" not in names
    assert "logic_basic" not in names
    assert set(names) == {"quant_basic", "domain_basic"}


def test_gaps_empty_when_student_exceeds_all_benchmarks() -> None:
    """EdgeCases §3.1: no priority gaps."""
    track = _track()
    s = _student(
        assessments=_flat(
            {
                "english_basic": [80],
                "logic_basic": [80],
                "quant_basic": [80],
                "domain_basic": [80],
            }
        ),
    )
    assert compute_gaps(s, track) == []
    assert top_n_gaps(s, track) == []


def test_gaps_priority_score_is_size_times_dim_weight() -> None:
    """Heavier-weighted dimension wins over a numerically larger gap in a lighter dim."""
    track = _track(weights={"E": 0.1, "L": 0.1, "Q": 0.7, "D": 0.1})
    s = _student(
        assessments=_flat(
            {
                "english_basic": [30],  # gap 40, priority 4
                "logic_basic": [70],  # no gap
                "quant_basic": [60],  # gap 10, priority 7
                "domain_basic": [70],  # no gap
            }
        ),
    )
    gaps = compute_gaps(s, track)
    assert gaps[0].subskill == "quant_basic"
    assert gaps[0].priority_score == pytest.approx(7.0)
    assert gaps[1].subskill == "english_basic"
    assert gaps[1].priority_score == pytest.approx(4.0)


def test_gaps_stable_tiebreak_by_subskill_name() -> None:
    """EdgeCases §3.3: identical priority → alphabetical sub-skill order."""
    track = _track(
        weights={"E": 0.25, "L": 0.25, "Q": 0.25, "D": 0.25},
        subskills={
            # All in dim E with the same benchmark + same student score
            # → identical priority. Tiebreak must be reproducible.
            "zebra": ("E", 80),
            "apple": ("E", 80),
            "mango": ("E", 80),
            # Filler for the other 3 dims so weights stay realistic
            "logic_basic": ("L", 0),
            "quant_basic": ("Q", 0),
            "domain_basic": ("D", 0),
        },
    )
    s = _student(
        assessments=_flat(
            {
                "zebra": [50],
                "apple": [50],
                "mango": [50],
            }
        ),
    )
    gaps = compute_gaps(s, track)
    tied_names = [g.subskill for g in gaps if g.dimension == "E"]
    assert tied_names == ["apple", "mango", "zebra"]


def test_gaps_missing_subskill_treated_as_zero_with_signal() -> None:
    """EdgeCases §1.4: sub-skill never assessed → score 0, full benchmark as gap, signal."""
    track = _track()
    s = _student(
        assessments=_flat({"english_basic": [80]}),  # only one sub-skill present
    )
    gaps = compute_gaps(s, track)
    quant = next(g for g in gaps if g.subskill == "quant_basic")
    assert quant.student_score == pytest.approx(0.0)
    assert quant.gap_size == pytest.approx(70.0)
    assert "no_data:quant_basic" in quant.signals


def test_gaps_includes_jd_frequency_when_available() -> None:
    track = _track(jd_frequency={"quant_basic": 0.42})
    s = _student(
        assessments=_flat(
            {
                "english_basic": [70],
                "logic_basic": [70],
                "quant_basic": [50],
                "domain_basic": [70],
            }
        ),
    )
    gaps = compute_gaps(s, track)
    quant = next(g for g in gaps if g.subskill == "quant_basic")
    assert quant.jd_frequency == pytest.approx(0.42)


def test_gaps_jd_frequency_absent_when_not_in_track() -> None:
    track = _track(jd_frequency={})
    s = _student(
        assessments=_flat(
            {
                "english_basic": [70],
                "logic_basic": [70],
                "quant_basic": [50],
                "domain_basic": [70],
            }
        ),
    )
    gaps = compute_gaps(s, track)
    quant = next(g for g in gaps if g.subskill == "quant_basic")
    assert quant.jd_frequency is None


def test_gaps_rank_assigned_in_priority_order() -> None:
    track = _track(weights={"E": 0.4, "L": 0.3, "Q": 0.2, "D": 0.1})
    s = _student(
        assessments=_flat(
            {
                "english_basic": [50],  # gap 20 * 0.4 = 8
                "logic_basic": [40],  # gap 30 * 0.3 = 9
                "quant_basic": [60],  # gap 10 * 0.2 = 2
                "domain_basic": [40],  # gap 30 * 0.1 = 3
            }
        ),
    )
    gaps = compute_gaps(s, track)
    assert [g.rank for g in gaps] == [1, 2, 3, 4]
    assert [g.subskill for g in gaps] == [
        "logic_basic",
        "english_basic",
        "domain_basic",
        "quant_basic",
    ]


# --- top_n_gaps -------------------------------------------------------------


def test_top_n_returns_at_most_n() -> None:
    track = _track()
    s = _student(
        assessments=_flat(
            {
                "english_basic": [10],
                "logic_basic": [10],
                "quant_basic": [10],
                "domain_basic": [10],
            }
        ),
    )
    assert len(top_n_gaps(s, track, n=3)) == 3
    assert len(top_n_gaps(s, track, n=2)) == 2
    assert len(top_n_gaps(s, track, n=10)) == 4  # only 4 sub-skills exist


def test_top_n_returns_fewer_when_not_enough_gaps() -> None:
    """EdgeCases §3.2: never pad with synthetic gaps."""
    track = _track()
    s = _student(
        assessments=_flat(
            {
                "english_basic": [80],  # no gap
                "logic_basic": [80],  # no gap
                "quant_basic": [60],  # gap 10
                "domain_basic": [80],  # no gap
            }
        ),
    )
    top = top_n_gaps(s, track, n=3)
    assert len(top) == 1
    assert top[0].subskill == "quant_basic"


def test_top_n_zero_or_negative_returns_empty() -> None:
    track = _track()
    s = _student(assessments=_flat({"english_basic": [10]}))
    assert top_n_gaps(s, track, n=0) == []
    assert top_n_gaps(s, track, n=-5) == []


def test_top_n_first_three_are_highest_priority() -> None:
    track = _track(weights={"E": 0.4, "L": 0.3, "Q": 0.2, "D": 0.1})
    s = _student(
        assessments=_flat(
            {
                "english_basic": [50],  # priority 8
                "logic_basic": [40],  # priority 9
                "quant_basic": [60],  # priority 2
                "domain_basic": [40],  # priority 3
            }
        ),
    )
    top = top_n_gaps(s, track, n=3)
    assert [g.subskill for g in top] == ["logic_basic", "english_basic", "domain_basic"]
    assert [g.rank for g in top] == [1, 2, 3]
