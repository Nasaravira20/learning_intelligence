from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ActivityKind = Literal[
    "explanation",
    "concrete_example",
    "worked_example",
    "guided_practice",
    "independent_practice",
    "check_for_understanding",
    "self_explanation",
]
SupportLevel = Literal["high", "medium", "low"]


class HintDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=8, max_length=240)
    reveals_answer: bool


class ActivityDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: str = Field(min_length=3, max_length=64)
    kind: ActivityKind
    title: str = Field(min_length=8, max_length=120)
    prompt: str = Field(min_length=12, max_length=500)
    example: str | None = Field(default=None, max_length=500)
    worked_steps: list[str] = Field(default_factory=list, max_length=6)
    expected_answer: str | None = Field(default=None, max_length=300)
    hints: list[HintDraft] = Field(default_factory=list, max_length=4)
    support_level: SupportLevel


class LessonDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_code: str = Field(min_length=3, max_length=80)
    activities: list[ActivityDraft] = Field(min_length=2, max_length=8)
