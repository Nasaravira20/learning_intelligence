from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.retention import RevisionReview
from app.retention.policy import review_timing


class ResponseInput(BaseModel):
    answer_text: str = Field(min_length=1, max_length=2000)
    reasoning_text: str = Field(min_length=1, max_length=2000)


class ReviewRead(BaseModel):
    id: UUID
    session_id: UUID
    objective_code: str
    interval_index: int
    due_on: str
    timezone: str
    status: str
    timing: str
    was_missed: bool
    outcome: str | None
    session_status: str
    prompt: str | None
    rubric: list[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: RevisionReview, session_status: str, moment: datetime) -> ReviewRead:
        timing = row.status if row.status != "scheduled" else review_timing(row.due_on, moment, row.timezone)
        if row.status == "completed":
            timing = "completed"
        return cls(
            id=row.id,
            session_id=row.session_id,
            objective_code=row.objective_code,
            interval_index=row.interval_index,
            due_on=row.due_on.isoformat(),
            timezone=row.timezone,
            status=row.status,
            timing=timing,
            was_missed=row.was_missed,
            outcome=row.outcome,
            session_status=session_status,
            prompt=row.prompt,
            rubric=list(row.rubric or []),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class MasteryHistoryRead(BaseModel):
    id: UUID
    objective_code: str
    decision: str
    credit: str
    evidence_kind: str
    created_at: datetime


class RetentionRead(BaseModel):
    session_status: str
    reviews: list[ReviewRead]
    mastery: list[MasteryHistoryRead]
