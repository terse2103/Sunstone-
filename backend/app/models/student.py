from pydantic import BaseModel, Field

from app.models.benchmark import Dimension


class Assessment(BaseModel):
    subskill: str = Field(min_length=1)
    score: float = Field(ge=0, le=100)
    cycle: int = Field(ge=1)


class Student(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    program: str = Field(min_length=1)
    campus: str = Field(min_length=1)
    career_track: str = Field(min_length=1)
    days_to_placement: int = Field(ge=0)
    assessments: list[Assessment] = Field(default_factory=list)
    attendance_pct: dict[Dimension, float] = Field(default_factory=dict)
    time_on_task_hrs: dict[Dimension, float] = Field(default_factory=dict)
    recent_signals: list[str] = Field(default_factory=list)
