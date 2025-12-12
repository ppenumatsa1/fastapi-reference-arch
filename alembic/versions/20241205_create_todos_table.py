"""create todos table

Revision ID: 20241205_create_todos
Revises:
Create Date: 2025-12-05 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20241205_create_todos"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "todos",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column(
            "is_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_todos_id", "todos", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_todos_id", table_name="todos")
    op.drop_table("todos")
