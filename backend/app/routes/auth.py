"""Mock login endpoint. No tokens issued — the frontend persists role / student_id
client-side per architecture §5.3."""

from fastapi import APIRouter, HTTPException

from app.data import seed
from app.models import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    if payload.role == "student":
        if not payload.student_id:
            raise HTTPException(status_code=422, detail="student_id_required_for_student_role")
        if payload.student_id not in seed.STUDENTS:
            raise HTTPException(status_code=404, detail="unknown_student_id")
        return LoginResponse(role="student", student_id=payload.student_id)
    return LoginResponse(role="counselor")
