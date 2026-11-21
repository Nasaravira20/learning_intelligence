from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class TopicConcept(Base):
    __tablename__ = "topic_concepts"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_topic_concepts_name_not_blank"),
        CheckConstraint("length(btrim(name_key)) > 0", name="ck_topic_concepts_name_key_not_blank"),
        CheckConstraint("length(btrim(summary)) > 0", name="ck_topic_concepts_summary_not_blank"),
        CheckConstraint("position >= 0", name="ck_topic_concepts_position"),
        UniqueConstraint("topic_id", "name_key", name="uq_topic_concepts_topic_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_key: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )


class LearningPlan(Base):
    __tablename__ = "learning_plans"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_learning_plans_revision"),
        CheckConstraint("status IN ('active', 'superseded')", name="ck_learning_plans_status"),
        CheckConstraint("length(btrim(summary)) > 0", name="ck_learning_plans_summary_not_blank"),
        UniqueConstraint("session_id", "revision", name="uq_learning_plans_session_revision"),
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
        index=True,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    diagnostic_attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("diagnostic_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    current_step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_plan_steps.id", ondelete="SET NULL", use_alter=True, name="fk_learning_plans_current_step_id"),
        nullable=True,
    )
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


class LearningPlanStep(Base):
    __tablename__ = "learning_plan_steps"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_learning_plan_steps_position"),
        CheckConstraint(
            "status IN ('satisfied', 'current', 'upcoming')",
            name="ck_learning_plan_steps_status",
        ),
        CheckConstraint("evidence IN ('observed', 'none')", name="ck_learning_plan_steps_evidence"),
        CheckConstraint(
            "length(btrim(completion_criteria)) > 0",
            name="ck_learning_plan_steps_criteria_not_blank",
        ),
        CheckConstraint(
            "(status = 'satisfied' AND evidence = 'observed') OR (status <> 'satisfied' AND evidence = 'none')",
            name="ck_learning_plan_steps_skip_needs_evidence",
        ),
        UniqueConstraint("plan_id", "position", name="uq_learning_plan_steps_position"),
        UniqueConstraint("plan_id", "objective_id", name="uq_learning_plan_steps_objective"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("topic_concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    objective_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence: Mapped[str] = mapped_column(String(16), nullable=False)
    completion_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
