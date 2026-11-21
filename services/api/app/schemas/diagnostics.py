from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

QuestionFormat = Literal["short_answer", "multiple_choice", "reasoning"]
AnswerVerdict = Literal["correct", "partial", "incorrect", "unanswered"]
ReasoningVerdict = Literal["sound", "partial", "weak", "absent", "uncertain"]
Understanding = Literal["none", "partial", "solid", "uncertain"]
StartingPoint = Literal["beginner", "partial", "uncertain"]
AttemptStatus = Literal["in_progress", "completed"]


def _required(value: str, message: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(message)
    return cleaned


class ObjectiveCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    statement: str = Field(min_length=1, max_length=300)
    concept: str = Field(min_length=1, max_length=120)
    position: int | None = Field(default=None, ge=0, le=100)
    prerequisite_codes: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("code", "statement", "concept")
    @classmethod
    def clean_required(cls, value: str) -> str:
        return _required(value, "This field is required.")

    @field_validator("prerequisite_codes")
    @classmethod
    def clean_codes(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Prerequisite codes must be unique.")
        return cleaned


class ObjectiveRead(BaseModel):
    id: UUID
    topic_id: UUID
    code: str
    statement: str
    concept: str
    position: int
    prerequisite_codes: list[str]
    created_at: datetime


class ResponseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    answer_text: str = Field(default="", max_length=1000)
    reasoning_text: str = Field(default="", max_length=1000)

    @field_validator("answer_text", "reasoning_text")
    @classmethod
    def trim(cls, value: str) -> str:
        return value.strip()


class ResponseBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    responses: list[ResponseInput] = Field(min_length=1, max_length=8)


class DiagnosisQuestionRead(BaseModel):
    id: UUID
    objective_code: str
    objective_statement: str
    concept: str
    format: QuestionFormat
    prompt: str
    choices: list[str] | None
    position: int


class DiagnosisJudgmentRead(BaseModel):
    question_id: UUID
    objective_code: str
    answer_text: str
    reasoning_text: str
    answer_verdict: AnswerVerdict
    reasoning_verdict: ReasoningVerdict
    understanding: Understanding
    confidence: float
    needs_review: bool
    confirmed: bool


class DiagnosisMisconceptionRead(BaseModel):
    id: UUID
    concept: str
    description: str
    evidence: str | None
    confidence: float
    confirmed: bool


class DiagnosisReport(BaseModel):
    id: UUID
    session_id: UUID
    topic_id: UUID
    status: AttemptStatus
    session_status: str
    starting_point: StartingPoint | None
    confidence: float | None
    summary: str | None
    first_unmet_objective_code: str | None
    questions: list[DiagnosisQuestionRead]
    judgments: list[DiagnosisJudgmentRead]
    misconceptions: list[DiagnosisMisconceptionRead]
