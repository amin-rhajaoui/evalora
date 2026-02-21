"""add tavus_conversation_id to exam_sessions

Revision ID: 006
Revises: 005
Create Date: 2026-02-21
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exam_sessions",
        sa.Column("tavus_conversation_id", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("exam_sessions", "tavus_conversation_id")
