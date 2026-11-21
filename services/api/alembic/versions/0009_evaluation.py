"""Evaluation attempts, mastery records, and a second lesson after remediation."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_evaluation"
down_revision: Union[str, None] = "0008_teaching"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = sa.dialects.postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.drop_constraint("ck_learning_sessions_status", "learning_sessions", type_="check")
    op.create_check_constraint(
        "ck_learning_sessions_status",
        "learning_sessions",
        "status IN ('TOPIC_SELECTED', 'DIAGNOSING', 'PLAN_READY', 'TEACHING', "
        "'EVALUATING', 'REMEDIATION', 'MASTERED', 'NEEDS_REVIEW')",
    )
    op.add_column(
        "teaching_lessons",
        sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.drop_constraint("uq_teaching_lessons_session", "teaching_lessons", type_="unique")
    op.create_unique_constraint("uq_teaching_lessons_session_revision", "teaching_lessons", ["session_id", "revision"])
    op.drop_constraint("ck_teaching_lessons_status", "teaching_lessons", type_="check")
    op.create_check_constraint(
        "ck_teaching_lessons_status",
        "teaching_lessons",
        "status IN ('active', 'completed', 'superseded')",
    )
    op.create_index(
        "uq_teaching_lessons_one_active",
        "teaching_lessons",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_table(
        "mastery_records",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("session_id", uuid, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("topic_id", uuid, nullable=False),
        sa.Column("objective_code", sa.String(length=80), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("credit", sa.Numeric(4, 3), nullable=False),
        sa.Column("evidence_kind", sa.String(length=16), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("answer_verdict", sa.String(length=16), nullable=False),
        sa.Column("reasoning_verdict", sa.String(length=16), nullable=False),
        sa.Column("understanding", sa.String(length=16), nullable=False),
        sa.Column("remediation_strategy_id", sa.String(length=64), nullable=True),
        sa.Column("misconception_evidence", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "decision IN ('mastered', 'remediation', 'further_assessment', 'needs_review')",
            name="ck_mastery_records_decision",
        ),
        sa.CheckConstraint(
            "(decision = 'mastered' AND evidence_kind = 'observed' AND credit = 1) "
            "OR (decision <> 'mastered' AND evidence_kind = 'inferred')",
            name="ck_mastery_records_evidence",
        ),
        sa.CheckConstraint("credit >= 0 AND credit <= 1", name="ck_mastery_records_credit"),
        sa.CheckConstraint("length(btrim(feedback)) > 0", name="ck_mastery_records_feedback_not_blank"),
        sa.CheckConstraint("length(btrim(objective_code)) > 0", name="ck_mastery_records_objective_not_blank"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_mastery_records_session_id", "mastery_records", ["session_id"])
    op.create_table(
        "evaluation_attempts",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("session_id", uuid, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("lesson_id", uuid, nullable=False),
        sa.Column("mastery_record_id", uuid, nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'open'")),
        sa.Column("objective_code", sa.String(length=80), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("rubric", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("reasoning_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("revision >= 1", name="ck_evaluation_attempts_revision"),
        sa.CheckConstraint("status IN ('open', 'completed')", name="ck_evaluation_attempts_status"),
        sa.CheckConstraint("length(btrim(prompt)) > 0", name="ck_evaluation_attempts_prompt_not_blank"),
        sa.CheckConstraint("length(btrim(objective_code)) > 0", name="ck_evaluation_attempts_objective_not_blank"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["teaching_lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mastery_record_id"], ["mastery_records.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("session_id", "revision", name="uq_evaluation_attempts_revision"),
    )
    op.create_index("ix_evaluation_attempts_session_id", "evaluation_attempts", ["session_id"])
    op.create_index(
        "uq_evaluation_attempts_one_open",
        "evaluation_attempts",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    op.drop_index("uq_evaluation_attempts_one_open", table_name="evaluation_attempts")
    op.drop_index("ix_evaluation_attempts_session_id", table_name="evaluation_attempts")
    op.drop_table("evaluation_attempts")
    op.drop_index("ix_mastery_records_session_id", table_name="mastery_records")
    op.drop_table("mastery_records")
    op.drop_index("uq_teaching_lessons_one_active", table_name="teaching_lessons")
    op.execute("DELETE FROM teaching_lessons WHERE revision > 1")
    op.drop_constraint("uq_teaching_lessons_session_revision", "teaching_lessons", type_="unique")
    op.execute("UPDATE teaching_lessons SET status = 'completed' WHERE status = 'superseded'")
    op.drop_constraint("ck_teaching_lessons_status", "teaching_lessons", type_="check")
    op.create_check_constraint(
        "ck_teaching_lessons_status",
        "teaching_lessons",
        "status IN ('active', 'completed')",
    )
    op.create_unique_constraint("uq_teaching_lessons_session", "teaching_lessons", ["session_id"])
    op.drop_column("teaching_lessons", "revision")
    op.execute(
        "UPDATE learning_sessions SET status = 'TEACHING' "
        "WHERE status IN ('EVALUATING', 'REMEDIATION', 'MASTERED', 'NEEDS_REVIEW')"
    )
    op.drop_constraint("ck_learning_sessions_status", "learning_sessions", type_="check")
    op.create_check_constraint(
        "ck_learning_sessions_status",
        "learning_sessions",
        "status IN ('TOPIC_SELECTED', 'DIAGNOSING', 'PLAN_READY', 'TEACHING')",
    )
