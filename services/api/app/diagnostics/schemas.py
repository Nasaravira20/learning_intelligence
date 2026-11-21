from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QuestionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_code: str = Field(min_length=1, max_length=64)
    format: Literal["short_answer", "multiple_choice", "reasoning"]
    prompt: str = Field(min_length=1, max_length=400)
    choices: list[str] | None = None


class QuestionSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[QuestionDraft] = Field(min_length=1, max_length=8)


class MisconceptionHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=400)
    evidence: str = Field(min_length=1, max_length=400)
    confidence: Literal["low", "medium", "high"]


class ItemJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_code: str = Field(min_length=1, max_length=64)
    answer_verdict: Literal["correct", "partial", "incorrect", "unanswered"]
    reasoning_verdict: Literal["sound", "partial", "weak", "absent", "uncertain"]
    understanding: Literal["none", "partial", "solid", "uncertain"]
    confidence: Literal["low", "medium", "high"]
    misconception: MisconceptionHypothesis | None = None


class JudgmentSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    judgments: list[ItemJudgment] = Field(min_length=1, max_length=8)
