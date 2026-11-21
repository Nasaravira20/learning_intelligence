from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class LearningObjective(Base):
    __tablename__ = "learning_objectives"
    __table_args__ = (
        CheckConstraint("length(btrim(code)) > 0", name="ck_learning_objectives_code_not_blank"),
        CheckConstraint("length(btrim(statement)) > 0", name="ck_learning_objectives_statement_not_blank"),
        CheckConstraint("length(btrim(concept)) > 0", name="ck_learning_objectives_concept_not_blank"),
        CheckConstraint("position >= 0", name="ck_learning_objectives_position"),
        UniqueConstraint("topic_id", "code", name="uq_learning_objectives_topic_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    statement: Mapped[str] = mapped_column(String(300), nullable=False)
    concept: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )


class ObjectivePrerequisite(Base):
    __tablename__ = "objective_prerequisites"
    __table_args__ = (
        CheckConstraint("objective_id <> prerequisite_id", name="ck_objective_prerequisites_not_self"),
        UniqueConstraint("objective_id", "prerequisite_id", name="uq_objective_prerequisites_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    objective_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prerequisite_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class DiagnosticAttempt(Base):
    __tablename__ = "diagnostic_attempts"
    __table_args__ = (
        CheckConstraint("status IN ('in_progress', 'completed')", name="ck_diagnostic_attempts_status"),
        CheckConstraint(
            "starting_point IS NULL OR starting_point IN ('beginner', 'partial', 'uncertain')",
            name="ck_diagnostic_attempts_starting_point",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_diagnostic_attempts_confidence",
        ),
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
        index=True,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress")
    starting_point: Mapped[str | None] = mapped_column(String(16), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_unmet_objective_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_objectives.id", ondelete="SET NULL"),
        nullable=True,
    )
    hypothesis_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DiagnosticQuestion(Base):
    __tablename__ = "diagnostic_questions"
    __table_args__ = (
        CheckConstraint(
            "format IN ('short_answer', 'multiple_choice', 'reasoning')",
            name="ck_diagnostic_questions_format",
        ),
        CheckConstraint("length(btrim(prompt)) > 0", name="ck_diagnostic_questions_prompt_not_blank"),
        CheckConstraint("position >= 0", name="ck_diagnostic_questions_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("diagnostic_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    objective_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class DiagnosticResponse(Base):
    __tablename__ = "diagnostic_responses"
    __table_args__ = (
        CheckConstraint(
            "answer_verdict IN ('correct', 'partial', 'incorrect', 'unanswered')",
            name="ck_diagnostic_responses_answer",
        ),
        CheckConstraint(
            "reasoning_verdict IN ('sound', 'partial', 'weak', 'absent', 'uncertain')",
            name="ck_diagnostic_responses_reasoning",
        ),
        CheckConstraint(
            "understanding IN ('none', 'partial', 'solid', 'uncertain')",
            name="ck_diagnostic_responses_understanding",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_diagnostic_responses_confidence"),
        UniqueConstraint("question_id", name="uq_diagnostic_responses_question_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("diagnostic_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reasoning_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answer_verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    reasoning_verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    understanding: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
