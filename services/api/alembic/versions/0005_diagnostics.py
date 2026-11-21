"""Learning objectives and diagnostic attempts."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_diagnostics"
down_revision: Union[str, None] = "0004_learner_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.drop_constraint("ck_learning_sessions_status", "learning_sessions", type_="check")
    op.create_check_constraint(
        "ck_learning_sessions_status",
        "learning_sessions",
        "status IN ('TOPIC_SELECTED', 'DIAGNOSING')",
    )
    op.create_table(
        "learning_objectives",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("topic_id", uuid, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("statement", sa.String(length=300), nullable=False),
        sa.Column("concept", sa.String(length=120), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(btrim(code)) > 0", name="ck_learning_objectives_code_not_blank"),
        sa.CheckConstraint("length(btrim(statement)) > 0", name="ck_learning_objectives_statement_not_blank"),
        sa.CheckConstraint("length(btrim(concept)) > 0", name="ck_learning_objectives_concept_not_blank"),
        sa.CheckConstraint("position >= 0", name="ck_learning_objectives_position"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("topic_id", "code", name="uq_learning_objectives_topic_code"),
    )
    op.create_index("ix_learning_objectives_topic_id", "learning_objectives", ["topic_id"])
    op.create_table(
        "objective_prerequisites",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("objective_id", uuid, nullable=False),
        sa.Column("prerequisite_id", uuid, nullable=False),
        sa.CheckConstraint("objective_id <> prerequisite_id", name="ck_objective_prerequisites_not_self"),
        sa.ForeignKeyConstraint(["objective_id"], ["learning_objectives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prerequisite_id"], ["learning_objectives.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("objective_id", "prerequisite_id", name="uq_objective_prerequisites_pair"),
    )
    op.create_index("ix_objective_prerequisites_objective_id", "objective_prerequisites", ["objective_id"])
    op.create_index("ix_objective_prerequisites_prerequisite_id", "objective_prerequisites", ["prerequisite_id"])
    op.create_table(
        "diagnostic_attempts",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("session_id", uuid, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("topic_id", uuid, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'in_progress'")),
        sa.Column("starting_point", sa.String(length=16), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("first_unmet_objective_id", uuid, nullable=True),
        sa.Column("hypothesis_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('in_progress', 'completed')", name="ck_diagnostic_attempts_status"),
        sa.CheckConstraint(
            "starting_point IS NULL OR starting_point IN ('beginner', 'partial', 'uncertain')",
            name="ck_diagnostic_attempts_starting_point",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_diagnostic_attempts_confidence",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["first_unmet_objective_id"], ["learning_objectives.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("session_id", name="uq_diagnostic_attempts_session_id"),
    )
    op.create_index("ix_diagnostic_attempts_learner_id", "diagnostic_attempts", ["learner_id"])
    op.create_index("ix_diagnostic_attempts_topic_id", "diagnostic_attempts", ["topic_id"])
    op.create_table(
        "diagnostic_questions",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("attempt_id", uuid, nullable=False),
        sa.Column("objective_id", uuid, nullable=False),
        sa.Column("format", sa.String(length=32), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("choices", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "format IN ('short_answer', 'multiple_choice', 'reasoning')",
            name="ck_diagnostic_questions_format",
        ),
        sa.CheckConstraint("length(btrim(prompt)) > 0", name="ck_diagnostic_questions_prompt_not_blank"),
        sa.CheckConstraint("position >= 0", name="ck_diagnostic_questions_position"),
        sa.ForeignKeyConstraint(["attempt_id"], ["diagnostic_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["objective_id"], ["learning_objectives.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_diagnostic_questions_attempt_id", "diagnostic_questions", ["attempt_id"])
    op.create_index("ix_diagnostic_questions_objective_id", "diagnostic_questions", ["objective_id"])
    op.create_table(
        "diagnostic_responses",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("question_id", uuid, nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("reasoning_text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("answer_verdict", sa.String(length=16), nullable=False),
        sa.Column("reasoning_verdict", sa.String(length=16), nullable=False),
        sa.Column("understanding", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "answer_verdict IN ('correct', 'partial', 'incorrect', 'unanswered')",
            name="ck_diagnostic_responses_answer",
        ),
        sa.CheckConstraint(
            "reasoning_verdict IN ('sound', 'partial', 'weak', 'absent', 'uncertain')",
            name="ck_diagnostic_responses_reasoning",
        ),
        sa.CheckConstraint(
            "understanding IN ('none', 'partial', 'solid', 'uncertain')",
            name="ck_diagnostic_responses_understanding",
        ),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_diagnostic_responses_confidence"),
        sa.ForeignKeyConstraint(["question_id"], ["diagnostic_questions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("question_id", name="uq_diagnostic_responses_question_id"),
    )


def downgrade() -> None:
    op.drop_table("diagnostic_responses")
    op.drop_index("ix_diagnostic_questions_objective_id", table_name="diagnostic_questions")
    op.drop_index("ix_diagnostic_questions_attempt_id", table_name="diagnostic_questions")
    op.drop_table("diagnostic_questions")
    op.drop_index("ix_diagnostic_attempts_topic_id", table_name="diagnostic_attempts")
    op.drop_index("ix_diagnostic_attempts_learner_id", table_name="diagnostic_attempts")
    op.drop_table("diagnostic_attempts")
    op.drop_index("ix_objective_prerequisites_prerequisite_id", table_name="objective_prerequisites")
    op.drop_index("ix_objective_prerequisites_objective_id", table_name="objective_prerequisites")
    op.drop_table("objective_prerequisites")
    op.drop_index("ix_learning_objectives_topic_id", table_name="learning_objectives")
    op.drop_table("learning_objectives")
    op.drop_constraint("ck_learning_sessions_status", "learning_sessions", type_="check")
    op.create_check_constraint(
        "ck_learning_sessions_status",
        "learning_sessions",
        "status = 'TOPIC_SELECTED'",
    )
