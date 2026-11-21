"""Persist a pedagogy selection without starting teaching."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_pedagogy_selections"
down_revision: Union[str, None] = "0006_learning_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "pedagogy_selections",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("session_id", uuid, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'active'")),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("registry_version", sa.String(length=32), nullable=False),
        sa.Column("situation", sa.String(length=64), nullable=False),
        sa.Column("primary_strategy_id", sa.String(length=64), nullable=True),
        sa.Column("supporting_strategy_ids", postgresql.JSONB(), nullable=False),
        sa.Column("sequence", postgresql.JSONB(), nullable=False),
        sa.Column("success_signals", postgresql.JSONB(), nullable=False),
        sa.Column("fallback_strategy_id", sa.String(length=64), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("controls_teaching", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("production_primary_strategy_id", sa.String(length=64), nullable=True),
        sa.Column("rejected", postgresql.JSONB(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("revision >= 1", name="ck_pedagogy_selections_revision"),
        sa.CheckConstraint("status IN ('active', 'superseded')", name="ck_pedagogy_selections_status"),
        sa.CheckConstraint("controls_teaching = false", name="ck_pedagogy_selections_do_not_teach"),
        sa.CheckConstraint("length(btrim(rationale)) > 0", name="ck_pedagogy_selections_rationale_not_blank"),
        sa.CheckConstraint("length(btrim(situation)) > 0", name="ck_pedagogy_selections_situation_not_blank"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "revision", name="uq_pedagogy_selections_session_revision"),
    )
    op.create_index("ix_pedagogy_selections_session_id", "pedagogy_selections", ["session_id"])
    op.create_index("ix_pedagogy_selections_learner_id", "pedagogy_selections", ["learner_id"])
    op.create_index(
        "uq_pedagogy_selections_one_active",
        "pedagogy_selections",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_pedagogy_selections_one_active", table_name="pedagogy_selections")
    op.drop_index("ix_pedagogy_selections_learner_id", table_name="pedagogy_selections")
    op.drop_index("ix_pedagogy_selections_session_id", table_name="pedagogy_selections")
    op.drop_table("pedagogy_selections")
