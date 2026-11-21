"""Structured lessons that execute a saved pedagogy selection."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_teaching"
down_revision: Union[str, None] = "0007_pedagogy_selections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.drop_constraint("ck_learning_sessions_status", "learning_sessions", type_="check")
    op.create_check_constraint(
        "ck_learning_sessions_status",
        "learning_sessions",
        "status IN ('TOPIC_SELECTED', 'DIAGNOSING', 'PLAN_READY', 'TEACHING')",
    )
    op.create_table(
        "teaching_lessons",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("session_id", uuid, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("selection_id", uuid, nullable=False),
        sa.Column("objective_code", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'active'")),
        sa.Column(
            "review_status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'pending_human_review'"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('active', 'completed')", name="ck_teaching_lessons_status"),
        sa.CheckConstraint("review_status = 'pending_human_review'", name="ck_teaching_lessons_review_pending"),
        sa.CheckConstraint("length(btrim(objective_code)) > 0", name="ck_teaching_lessons_objective_not_blank"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selection_id"], ["pedagogy_selections.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", name="uq_teaching_lessons_session"),
    )
    op.create_index("ix_teaching_lessons_learner_id", "teaching_lessons", ["learner_id"])
    op.create_table(
        "teaching_activities",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("lesson_id", uuid, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("example", sa.Text(), nullable=True),
        sa.Column("worked_steps", postgresql.JSONB(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=True),
        sa.Column("support_level", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("hints_revealed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("inserted_for_struggle", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("position >= 0", name="ck_teaching_activities_position"),
        sa.CheckConstraint("hints_revealed >= 0", name="ck_teaching_activities_hints_revealed"),
        sa.CheckConstraint(
            "kind IN ('explanation', 'concrete_example', 'worked_example', 'guided_practice', "
            "'independent_practice', 'check_for_understanding', 'self_explanation')",
            name="ck_teaching_activities_kind",
        ),
        sa.CheckConstraint("support_level IN ('high', 'medium', 'low')", name="ck_teaching_activities_support"),
        sa.CheckConstraint(
            "status IN ('upcoming', 'current', 'completed')",
            name="ck_teaching_activities_status",
        ),
        sa.CheckConstraint("length(btrim(strategy_id)) > 0", name="ck_teaching_activities_strategy_not_blank"),
        sa.CheckConstraint("length(btrim(title)) > 0", name="ck_teaching_activities_title_not_blank"),
        sa.CheckConstraint("length(btrim(prompt)) > 0", name="ck_teaching_activities_prompt_not_blank"),
        sa.ForeignKeyConstraint(["lesson_id"], ["teaching_lessons.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("lesson_id", "position", name="uq_teaching_activities_position"),
    )
    op.create_index("ix_teaching_activities_lesson_id", "teaching_activities", ["lesson_id"])
    op.create_index(
        "uq_teaching_activities_one_current",
        "teaching_activities",
        ["lesson_id"],
        unique=True,
        postgresql_where=sa.text("status = 'current'"),
    )
    op.create_table(
        "teaching_hints",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("activity_id", uuid, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("reveals_answer", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("position >= 0", name="ck_teaching_hints_position"),
        sa.CheckConstraint("length(btrim(text)) > 0", name="ck_teaching_hints_text_not_blank"),
        sa.CheckConstraint("position > 0 OR reveals_answer = false", name="ck_teaching_hints_first_hides_answer"),
        sa.ForeignKeyConstraint(["activity_id"], ["teaching_activities.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("activity_id", "position", name="uq_teaching_hints_position"),
    )
    op.create_index("ix_teaching_hints_activity_id", "teaching_hints", ["activity_id"])
    op.create_table(
        "teaching_attempts",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("activity_id", uuid, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "outcome IN ('correct', 'incorrect', 'struggled')",
            name="ck_teaching_attempts_outcome",
        ),
        sa.CheckConstraint("length(btrim(answer_text)) > 0", name="ck_teaching_attempts_answer_not_blank"),
        sa.ForeignKeyConstraint(["activity_id"], ["teaching_activities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_teaching_attempts_activity_id", "teaching_attempts", ["activity_id"])


def downgrade() -> None:
    op.drop_index("ix_teaching_attempts_activity_id", table_name="teaching_attempts")
    op.drop_table("teaching_attempts")
    op.drop_index("ix_teaching_hints_activity_id", table_name="teaching_hints")
    op.drop_table("teaching_hints")
    op.drop_index("uq_teaching_activities_one_current", table_name="teaching_activities")
    op.drop_index("ix_teaching_activities_lesson_id", table_name="teaching_activities")
    op.drop_table("teaching_activities")
    op.drop_index("ix_teaching_lessons_learner_id", table_name="teaching_lessons")
    op.drop_table("teaching_lessons")
    op.execute("UPDATE learning_sessions SET status = 'PLAN_READY' WHERE status = 'TEACHING'")
    op.drop_constraint("ck_learning_sessions_status", "learning_sessions", type_="check")
    op.create_check_constraint(
        "ck_learning_sessions_status",
        "learning_sessions",
        "status IN ('TOPIC_SELECTED', 'DIAGNOSING', 'PLAN_READY')",
    )
