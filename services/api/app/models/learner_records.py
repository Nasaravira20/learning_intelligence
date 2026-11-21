from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base
from app.learner.evidence import EVIDENCE_CONSTRAINT


class LearningGoal(Base):
    __tablename__ = "learning_goals"
    __table_args__ = (
        CheckConstraint("length(btrim(statement)) > 0", name="ck_learning_goals_statement_not_blank"),
        CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name="ck_learning_goals_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learner_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    statement: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
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


class LearningPreference(Base):
    __tablename__ = "learning_preferences"
    __table_args__ = (
        CheckConstraint(
            "pace IN ('unhurried', 'steady', 'intensive')",
            name="ck_learning_preferences_pace",
        ),
        CheckConstraint(
            "explanation_detail IN ('concise', 'balanced', 'thorough')",
            name="ck_learning_preferences_detail",
        ),
        CheckConstraint(
            "notes IS NULL OR length(btrim(notes)) > 0",
            name="ck_learning_preferences_notes_not_blank",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learner_profiles.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    pace: Mapped[str] = mapped_column(String(16), nullable=False)
    explanation_detail: Mapped[str] = mapped_column(String(16), nullable=False)
    practice_first: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class LearnerKnowledge(Base):
    __tablename__ = "learner_knowledge"
    __table_args__ = (
        CheckConstraint("length(btrim(concept)) > 0", name="ck_learner_knowledge_concept_not_blank"),
        CheckConstraint("length(btrim(summary)) > 0", name="ck_learner_knowledge_summary_not_blank"),
        CheckConstraint(EVIDENCE_CONSTRAINT, name="ck_learner_knowledge_evidence"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_learner_knowledge_confidence"),
        CheckConstraint(
            "corrected_at IS NULL OR length(btrim(correction_note)) > 0",
            name="ck_learner_knowledge_correction_note",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    concept: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False)
    correction_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaces_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learner_knowledge.id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )


class MisconceptionRecord(Base):
    __tablename__ = "misconception_records"
    __table_args__ = (
        CheckConstraint("length(btrim(concept)) > 0", name="ck_misconception_concept_not_blank"),
        CheckConstraint("length(btrim(description)) > 0", name="ck_misconception_description_not_blank"),
        CheckConstraint(EVIDENCE_CONSTRAINT, name="ck_misconception_evidence"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_misconception_confidence"),
        CheckConstraint(
            "status IN ('open', 'resolved', 'rejected')",
            name="ck_misconception_status",
        ),
        CheckConstraint(
            "corrected_at IS NULL OR length(btrim(correction_note)) > 0",
            name="ck_misconception_correction_note",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    concept: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False)
    supporting_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    correction_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaces_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("misconception_records.id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )


class AssessmentRecord(Base):
    __tablename__ = "assessment_records"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(prompt_summary)) > 0",
            name="ck_assessment_prompt_not_blank",
        ),
        CheckConstraint(
            "length(btrim(response_summary)) > 0",
            name="ck_assessment_response_not_blank",
        ),
        CheckConstraint(
            "outcome IN ('recorded', 'correct', 'partial', 'incorrect', 'unanswered')",
            name="ck_assessment_outcome",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prompt_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    response_summary: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="recorded")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )


class LearningActivity(Base):
    __tablename__ = "learning_activities"
    __table_args__ = (
        CheckConstraint("length(btrim(summary)) > 0", name="ck_learning_activities_summary_not_blank"),
        CheckConstraint(
            "activity_kind IN ('explanation', 'practice', 'review', 'note')",
            name="ck_learning_activities_kind",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learner_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    activity_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
