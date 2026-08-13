"""add dev_sessions and dev_logs tables

Revision ID: 0003_dev_logs
Revises: 0002_api_keys
Create Date: 2026-08-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_dev_logs"
down_revision: Union[str, None] = "0002_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dev_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(120), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("author", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_dev_sessions_project_id", "dev_sessions", ["project_id"])

    op.create_table(
        "dev_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("dev_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("severity", sa.String(10), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("related_task_ids", sa.JSON(), nullable=True),
        sa.Column("git_ref", sa.String(100), nullable=True),
        sa.Column("author", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dev_logs_project_id", "dev_logs", ["project_id"])
    op.create_index("ix_dev_logs_session_id", "dev_logs", ["session_id"])
    op.create_index("ix_dev_logs_project_type", "dev_logs", ["project_id", "entry_type"])
    op.create_index("ix_dev_logs_project_created", "dev_logs", ["project_id", "created_at"])
    op.create_index("ix_dev_logs_project_status", "dev_logs", ["project_id", "status"])


def downgrade() -> None:
    op.drop_table("dev_logs")
    op.drop_table("dev_sessions")