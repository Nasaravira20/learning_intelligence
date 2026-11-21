"""Initial learner, topic, and session tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "learner_profiles",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "length(btrim(display_name)) > 0",
            name="ck_learner_display_name_not_blank",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_learner_profiles_user_id"),
    )
    op.create_table(
        "learning_topics",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(btrim(title)) > 0", name="ck_learning_topics_title_not_blank"),
        sa.CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
            name="ck_learning_topics_slug_format",
        ),
        sa.UniqueConstraint("slug", name="uq_learning_topics_slug"),
    )
    op.create_table(
        "learning_sessions",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("learner_id", uuid, nullable=False),
        sa.Column("topic_id", uuid, nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'TOPIC_SELECTED'"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status = 'TOPIC_SELECTED'", name="ck_learning_sessions_status"),
        sa.ForeignKeyConstraint(["learner_id"], ["learner_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["learning_topics.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_learning_sessions_learner_id", "learning_sessions", ["learner_id"])
    op.create_index("ix_learning_sessions_topic_id", "learning_sessions", ["topic_id"])


def downgrade() -> None:
    op.drop_index("ix_learning_sessions_topic_id", table_name="learning_sessions")
    op.drop_index("ix_learning_sessions_learner_id", table_name="learning_sessions")
    op.drop_table("learning_sessions")
    op.drop_table("learning_topics")
    op.drop_table("learner_profiles")
    op.drop_table("users")
