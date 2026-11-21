from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.learner.evidence import is_confirmed, pair_is_valid

EvidenceKind = Literal["observed", "inferred"]
Provenance = Literal["learner_response", "assessment", "system_estimate", "learner_report"]
GoalStatus = Literal["active", "completed", "archived"]
Pace = Literal["unhurried", "steady", "intensive"]
ExplanationDetail = Literal["concise", "balanced", "thorough"]
MisconceptionStatus = Literal["open", "resolved", "rejected"]
AssessmentOutcome = Literal["recorded", "correct", "partial", "incorrect", "unanswered"]
ActivityKind = Literal["explanation", "practice", "review", "note"]


def _required_text(value: str, message: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(message)
    return cleaned


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _confidence(value: Decimal) -> Decimal:
    quantized = value.quantize(Decimal("0.001"))
    if quantized < 0 or quantized > 1:
        raise ValueError("Confidence must be between 0 and 1.")
    return quantized


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=80)
    background_note: str | None = Field(default=None, max_length=500)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _required_text(value, "Display name is required.")

    @field_validator("background_note")
    @classmethod
    def clean_background_note(cls, value: str | None) -> str | None:
        return _optional_text(value)

    @model_validator(mode="after")
    def require_a_change(self) -> "ProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide a display name or a background note to update.")
        if "display_name" in self.model_fields_set and self.display_name is None:
            raise ValueError("Display name is required.")
        return self


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    background_note: str | None
    created_at: datetime
    updated_at: datetime


class PreferenceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pace: Pace
    explanation_detail: ExplanationDetail
    practice_first: bool = False
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        return _optional_text(value)


class PreferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pace: Pace
    explanation_detail: ExplanationDetail
    practice_first: bool
    notes: str | None
    updated_at: datetime


class GoalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1, max_length=300)
    topic_id: UUID | None = None

    @field_validator("statement")
    @classmethod
    def clean_statement(cls, value: str) -> str:
        return _required_text(value, "A learning goal needs a statement.")


class GoalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str | None = Field(default=None, max_length=300)
    status: GoalStatus | None = None

    @field_validator("statement")
    @classmethod
    def clean_statement(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _required_text(value, "A learning goal needs a statement.")

    @model_validator(mode="after")
    def require_a_change(self) -> "GoalUpdate":
        if self.statement is None and self.status is None:
            raise ValueError("Provide a statement or a status to update.")
        return self


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID | None
    statement: str
    status: GoalStatus
    created_at: datetime
    updated_at: datetime


class EvidenceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic_id: UUID
    concept: str = Field(min_length=1, max_length=120)
    evidence_kind: EvidenceKind
    confidence: Decimal = Field(ge=0, le=1, max_digits=4, decimal_places=3)
    provenance: Provenance

    @field_validator("concept")
    @classmethod
    def clean_concept(cls, value: str) -> str:
        return _required_text(value, "Concept is required.")

    @field_validator("confidence")
    @classmethod
    def quantize_confidence(cls, value: Decimal) -> Decimal:
        return _confidence(value)

    @model_validator(mode="after")
    def evidence_matches_provenance(self) -> "EvidenceWrite":
        if not pair_is_valid(self.evidence_kind, self.provenance):
            raise ValueError("The evidence kind does not match its provenance. Inferred knowledge is not confirmed.")
        return self


class KnowledgeCreate(EvidenceWrite):
    summary: str = Field(min_length=1, max_length=1000)

    @field_validator("summary")
    @classmethod
    def clean_summary(cls, value: str) -> str:
        return _required_text(value, "Summary is required.")


class KnowledgeCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str | None = Field(default=None, max_length=120)
    summary: str | None = Field(default=None, max_length=1000)
    confidence: Decimal | None = Field(default=None, ge=0, le=1, max_digits=4, decimal_places=3)
    correction_note: str = Field(min_length=1, max_length=500)

    @field_validator("concept")
    @classmethod
    def clean_concept(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _required_text(value, "Concept is required.")

    @field_validator("summary")
    @classmethod
    def clean_summary(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _required_text(value, "Summary is required.")

    @field_validator("confidence")
    @classmethod
    def quantize_confidence(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return _confidence(value)

    @field_validator("correction_note")
    @classmethod
    def clean_note(cls, value: str) -> str:
        return _required_text(value, "A correction needs a note.")

    @model_validator(mode="after")
    def require_a_change(self) -> "KnowledgeCorrection":
        if self.concept is None and self.summary is None and self.confidence is None:
            raise ValueError("A correction needs a concept, summary, or confidence change.")
        return self


class KnowledgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    concept: str
    summary: str
    evidence_kind: EvidenceKind
    provenance: Provenance
    confidence: float
    correction_note: str | None
    corrected_at: datetime | None
    replaces_id: UUID | None
    created_at: datetime

    @field_validator("confidence", mode="before")
    @classmethod
    def coerce_confidence(cls, value: object) -> float:
        return float(value)  # type: ignore[arg-type]

    @computed_field
    @property
    def confirmed(self) -> bool:
        return is_confirmed(self.evidence_kind)


class MisconceptionCreate(EvidenceWrite):
    description: str = Field(min_length=1, max_length=1000)
    supporting_note: str | None = Field(default=None, max_length=1000)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        return _required_text(value, "Description is required.")

    @field_validator("supporting_note")
    @classmethod
    def clean_support(cls, value: str | None) -> str | None:
        return _optional_text(value)


class MisconceptionCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, max_length=1000)
    status: MisconceptionStatus | None = None
    correction_note: str = Field(min_length=1, max_length=500)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _required_text(value, "Description is required.")

    @field_validator("correction_note")
    @classmethod
    def clean_note(cls, value: str) -> str:
        return _required_text(value, "A correction needs a note.")

    @model_validator(mode="after")
    def require_a_change(self) -> "MisconceptionCorrection":
        if self.description is None and self.status is None:
            raise ValueError("A correction needs a description or a status.")
        return self


class MisconceptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    concept: str
    description: str
    evidence_kind: EvidenceKind
    provenance: Provenance
    confidence: float
    supporting_note: str | None
    status: MisconceptionStatus
    correction_note: str | None
    corrected_at: datetime | None
    replaces_id: UUID | None
    created_at: datetime

    @field_validator("confidence", mode="before")
    @classmethod
    def coerce_confidence(cls, value: object) -> float:
        return float(value)  # type: ignore[arg-type]

    @computed_field
    @property
    def confirmed(self) -> bool:
        return is_confirmed(self.evidence_kind)


class AssessmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic_id: UUID
    session_id: UUID | None = None
    prompt_summary: str = Field(min_length=1, max_length=500)
    response_summary: str = Field(min_length=1, max_length=2000)
    outcome: AssessmentOutcome = "recorded"

    @field_validator("prompt_summary")
    @classmethod
    def clean_prompt(cls, value: str) -> str:
        return _required_text(value, "Prompt summary is required.")

    @field_validator("response_summary")
    @classmethod
    def clean_response(cls, value: str) -> str:
        return _required_text(value, "Response summary is required.")


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    session_id: UUID | None
    prompt_summary: str
    response_summary: str
    outcome: AssessmentOutcome
    created_at: datetime


class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic_id: UUID | None = None
    session_id: UUID | None = None
    activity_kind: ActivityKind
    summary: str = Field(min_length=1, max_length=500)
    occurred_at: datetime | None = None

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("occurred_at must include a timezone.")
        return value

    @field_validator("summary")
    @classmethod
    def clean_summary(cls, value: str) -> str:
        return _required_text(value, "Activity summary is required.")


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID | None
    session_id: UUID | None
    activity_kind: ActivityKind
    summary: str
    occurred_at: datetime
    created_at: datetime


class LearnerDashboard(BaseModel):
    profile: ProfileRead
    preferences: PreferenceRead | None
    goals: list[GoalRead]
    knowledge: list[KnowledgeRead]
    misconceptions: list[MisconceptionRead]
    assessments: list[AssessmentRead]
    activities: list[ActivityRead]


class SessionHistoryRead(BaseModel):
    session_id: UUID
    learner_id: UUID
    topic_id: UUID
    topic_title: str
    profile: ProfileRead
    preferences: PreferenceRead | None
    goals: list[GoalRead]
    knowledge: list[KnowledgeRead]
    misconceptions: list[MisconceptionRead]
    assessments: list[AssessmentRead]
    activities: list[ActivityRead]
