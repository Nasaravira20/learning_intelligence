from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class PedagogySelection(Base):
    __tablename__ = "pedagogy_selections"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_pedagogy_selections_revision"),
        CheckConstraint("status IN ('active', 'superseded')", name="ck_pedagogy_selections_status"),
        CheckConstraint("controls_teaching = false", name="ck_pedagogy_selections_do_not_teach"),
        CheckConstraint("length(btrim(rationale)) > 0", name="ck_pedagogy_selections_rationale_not_blank"),
        CheckConstraint("length(btrim(situation)) > 0", name="ck_pedagogy_selections_situation_not_blank"),
        UniqueConstraint("session_id", "revision", name="uq_pedagogy_selections_session_revision"),
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
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    registry_version: Mapped[str] = mapped_column(String(32), nullable=False)
    situation: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supporting_strategy_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    sequence: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    success_signals: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    fallback_strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    controls_teaching: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    production_primary_strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rejected: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
