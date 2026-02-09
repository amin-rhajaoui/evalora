"""create exam_sessions table

Revision ID: 004
Revises: 003
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exam_sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("student_name", sa.String(100), nullable=False),
        sa.Column("level", sa.String(10), nullable=False, server_default="B1"),
        sa.Column("avatar_id", sa.String(32), nullable=True),
        sa.Column("document_id", sa.String(64), nullable=True),
        sa.Column("current_phase", sa.String(32), nullable=False, server_default="consignes"),
        sa.Column("monologue_duration", sa.Integer, nullable=True),
        sa.Column("debat_duration", sa.Integer, nullable=True),
        sa.Column("livekit_room_name", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("exam_sessions")
