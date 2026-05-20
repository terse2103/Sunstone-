"""Student-facing routes: profile, readiness, top gaps with LLM rationale."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query

from app.core import benchmarks as benchmarks_registry
from app.core.gaps import top_n_gaps
from app.core.scoring import compute_readiness
from app.data import seed
from app.deps import get_llm, get_student_or_404
from app.llm.client import AnthropicClient
from app.models import (
    Gap,
    ReadinessNarrative,
    ReadinessResult,
    Student,
    StudentSummary,
)

router = APIRouter(prefix="/api/students", tags=["student"])


@router.get("", response_model=list[StudentSummary])
def list_students() -> list[StudentSummary]:
    return [
        StudentSummary(
            id=s.id,
            name=s.name,
            program=s.program,
            campus=s.campus,
            career_track=s.career_track,
        )
        for s in seed.STUDENTS.values()
    ]


@router.get("/{student_id}", response_model=Student)
def get_student(student: Student = Depends(get_student_or_404)) -> Student:
    return student


@router.get("/{student_id}/readiness", response_model=ReadinessResult)
def get_readiness(student: Student = Depends(get_student_or_404)) -> ReadinessResult:
    track = benchmarks_registry.get_track(student.career_track)
    return compute_readiness(student, track)


@router.get("/{student_id}/narrative", response_model=ReadinessNarrative)
async def get_narrative(
    student: Student = Depends(get_student_or_404),
    llm: AnthropicClient = Depends(get_llm),
) -> ReadinessNarrative:
    track = benchmarks_registry.get_track(student.career_track)
    readiness = compute_readiness(student, track)
    text = await asyncio.to_thread(
        llm.readiness_narrative,
        readiness=readiness,
        student_name=student.name,
        track_name=track.name,
    )
    return ReadinessNarrative(student_id=student.id, text=text)


@router.get("/{student_id}/gaps", response_model=list[Gap])
async def get_gaps(
    student: Student = Depends(get_student_or_404),
    n: int = Query(default=3, ge=1, le=20),
    llm: AnthropicClient = Depends(get_llm),
) -> list[Gap]:
    track = benchmarks_registry.get_track(student.career_track)
    gaps = top_n_gaps(student, track, n=n)
    if not gaps:
        return gaps

    # Per architecture §4.6, fan out the LLM calls in parallel. The client is
    # sync, so we hand each call to a thread and gather them.
    rationales = await asyncio.gather(
        *(
            asyncio.to_thread(
                llm.gap_rationale,
                gap=g,
                student_name=student.name,
                track_name=track.name,
            )
            for g in gaps
        )
    )
    return [g.model_copy(update={"rationale": r}) for g, r in zip(gaps, rationales)]
