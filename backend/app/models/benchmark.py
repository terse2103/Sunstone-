from typing import Literal

from pydantic import BaseModel, Field

Dimension = Literal["E", "L", "Q", "D"]


class SubSkillBenchmark(BaseModel):
    dimension: Dimension
    benchmark: float = Field(ge=0, le=100)


class TrackBenchmark(BaseModel):
    name: str = Field(min_length=1)
    weights: dict[Dimension, float]
    subskills: dict[str, SubSkillBenchmark]
    jd_frequency: dict[str, float] = Field(default_factory=dict)
