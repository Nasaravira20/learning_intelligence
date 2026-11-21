from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ReviewStatus = Literal["reviewed", "pending_human_review"]
AccessType = Literal["open_access", "free_to_read", "publisher", "index_only"]
VerificationMethod = Literal["crossref", "publisher_page", "eric_record"]

P0_STRATEGY_IDS = (
    "retrieval_practice",
    "spaced_practice",
    "worked_examples",
    "guided_practice",
    "scaffolding",
    "small_step_instruction",
    "checks_for_understanding",
    "formative_feedback",
    "self_explanation",
    "concrete_examples",
    "elaborative_interrogation",
    "mastery_learning",
)

SUMMARY_LIMIT = 800


class MetadataVerification(BaseModel):
    checked_on: date
    method: VerificationMethod
    identifier: str = Field(min_length=8)


class SourceRecord(BaseModel):
    source_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    title: str = Field(min_length=3)
    authors: list[str] = Field(min_length=1)
    year: int = Field(ge=1900, le=2100)
    publication: str = Field(min_length=3)
    doi: str | None = None
    url: str = Field(min_length=8)
    access_type: AccessType
    license: str = Field(min_length=3)
    retrieved_date: date
    relevant_sections: list[str] = Field(min_length=1)
    evidence_notes: str = Field(min_length=40, max_length=SUMMARY_LIMIT)
    limitations: list[str] = Field(min_length=1)
    review_status: ReviewStatus
    reviewed_by: str | None = None
    metadata_verification: MetadataVerification

    @field_validator("authors", "relevant_sections", "limitations")
    @classmethod
    def non_blank_items(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values]
        if any(not item for item in cleaned):
            raise ValueError("List entries must be non-blank.")
        return cleaned

    @field_validator("evidence_notes")
    @classmethod
    def original_summary(cls, value: str) -> str:
        if '"' in value or "“" in value or "”" in value:
            raise ValueError("Evidence notes must be an original summary without quotations.")
        return value.strip()

    @model_validator(mode="after")
    def identifier_matches_check(self) -> SourceRecord:
        if self.metadata_verification.method == "crossref":
            if not self.doi or self.metadata_verification.identifier != self.doi:
                raise ValueError("Crossref verification must repeat the source DOI.")
        elif self.metadata_verification.identifier != self.url:
            raise ValueError("Page verification must repeat the source URL.")
        if self.review_status == "reviewed" and not (self.reviewed_by and self.reviewed_by.strip()):
            raise ValueError("A reviewed source needs reviewed_by.")
        if self.review_status != "reviewed" and self.reviewed_by:
            raise ValueError("reviewed_by is only set after human review.")
        return self


class StrategyRecord(BaseModel):
    strategy_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=3)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    category: str = Field(min_length=3)
    description: str = Field(min_length=20, max_length=SUMMARY_LIMIT)
    learning_objectives: list[str] = Field(min_length=1)
    suitable_contexts: list[str] = Field(min_length=1)
    learner_conditions: list[str] = Field(min_length=1)
    avoid_or_modify_conditions: list[str] = Field(min_length=1)
    implementation_steps: list[str] = Field(min_length=1)
    assessment_signals: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    sources: list[str] = Field(min_length=1)
    review_status: ReviewStatus
    reviewed_by: str | None = None

    @field_validator(
        "learning_objectives",
        "suitable_contexts",
        "learner_conditions",
        "avoid_or_modify_conditions",
        "implementation_steps",
        "assessment_signals",
        "limitations",
        "sources",
    )
    @classmethod
    def non_blank_items(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values]
        if any(not item for item in cleaned):
            raise ValueError("List entries must be non-blank.")
        return cleaned

    @field_validator("description")
    @classmethod
    def no_quotations(cls, value: str) -> str:
        if '"' in value or "“" in value or "”" in value:
            raise ValueError("Descriptions must not contain quotations.")
        return value.strip()

    @model_validator(mode="after")
    def review_identity(self) -> StrategyRecord:
        if self.review_status == "reviewed" and not (self.reviewed_by and self.reviewed_by.strip()):
            raise ValueError("A reviewed strategy needs reviewed_by.")
        if self.review_status != "reviewed" and self.reviewed_by:
            raise ValueError("reviewed_by is only set after human review.")
        return self


class RegistryManifest(BaseModel):
    registry_version: str = Field(pattern=r"^\d{4}\.\d{2}\.\d{2}$")
    strategies: dict[str, str] = Field(min_length=1)
