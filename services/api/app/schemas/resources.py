from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class LearnerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("display_name")
    @classmethod
    def require_display_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Display name is required.")
        return cleaned


class LearnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    created_at: datetime
    updated_at: datetime


class TopicCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=80, pattern=SLUG_PATTERN)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def require_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title is required.")
        return cleaned

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    description: str | None
    created_at: datetime


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: UUID
    topic_id: UUID


class SessionRead(BaseModel):
    id: UUID
    learner_id: UUID
    topic_id: UUID
    learner_name: str
    topic_title: str
    topic_slug: str
    status: str
    created_at: datetime
    updated_at: datetime
    resumed_at: datetime | None
