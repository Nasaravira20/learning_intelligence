"""Revision reviews and retention session states."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_retention"
down_revision: Union[str, None] = "0009_evaluation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = sa.dialects.postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.drop_constraint("ck_learning_sessions_status", "learning_sessions", type_="check")
    op.create_check_constraint(
        "ck_learning_sessions_status",
        "learning_sessions",
        "status IN ('TOPIC_SELECTED', 'DIAGNOSING', 'PLAN_READY', 'TEACHING', "
        "'EVALUATING', 'REMEDIATION', 'MASTERED', 'NEEDS_REVIEW', "
        "'RETENTION_ASSESSMENT', 'MASTERY_UPDATED')",
    )
    op.create_table(
        "revision_reviews",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("session_id", uuid, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("topic_id", uuid, nullable=False),
        sa.Column("objective_code", sa.String(length=80), nullable=False),
        sa.Column("interval_index", sa.Integer(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("was_missed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("rubric", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("reasoning_text", sa.Text(), nullable=True),
        sa.Column("mastery_record_id", uuid, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('scheduled', 'in_progress', 'completed')",
            name="ck_revision_reviews_status",
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('recalled', 'failed', 'needs_review', 'further_assessment')",
            name="ck_revision_reviews_outcome",
        ),
        sa.CheckConstraint("interval_index >= 0", name="ck_revision_reviews_interval"),
        sa.CheckConstraint("length(btrim(objective_code)) > 0", name="ck_revision_reviews_objective_not_blank"),
        sa.CheckConstraint("length(btrim(timezone)) > 0", name="ck_revision_reviews_timezone_not_blank"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mastery_record_id"], ["mastery_records.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_revision_reviews_session_id", "revision_reviews", ["session_id"])
    op.create_index("ix_revision_reviews_learner_id", "revision_reviews", ["learner_id"])
    op.create_index(
        "uq_revision_reviews_one_open",
        "revision_reviews",
        ["session_id", "objective_code"],
        unique=True,
        postgresql_where=sa.text("status IN ('scheduled', 'in_progress')"),
    )


def downgrade() -> None:
    op.drop_index("uq_revision_reviews_one_open", table_name="revision_reviews")
    op.drop_index("ix_revision_reviews_learner_id", table_name="revision_reviews")
    op.drop_index("ix_revision_reviews_session_id", table_name="revision_reviews")
    op.drop_table("revision_reviews")
    op.execute(
        "UPDATE learning_sessions SET status = 'MASTERED' "
        "WHERE status IN ('RETENTION_ASSESSMENT', 'MASTERY_UPDATED')"
    )
    op.drop_constraint("ck_learning_sessions_status", "learning_sessions", type_="check")
    op.create_check_constraint(
        "ck_learning_sessions_status",
        "learning_sessions",
        "status IN ('TOPIC_SELECTED', 'DIAGNOSING', 'PLAN_READY', 'TEACHING', "
        "'EVALUATING', 'REMEDIATION', 'MASTERED', 'NEEDS_REVIEW')",
    )
