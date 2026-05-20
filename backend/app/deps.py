"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import HTTPException, Request

from app.data import seed
from app.llm.client import AnthropicClient
from app.models import Student


def get_llm(request: Request) -> AnthropicClient:
    """Singleton AnthropicClient stored on app.state by the lifespan handler."""
    return request.app.state.llm


def get_student_or_404(student_id: str) -> Student:
    student = seed.STUDENTS.get(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="unknown_student_id")
    return student
