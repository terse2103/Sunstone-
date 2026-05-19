from typing import Literal

from pydantic import BaseModel, Field

from app.models.readiness import Gap

RiskLevel = Literal["high", "medium", "low", "unknown"]


class AtRiskAssessment(BaseModel):
    student_id: str
    risk_level: RiskLevel
    flagged: bool
    readiness: float = Field(ge=0, le=100)
    trajectory_slope: float | None = None
    days_to_placement: int = Field(ge=0)
    primary_gap: Gap | None = None
    contributing_signals: list[str] = Field(default_factory=list)


class InterventionBrief(BaseModel):
    student_id: str
    lines: list[str] = Field(min_length=1)
    contributing_signals: list[str] = Field(default_factory=list)
