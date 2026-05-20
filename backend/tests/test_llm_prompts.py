"""Sanity tests for prompt rendering and the prompt-injection guard (§5.6)."""

from __future__ import annotations

from app.llm.prompts import (
    GAP_RATIONALE_SYSTEM,
    INJECTION_GUARD,
    INTERVENTION_BRIEF_SYSTEM,
    READINESS_NARRATIVE_SYSTEM,
    render_gap_rationale,
    render_intervention_brief,
    render_readiness_narrative,
)
from app.models import AtRiskAssessment, DimensionScore, Gap, ReadinessResult


def _gap(**overrides) -> Gap:
    base = dict(
        subskill="quant_aptitude",
        dimension="Q",
        student_score=55.0,
        benchmark=80.0,
        gap_size=25.0,
        priority_score=8.75,
        rank=1,
        jd_frequency=0.71,
        signals=["no_data:financial_math"],
    )
    base.update(overrides)
    return Gap(**base)


def _at_risk(**overrides) -> AtRiskAssessment:
    base = dict(
        student_id="STU_X",
        risk_level="high",
        flagged=True,
        readiness=38.4,
        trajectory_slope=-3.5,
        days_to_placement=140,
        primary_gap=_gap(),
        contributing_signals=["Missed 4 of last 6 sessions"],
    )
    base.update(overrides)
    return AtRiskAssessment(**base)


def test_system_prompts_include_injection_guard() -> None:
    assert INJECTION_GUARD in GAP_RATIONALE_SYSTEM
    assert INJECTION_GUARD in INTERVENTION_BRIEF_SYSTEM
    assert INJECTION_GUARD in READINESS_NARRATIVE_SYSTEM


def test_render_readiness_narrative_emits_precomputed_signals() -> None:
    """The new narrative payload deliberately contains NO numbers and NO
    student name — only the pre-computed band, exceeding dims, and priority
    dims. Numbers and names are stripped on purpose so the model can't
    accidentally surface them in the output.
    """
    readiness = ReadinessResult(
        student_id="STU_X",
        track="BFSI",
        overall=63.1,
        dimensions=[
            DimensionScore(
                dimension="E", score=70, benchmark=65, assessment_avg=70,
                attendance_pct=85, time_on_task_hrs=18, signals=[],
            ),
            DimensionScore(
                dimension="L", score=60, benchmark=70, assessment_avg=58,
                attendance_pct=90, time_on_task_hrs=22, signals=[],
            ),
            DimensionScore(
                dimension="Q", score=82, benchmark=78, assessment_avg=80,
                attendance_pct=90, time_on_task_hrs=25, signals=[],
            ),
            DimensionScore(
                dimension="D", score=45, benchmark=72, assessment_avg=40,
                attendance_pct=88, time_on_task_hrs=24, signals=[],
            ),
        ],
    )
    out = render_readiness_narrative(
        readiness=readiness, student_name="Priya Sharma", track_name="BFSI"
    )
    pre, payload = out.split("<student_data>", 1)
    body, post = payload.split("</student_data>", 1)

    # Student name must never appear in the prompt body (or the trailing
    # instruction) — addressing 'you' is enforced by the system prompt and
    # leaking the name here would give the model a way to break that rule.
    assert "Priya Sharma" not in body
    assert "Priya Sharma" not in post

    # No raw scores or benchmarks should be in the payload — only the
    # pre-computed band + dimension classification.
    assert "63" not in body
    assert "score" not in body
    assert "benchmark" not in body or "exceeding_benchmark" in body

    assert "track: BFSI" in body
    # Overall 63.1 is in the 55–70 borderline band.
    assert "readiness_band: borderline" in body
    # English (+5) outranks Quant (+4) on surplus, so listed first.
    assert "exceeding_benchmark (strongest surplus first): English, Quant" in body
    # Domain (-27) outranks Logic (-10) on shortfall, so listed first.
    assert "priority_dimensions (work on first): Domain, Logic" in body


def test_render_readiness_narrative_handles_all_exceeding() -> None:
    """No priority dimensions — payload should mark it as '(none)' so the
    model knows to skip the priority sentence and pivot the CTA."""
    readiness = ReadinessResult(
        student_id="STU_Y",
        track="BFSI",
        overall=88.0,
        dimensions=[
            DimensionScore(
                dimension=dim, score=90, benchmark=70, assessment_avg=90,
                attendance_pct=90, time_on_task_hrs=24, signals=[],
            )
            for dim in ("E", "L", "Q", "D")
        ],
    )
    out = render_readiness_narrative(
        readiness=readiness, student_name="X", track_name="BFSI"
    )
    assert "readiness_band: on track" in out
    assert "priority_dimensions (work on first): (none)" in out


def test_render_readiness_narrative_handles_all_below() -> None:
    """No exceeding dimensions — payload should mark it as '(none)' so the
    model skips the recognition sentence."""
    readiness = ReadinessResult(
        student_id="STU_Z",
        track="Analytics",
        overall=40.0,
        dimensions=[
            DimensionScore(
                dimension=dim, score=40, benchmark=75, assessment_avg=40,
                attendance_pct=60, time_on_task_hrs=10, signals=[],
            )
            for dim in ("E", "L", "Q", "D")
        ],
    )
    out = render_readiness_narrative(
        readiness=readiness, student_name="X", track_name="Analytics"
    )
    assert "readiness_band: at risk of falling short of placement" in out
    assert "exceeding_benchmark (strongest surplus first): (none)" in out


def test_render_gap_rationale_wraps_user_data_in_tag() -> None:
    out = render_gap_rationale(
        gap=_gap(), student_name="Priya Sharma", track_name="BFSI"
    )
    assert "<student_data>" in out
    assert "</student_data>" in out
    # Student-controlled fields must appear inside the tag.
    pre, payload = out.split("<student_data>", 1)
    body, post = payload.split("</student_data>", 1)
    assert "Priya Sharma" in body
    assert "quant_aptitude" in body
    assert "BFSI" in body
    # Nothing student-controlled should appear in the trailing instruction.
    assert "Priya Sharma" not in post
    assert "quant_aptitude" not in post


def test_render_gap_rationale_handles_missing_jd_frequency() -> None:
    out = render_gap_rationale(
        gap=_gap(jd_frequency=None), student_name="Test", track_name="BFSI"
    )
    assert "JD frequency unknown" in out


def test_render_intervention_brief_includes_all_decision_inputs() -> None:
    out = render_intervention_brief(
        at_risk=_at_risk(), student_name="Meera Iyer", track_name="BFSI"
    )
    assert "Meera Iyer" in out
    assert "readiness: 38.4" in out
    assert "trajectory_slope: -3.50 per cycle" in out
    assert "days_to_placement: 140" in out
    assert "primary_gap_subskill: quant_aptitude" in out
    assert "Missed 4 of last 6 sessions" in out


def test_render_intervention_brief_handles_no_slope() -> None:
    out = render_intervention_brief(
        at_risk=_at_risk(trajectory_slope=None),
        student_name="Test",
        track_name="BFSI",
    )
    assert "trajectory_slope: insufficient data" in out


def test_render_intervention_brief_handles_no_primary_gap() -> None:
    out = render_intervention_brief(
        at_risk=_at_risk(primary_gap=None),
        student_name="Test",
        track_name="BFSI",
    )
    assert "primary_gap: none" in out
