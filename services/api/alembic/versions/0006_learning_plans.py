"""Topic concepts and prerequisite-aware learning plans."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_learning_plans"
down_revision: Union[str, None] = "0005_diagnostics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.drop_constraint("ck_learning_sessions_status", "learning_sessions", type_="check")
    op.create_check_constraint(
        "ck_learning_sessions_status",
        "learning_sessions",
        "status IN ('TOPIC_SELECTED', 'DIAGNOSING', 'PLAN_READY')",
    )
    op.drop_constraint("uq_diagnostic_attempts_session_id", "diagnostic_attempts", type_="unique")
    op.create_index(
        "uq_diagnostic_attempts_one_open",
        "diagnostic_attempts",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'in_progress'"),
    )
    op.create_table(
        "topic_concepts",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("topic_id", uuid, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("name_key", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_topic_concepts_name_not_blank"),
        sa.CheckConstraint("length(btrim(name_key)) > 0", name="ck_topic_concepts_name_key_not_blank"),
        sa.CheckConstraint("length(btrim(summary)) > 0", name="ck_topic_concepts_summary_not_blank"),
        sa.CheckConstraint("position >= 0", name="ck_topic_concepts_position"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("topic_id", "name_key", name="uq_topic_concepts_topic_name"),
    )
    op.create_index("ix_topic_concepts_topic_id", "topic_concepts", ["topic_id"])
    op.create_table(
        "learning_plans",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("session_id", uuid, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("topic_id", uuid, nullable=False),
        sa.Column("diagnostic_attempt_id", uuid, nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'active'")),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("current_step_id", uuid, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("revision >= 1", name="ck_learning_plans_revision"),
        sa.CheckConstraint("status IN ('active', 'superseded')", name="ck_learning_plans_status"),
        sa.CheckConstraint("length(btrim(summary)) > 0", name="ck_learning_plans_summary_not_blank"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["diagnostic_attempt_id"], ["diagnostic_attempts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "revision", name="uq_learning_plans_session_revision"),
    )
    op.create_index("ix_learning_plans_session_id", "learning_plans", ["session_id"])
    op.create_index("ix_learning_plans_learner_id", "learning_plans", ["learner_id"])
    op.create_index("ix_learning_plans_topic_id", "learning_plans", ["topic_id"])
    op.create_index(
        "uq_learning_plans_one_active",
        "learning_plans",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "learning_plan_steps",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("plan_id", uuid, nullable=False),
        sa.Column("concept_id", uuid, nullable=False),
        sa.Column("objective_id", uuid, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("evidence", sa.String(length=16), nullable=False),
        sa.Column("completion_criteria", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("position >= 0", name="ck_learning_plan_steps_position"),
        sa.CheckConstraint(
            "status IN ('satisfied', 'current', 'upcoming')",
            name="ck_learning_plan_steps_status",
        ),
        sa.CheckConstraint("evidence IN ('observed', 'none')", name="ck_learning_plan_steps_evidence"),
        sa.CheckConstraint(
            "length(btrim(completion_criteria)) > 0",
            name="ck_learning_plan_steps_criteria_not_blank",
        ),
        sa.CheckConstraint(
            "(status = 'satisfied' AND evidence = 'observed') OR (status <> 'satisfied' AND evidence = 'none')",
            name="ck_learning_plan_steps_skip_needs_evidence",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["learning_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concept_id"], ["topic_concepts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["objective_id"], ["learning_objectives.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("plan_id", "position", name="uq_learning_plan_steps_position"),
        sa.UniqueConstraint("plan_id", "objective_id", name="uq_learning_plan_steps_objective"),
    )
    op.create_index("ix_learning_plan_steps_plan_id", "learning_plan_steps", ["plan_id"])
    op.create_index("ix_learning_plan_steps_objective_id", "learning_plan_steps", ["objective_id"])
    op.create_foreign_key(
        "fk_learning_plans_current_step_id",
        "learning_plans",
        "learning_plan_steps",
        ["current_step_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_learning_plans_current_step_id", "learning_plans", type_="foreignkey")
    op.drop_index("ix_learning_plan_steps_objective_id", table_name="learning_plan_steps")
    op.drop_index("ix_learning_plan_steps_plan_id", table_name="learning_plan_steps")
    op.drop_table("learning_plan_steps")
    op.drop_index("uq_learning_plans_one_active", table_name="learning_plans")
    op.drop_index("ix_learning_plans_topic_id", table_name="learning_plans")
    op.drop_index("ix_learning_plans_learner_id", table_name="learning_plans")
    op.drop_index("ix_learning_plans_session_id", table_name="learning_plans")
    op.drop_table("learning_plans")
    op.drop_index("ix_topic_concepts_topic_id", table_name="topic_concepts")
    op.drop_table("topic_concepts")
    op.drop_index("uq_diagnostic_attempts_one_open", table_name="diagnostic_attempts")
    op.create_unique_constraint("uq_diagnostic_attempts_session_id", "diagnostic_attempts", ["session_id"])
    op.drop_constraint("ck_learning_sessions_status", "learning_sessions", type_="check")
    op.create_check_constraint(
        "ck_learning_sessions_status",
        "learning_sessions",
        "status IN ('TOPIC_SELECTED', 'DIAGNOSING')",
    )
