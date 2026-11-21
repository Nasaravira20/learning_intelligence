"""Gemini usage records and model verification checks."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_ai_usage"
down_revision: Union[str, None] = "0002_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "ai_usage_records",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("task", sa.String(length=64), nullable=False),
        sa.Column("model_id", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("action_id", sa.String(length=64), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(14, 8), nullable=False, server_default=sa.text("0")),
        sa.Column("error_class", sa.String(length=32), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed', 'blocked')",
            name="ck_ai_usage_status",
        ),
        sa.CheckConstraint(
            "category IN ('smoke', 'development', 'teaching', 'evaluation', 'demo')",
            name="ck_ai_usage_category",
        ),
    )
    op.create_index("ix_ai_usage_records_category", "ai_usage_records", ["category"])
    op.create_table(
        "ai_model_checks",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("model_id", sa.String(length=200), nullable=False),
        sa.Column("check_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_class", sa.String(length=32), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('passed', 'failed')", name="ck_ai_model_checks_status"),
    )
    op.create_index("ix_ai_model_checks_model_id", "ai_model_checks", ["model_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_model_checks_model_id", table_name="ai_model_checks")
    op.drop_table("ai_model_checks")
    op.drop_index("ix_ai_usage_records_category", table_name="ai_usage_records")
    op.drop_table("ai_usage_records")
