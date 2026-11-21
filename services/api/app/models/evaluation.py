from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class MasteryRecord(Base):
    __tablename__ = "mastery_records"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('mastered', 'remediation', 'further_assessment', 'needs_review')",
            name="ck_mastery_records_decision",
        ),
        CheckConstraint(
            "(decision = 'mastered' AND evidence_kind = 'observed' AND credit = 1) "
            "OR (decision <> 'mastered' AND evidence_kind = 'inferred')",
            name="ck_mastery_records_evidence",
        ),
        CheckConstraint("credit >= 0 AND credit <= 1", name="ck_mastery_records_credit"),
        CheckConstraint("length(btrim(feedback)) > 0", name="ck_mastery_records_feedback_not_blank"),
        CheckConstraint("length(btrim(objective_code)) > 0", name="ck_mastery_records_objective_not_blank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learner_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    objective_code: Mapped[str] = mapped_column(String(80), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    answer_verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    reasoning_verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    understanding: Mapped[str] = mapped_column(String(16), nullable=False)
    remediation_strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    misconception_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )


class EvaluationAttempt(Base):
    __tablename__ = "evaluation_attempts"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_evaluation_attempts_revision"),
        CheckConstraint("status IN ('open', 'completed')", name="ck_evaluation_attempts_status"),
        CheckConstraint("length(btrim(prompt)) > 0", name="ck_evaluation_attempts_prompt_not_blank"),
        CheckConstraint("length(btrim(objective_code)) > 0", name="ck_evaluation_attempts_objective_not_blank"),
        UniqueConstraint("session_id", "revision", name="uq_evaluation_attempts_revision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learner_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("teaching_lessons.id", ondelete="CASCADE"),
        nullable=False,
    )
    mastery_record_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("mastery_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    objective_code: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    rubric: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
