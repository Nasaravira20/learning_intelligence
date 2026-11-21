from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class TeachingLesson(Base):
    __tablename__ = "teaching_lessons"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed')", name="ck_teaching_lessons_status"),
        CheckConstraint(
            "review_status = 'pending_human_review'",
            name="ck_teaching_lessons_review_pending",
        ),
        CheckConstraint("length(btrim(objective_code)) > 0", name="ck_teaching_lessons_objective_not_blank"),
        UniqueConstraint("session_id", name="uq_teaching_lessons_session"),
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
    selection_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pedagogy_selections.id", ondelete="CASCADE"),
        nullable=False,
    )
    objective_code: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_human_review")
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


class TeachingActivity(Base):
    __tablename__ = "teaching_activities"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_teaching_activities_position"),
        CheckConstraint("hints_revealed >= 0", name="ck_teaching_activities_hints_revealed"),
        CheckConstraint(
            "kind IN ('explanation', 'concrete_example', 'worked_example', 'guided_practice', "
            "'independent_practice', 'check_for_understanding', 'self_explanation')",
            name="ck_teaching_activities_kind",
        ),
        CheckConstraint(
            "support_level IN ('high', 'medium', 'low')",
            name="ck_teaching_activities_support",
        ),
        CheckConstraint(
            "status IN ('upcoming', 'current', 'completed')",
            name="ck_teaching_activities_status",
        ),
        CheckConstraint("length(btrim(strategy_id)) > 0", name="ck_teaching_activities_strategy_not_blank"),
        CheckConstraint("length(btrim(title)) > 0", name="ck_teaching_activities_title_not_blank"),
        CheckConstraint("length(btrim(prompt)) > 0", name="ck_teaching_activities_prompt_not_blank"),
        UniqueConstraint("lesson_id", "position", name="uq_teaching_activities_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("teaching_lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    worked_steps: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    support_level: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    hints_revealed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_for_struggle: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class TeachingHint(Base):
    __tablename__ = "teaching_hints"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_teaching_hints_position"),
        CheckConstraint("length(btrim(text)) > 0", name="ck_teaching_hints_text_not_blank"),
        CheckConstraint(
            "position > 0 OR reveals_answer = false",
            name="ck_teaching_hints_first_hides_answer",
        ),
        UniqueConstraint("activity_id", "position", name="uq_teaching_hints_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("teaching_activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    reveals_answer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class TeachingAttempt(Base):
    __tablename__ = "teaching_attempts"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('correct', 'incorrect', 'struggled')",
            name="ck_teaching_attempts_outcome",
        ),
        CheckConstraint("length(btrim(answer_text)) > 0", name="ck_teaching_attempts_answer_not_blank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("teaching_activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learner_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
