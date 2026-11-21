from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.teaching import TeachingActivity, TeachingHint, TeachingLesson

AttemptOutcome = Literal["correct", "incorrect", "struggled"]


class AttemptInput(BaseModel):
    outcome: AttemptOutcome
    answer_text: str = Field(min_length=1, max_length=2000)


class HintRead(BaseModel):
    position: int
    text: str


class ActivityRead(BaseModel):
    id: UUID
    position: int
    strategy_id: str
    kind: str
    title: str
    prompt: str
    example: str | None
    worked_steps: list[str]
    support_level: str
    status: str
    hints_available: int
    hints_revealed: list[HintRead]
    inserted_for_struggle: bool


class LessonRead(BaseModel):
    id: UUID
    session_id: UUID
    selection_id: UUID
    objective_code: str
    status: str
    session_status: str
    review_status: str
    strategy_ids: list[str]
    current_activity_id: UUID | None
    activities: list[ActivityRead]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_parts(
        cls,
        lesson: TeachingLesson,
        activities: list[tuple[TeachingActivity, list[TeachingHint]]],
        session_status: str,
    ) -> LessonRead:
        reads: list[ActivityRead] = []
        current_id: UUID | None = None
        strategy_ids: set[str] = set()
        for activity, hints in activities:
            strategy_ids.add(activity.strategy_id)
            revealed = [
                HintRead(position=hint.position, text=hint.text)
                for hint in hints
                if hint.position < activity.hints_revealed
            ]
            if activity.status == "current":
                current_id = activity.id
            reads.append(
                ActivityRead(
                    id=activity.id,
                    position=activity.position,
                    strategy_id=activity.strategy_id,
                    kind=activity.kind,
                    title=activity.title,
                    prompt=activity.prompt,
                    example=activity.example,
                    worked_steps=list(activity.worked_steps),
                    support_level=activity.support_level,
                    status=activity.status,
                    hints_available=len(hints),
                    hints_revealed=revealed,
                    inserted_for_struggle=activity.inserted_for_struggle,
                )
            )
        return cls(
            id=lesson.id,
            session_id=lesson.session_id,
            selection_id=lesson.selection_id,
            objective_code=lesson.objective_code,
            status=lesson.status,
            session_status=session_status,
            review_status=lesson.review_status,
            strategy_ids=sorted(strategy_ids),
            current_activity_id=current_id,
            activities=reads,
            created_at=lesson.created_at,
            updated_at=lesson.updated_at,
        )
