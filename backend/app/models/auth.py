from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["student", "counselor"]


class LoginRequest(BaseModel):
    role: Role
    student_id: str | None = Field(default=None, min_length=1)


class LoginResponse(BaseModel):
    role: Role
    student_id: str | None = None
