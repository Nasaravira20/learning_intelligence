from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class QuestionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_code: str = Field(min_length=3, max_length=80)
    prompt: str = Field(min_length=12, max_length=400)
