"""Counselor routes: at-risk listing, intervention brief, mark-action.

The mark-action set is in-memory and lost on restart — documented behaviour
per EdgeCases §11.1 and the prototype scope in architecture §9.3.
"""

from __future__ import annotations

import asyncio
from typing import Final

from fastapi import APIRouter, Depends, Response, status

from app.core import benchmarks as benchmarks_registry
from app.core.at_risk import assess_at_risk
from app.data import seed
from app.deps import get_llm, get_student_or_404
from app.llm.client import AnthropicClient
from app.models import AtRiskAssessment, InterventionBrief, Student

router = APIRouter(prefix="/api/counselor", tags=["counselor"])

# In-memory set of students the counselor has marked as actioned. Lost on
# restart — see EdgeCases §11.1.
_ACTIONS_TAKEN: Final[set[str]] = set()


@router.get("/at-risk", response_model=list[AtRiskAssessment])
def at_risk_students() -> list[AtRiskAssessment]:
    flagged: list[AtRiskAssessment] = []
    for student in seed.STUDENTS.values():
        track = benchmarks_registry.get_track(student.career_track)
        assessment = assess_at_risk(student, track)
        if assessment.flagged:
            flagged.append(assessment)
    # Most-at-risk first: lowest readiness, then student id for stability.
    flagged.sort(key=lambda a: (a.readiness, a.student_id))
    return flagged


@router.get(
    "/students/{student_id}/brief",
    response_model=InterventionBrief,
)
async def intervention_brief(
    student: Student = Depends(get_student_or_404),
    llm: AnthropicClient = Depends(get_llm),
) -> InterventionBrief:
    track = benchmarks_registry.get_track(student.career_track)
    assessment = assess_at_risk(student, track)
    lines = await asyncio.to_thread(
        llm.intervention_brief,
        at_risk=assessment,
        student_name=student.name,
        track_name=track.name,
    )
    return InterventionBrief(
        student_id=student.id,
        lines=lines,
        contributing_signals=assessment.contributing_signals,
    )


@router.post(
    "/students/{student_id}/action",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def mark_action(student: Student = Depends(get_student_or_404)) -> Response:
    _ACTIONS_TAKEN.add(student.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def actions_taken() -> frozenset[str]:
    """Read-only view of the in-memory action set, intended for tests."""
    return frozenset(_ACTIONS_TAKEN)


def reset_actions() -> None:
    """Test helper. Not exposed via HTTP."""
    _ACTIONS_TAKEN.clear()
