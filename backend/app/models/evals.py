from typing import Any, Literal

from pydantic import BaseModel, Field

EvalStatus = Literal["pass", "fail", "not_run"]


class EvalCase(BaseModel):
    name: str
    passed: bool
    expected: Any = None
    actual: Any = None
    note: str | None = None


class EvalResult(BaseModel):
    name: str
    status: EvalStatus
    metrics: dict[str, float] = Field(default_factory=dict)
    cases: list[EvalCase] = Field(default_factory=list)


class EvalsReport(BaseModel):
    status: EvalStatus
    ran_at: str | None = None
    suites: list[EvalResult] = Field(default_factory=list)
