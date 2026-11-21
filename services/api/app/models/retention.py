from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class RevisionReview(Base):
    __tablename__ = "revision_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'in_progress', 'completed')",
            name="ck_revision_reviews_status",
        ),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ('recalled', 'failed', 'needs_review', 'further_assessment')",
            name="ck_revision_reviews_outcome",
        ),
        CheckConstraint("interval_index >= 0", name="ck_revision_reviews_interval"),
        CheckConstraint("length(btrim(objective_code)) > 0", name="ck_revision_reviews_objective_not_blank"),
        CheckConstraint("length(btrim(timezone)) > 0", name="ck_revision_reviews_timezone_not_blank"),
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
    )
    objective_code: Mapped[str] = mapped_column(String(80), nullable=False)
    interval_index: Mapped[int] = mapped_column(Integer, nullable=False)
    due_on: Mapped[date] = mapped_column(Date, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    was_missed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    mastery_record_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("mastery_records.id", ondelete="SET NULL"),
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
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
