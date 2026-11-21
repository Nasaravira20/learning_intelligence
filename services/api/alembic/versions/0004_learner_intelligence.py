"""Learner profile, knowledge, and history."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_learner_intelligence"
down_revision: Union[str, None] = "0003_ai_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = postgresql.UUID(as_uuid=True)

EVIDENCE = (
    "(evidence_kind = 'observed' AND provenance IN ('learner_response', 'assessment')) "
    "OR (evidence_kind = 'inferred' AND provenance IN ('system_estimate', 'learner_report'))"
)


def upgrade() -> None:
    op.add_column("learner_profiles", sa.Column("background_note", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_learner_background_note_not_blank",
        "learner_profiles",
        "background_note IS NULL OR length(btrim(background_note)) > 0",
    )
    op.create_table(
        "learning_goals",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("topic_id", uuid, nullable=True),
        sa.Column("statement", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(btrim(statement)) > 0", name="ck_learning_goals_statement_not_blank"),
        sa.CheckConstraint("status IN ('active', 'completed', 'archived')", name="ck_learning_goals_status"),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_learning_goals_learner_id", "learning_goals", ["learner_id"])
    op.create_index("ix_learning_goals_topic_id", "learning_goals", ["topic_id"])
    op.create_table(
        "learning_preferences",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("pace", sa.String(length=16), nullable=False),
        sa.Column("explanation_detail", sa.String(length=16), nullable=False),
        sa.Column("practice_first", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("pace IN ('unhurried', 'steady', 'intensive')", name="ck_learning_preferences_pace"),
        sa.CheckConstraint(
            "explanation_detail IN ('concise', 'balanced', 'thorough')",
            name="ck_learning_preferences_detail",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR length(btrim(notes)) > 0",
            name="ck_learning_preferences_notes_not_blank",
        ),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("learner_id", name="uq_learning_preferences_learner_id"),
    )
    op.create_table(
        "learner_knowledge",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("topic_id", uuid, nullable=False),
        sa.Column("concept", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_kind", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("provenance", sa.String(length=32), nullable=False),
        sa.Column("correction_note", sa.Text(), nullable=True),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaces_id", uuid, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(btrim(concept)) > 0", name="ck_learner_knowledge_concept_not_blank"),
        sa.CheckConstraint("length(btrim(summary)) > 0", name="ck_learner_knowledge_summary_not_blank"),
        sa.CheckConstraint(EVIDENCE, name="ck_learner_knowledge_evidence"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_learner_knowledge_confidence"),
        sa.CheckConstraint(
            "corrected_at IS NULL OR length(btrim(correction_note)) > 0",
            name="ck_learner_knowledge_correction_note",
        ),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["replaces_id"], ["learner_knowledge.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("replaces_id", name="uq_learner_knowledge_replaces_id"),
    )
    op.create_index("ix_learner_knowledge_learner_id", "learner_knowledge", ["learner_id"])
    op.create_index("ix_learner_knowledge_topic_id", "learner_knowledge", ["topic_id"])
    op.create_table(
        "misconception_records",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("topic_id", uuid, nullable=False),
        sa.Column("concept", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_kind", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("provenance", sa.String(length=32), nullable=False),
        sa.Column("supporting_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'open'")),
        sa.Column("correction_note", sa.Text(), nullable=True),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaces_id", uuid, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(btrim(concept)) > 0", name="ck_misconception_concept_not_blank"),
        sa.CheckConstraint("length(btrim(description)) > 0", name="ck_misconception_description_not_blank"),
        sa.CheckConstraint(EVIDENCE, name="ck_misconception_evidence"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_misconception_confidence"),
        sa.CheckConstraint("status IN ('open', 'resolved', 'rejected')", name="ck_misconception_status"),
        sa.CheckConstraint(
            "corrected_at IS NULL OR length(btrim(correction_note)) > 0",
            name="ck_misconception_correction_note",
        ),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["replaces_id"], ["misconception_records.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("replaces_id", name="uq_misconception_records_replaces_id"),
    )
    op.create_index("ix_misconception_records_learner_id", "misconception_records", ["learner_id"])
    op.create_index("ix_misconception_records_topic_id", "misconception_records", ["topic_id"])
    op.create_table(
        "assessment_records",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("topic_id", uuid, nullable=False),
        sa.Column("session_id", uuid, nullable=True),
        sa.Column("prompt_summary", sa.String(length=500), nullable=False),
        sa.Column("response_summary", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False, server_default=sa.text("'recorded'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(btrim(prompt_summary)) > 0", name="ck_assessment_prompt_not_blank"),
        sa.CheckConstraint("length(btrim(response_summary)) > 0", name="ck_assessment_response_not_blank"),
        sa.CheckConstraint(
            "outcome IN ('recorded', 'correct', 'partial', 'incorrect', 'unanswered')",
            name="ck_assessment_outcome",
        ),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_assessment_records_learner_id", "assessment_records", ["learner_id"])
    op.create_index("ix_assessment_records_topic_id", "assessment_records", ["topic_id"])
    op.create_index("ix_assessment_records_session_id", "assessment_records", ["session_id"])
    op.create_table(
        "learning_activities",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("topic_id", uuid, nullable=True),
        sa.Column("session_id", uuid, nullable=True),
        sa.Column("activity_kind", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(btrim(summary)) > 0", name="ck_learning_activities_summary_not_blank"),
        sa.CheckConstraint(
            "activity_kind IN ('explanation', 'practice', 'review', 'note')",
            name="ck_learning_activities_kind",
        ),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_learning_activities_learner_id", "learning_activities", ["learner_id"])
    op.create_index("ix_learning_activities_topic_id", "learning_activities", ["topic_id"])
    op.create_index("ix_learning_activities_session_id", "learning_activities", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_learning_activities_session_id", table_name="learning_activities")
    op.drop_index("ix_learning_activities_topic_id", table_name="learning_activities")
    op.drop_index("ix_learning_activities_learner_id", table_name="learning_activities")
    op.drop_table("learning_activities")
    op.drop_index("ix_assessment_records_session_id", table_name="assessment_records")
    op.drop_index("ix_assessment_records_topic_id", table_name="assessment_records")
    op.drop_index("ix_assessment_records_learner_id", table_name="assessment_records")
    op.drop_table("assessment_records")
    op.drop_index("ix_misconception_records_topic_id", table_name="misconception_records")
    op.drop_index("ix_misconception_records_learner_id", table_name="misconception_records")
    op.drop_table("misconception_records")
    op.drop_index("ix_learner_knowledge_topic_id", table_name="learner_knowledge")
    op.drop_index("ix_learner_knowledge_learner_id", table_name="learner_knowledge")
    op.drop_table("learner_knowledge")
    op.drop_table("learning_preferences")
    op.drop_index("ix_learning_goals_topic_id", table_name="learning_goals")
    op.drop_index("ix_learning_goals_learner_id", table_name="learning_goals")
    op.drop_table("learning_goals")
    op.drop_constraint("ck_learner_background_note_not_blank", "learner_profiles", type_="check")
    op.drop_column("learner_profiles", "background_note")
