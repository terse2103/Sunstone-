from pydantic import BaseModel, Field

from app.models.benchmark import Dimension


class DimensionScore(BaseModel):
    dimension: Dimension
    score: float = Field(ge=0, le=100)
    benchmark: float = Field(ge=0, le=100)
    assessment_avg: float = Field(ge=0, le=100)
    attendance_pct: float = Field(ge=0, le=100)
    time_on_task_hrs: float = Field(ge=0)
    signals: list[str] = Field(default_factory=list)


class ReadinessResult(BaseModel):
    student_id: str
    track: str
    overall: float = Field(ge=0, le=100)
    dimensions: list[DimensionScore]


class ReadinessNarrative(BaseModel):
    student_id: str
    text: str = Field(min_length=1)


class Gap(BaseModel):
    subskill: str
    dimension: Dimension
    student_score: float = Field(ge=0, le=100)
    benchmark: float = Field(ge=0, le=100)
    gap_size: float = Field(gt=0)
    priority_score: float = Field(ge=0)
    rank: int = Field(ge=1)
    jd_frequency: float | None = Field(default=None, ge=0, le=1)
    signals: list[str] = Field(default_factory=list)
    rationale: str | None = None
