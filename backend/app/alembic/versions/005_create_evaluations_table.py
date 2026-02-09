"""create evaluation_results table

Revision ID: 005
Revises: 004
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("total_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("monologue_scores_json", JSON, nullable=True),
        sa.Column("debat_scores_json", JSON, nullable=True),
        sa.Column("general_scores_json", JSON, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("strengths_json", JSON, nullable=True),
        sa.Column("improvements_json", JSON, nullable=True),
        sa.Column("advice_json", JSON, nullable=True),
        sa.Column("avatar_id", sa.String(32), nullable=True),
        sa.Column("feedback_tone", sa.String(64), nullable=True, server_default="neutral"),
        sa.Column("monologue_duration", sa.Integer, nullable=True),
        sa.Column("debat_duration", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("evaluation_results")
