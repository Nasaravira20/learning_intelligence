from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(254), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )

    profile: Mapped[LearnerProfile] = relationship(back_populates="user")
    auth_sessions: Mapped[list[AuthSession]] = relationship(back_populates="user")


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(display_name)) > 0",
            name="ck_learner_display_name_not_blank",
        ),
        CheckConstraint(
            "background_note IS NULL OR length(btrim(background_note)) > 0",
            name="ck_learner_background_note_not_blank",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    background_note: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    user: Mapped[User] = relationship(back_populates="profile")
    sessions: Mapped[list[LearningSession]] = relationship(back_populates="learner")


class LearningTopic(Base):
    __tablename__ = "learning_topics"
    __table_args__ = (
        CheckConstraint("length(btrim(title)) > 0", name="ck_learning_topics_title_not_blank"),
        CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="ck_learning_topics_slug_format",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )

    sessions: Mapped[list[LearningSession]] = relationship(back_populates="topic")


class LearningSession(Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('TOPIC_SELECTED', 'DIAGNOSING', 'PLAN_READY')",
            name="ck_learning_sessions_status",
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
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="TOPIC_SELECTED")
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
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    learner: Mapped[LearnerProfile] = relationship(back_populates="sessions")
    topic: Mapped[LearningTopic] = relationship(back_populates="sessions")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="auth_sessions")


class AiUsageRecord(Base):
    __tablename__ = "ai_usage_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('succeeded', 'failed', 'blocked')",
            name="ck_ai_usage_status",
        ),
        CheckConstraint(
            "category IN ('smoke', 'development', 'teaching', 'evaluation', 'demo')",
            name="ck_ai_usage_category",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    task: Mapped[str] = mapped_column(String(64), nullable=False)
    model_id: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    action_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 8), nullable=False, default=0)
    error_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class AiModelCheck(Base):
    __tablename__ = "ai_model_checks"
    __table_args__ = (
        CheckConstraint("status IN ('passed', 'failed')", name="ck_ai_model_checks_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    check_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
