from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.evaluation import EvaluationAttempt, MasteryRecord


class ResponseInput(BaseModel):
    answer_text: str = Field(min_length=1, max_length=2000)
    reasoning_text: str = Field(min_length=1, max_length=2000)


class EvaluationRead(BaseModel):
    id: UUID
    session_id: UUID
    revision: int
    status: str
    session_status: str
    objective_code: str
    prompt: str
    rubric: list[str]
    decision: str | None
    credit: str | None
    feedback: str | None
    answer_verdict: str | None
    reasoning_verdict: str | None
    understanding: str | None
    remediation_strategy: str | None
    misconception_evidence: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_parts(
        cls,
        attempt: EvaluationAttempt,
        record: MasteryRecord | None,
        session_status: str,
    ) -> EvaluationRead:
        return cls(
            id=attempt.id,
            session_id=attempt.session_id,
            revision=attempt.revision,
            status=attempt.status,
            session_status=session_status,
            objective_code=attempt.objective_code,
            prompt=attempt.prompt,
            rubric=list(attempt.rubric),
            decision=record.decision if record else None,
            credit=f"{record.credit:.3f}" if record else None,
            feedback=record.feedback if record else None,
            answer_verdict=record.answer_verdict if record else None,
            reasoning_verdict=record.reasoning_verdict if record else None,
            understanding=record.understanding if record else None,
            remediation_strategy=record.remediation_strategy_id if record else None,
            misconception_evidence=record.misconception_evidence if record else None,
            created_at=attempt.created_at,
            updated_at=attempt.updated_at,
        )
