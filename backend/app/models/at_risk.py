from typing import Literal

from pydantic import BaseModel, Field

from app.models.readiness import Gap

RiskLevel = Literal["high", "medium", "low", "unknown"]

# The signal a counselor should attack first to move this student's readiness:
#   - assessment_scores: the dimension's mean cycle score is the biggest drag
#   - attendance: low attendance is the biggest drag
#   - time_on_task: low engagement hours are the biggest drag
PrimaryLever = Literal["assessment_scores", "attendance", "time_on_task"]

# Coarse projection of readiness vs the 55-point threshold:
#   - on_track_above: already at/above the threshold
#   - improving_in_reach: positive slope and projected to reach the threshold
#     before the placement window closes
#   - improving_too_slow: positive slope but won't reach in time
#   - flat_below: slope = 0, stuck under the threshold
#   - declining: slope < 0
#   - unknown: insufficient cycle data to project
TrajectoryOutlook = Literal[
    "on_track_above",
    "improving_in_reach",
    "improving_too_slow",
    "flat_below",
    "declining",
    "unknown",
]


class AtRiskAssessment(BaseModel):
    student_id: str
    risk_level: RiskLevel
    flagged: bool
    readiness: float = Field(ge=0, le=100)
    trajectory_slope: float | None = None
    days_to_placement: int = Field(ge=0)
    primary_gap: Gap | None = None
    contributing_signals: list[str] = Field(default_factory=list)
    # New in P10 polish — drive the rewritten intervention brief + UI:
    primary_lever: PrimaryLever | None = None
    trajectory_outlook: TrajectoryOutlook = "unknown"
    top_struggling_subskills: list[str] = Field(default_factory=list)
    # Full ELQD names ("English", "Logic", "Quant", "Domain") in severity
    # order — derived from the priority-ranked gap list. Empty when no
    # positive gaps exist.
    severity_ranked_dimensions: list[str] = Field(default_factory=list)


class InterventionBrief(BaseModel):
    student_id: str
    lines: list[str] = Field(min_length=1)
    contributing_signals: list[str] = Field(default_factory=list)
