"""add todos updated_at trigger

Revision ID: 20260320_todos_updated_at_trg
Revises: 20241205_create_todos
Create Date: 2026-03-20 14:12:00
"""

from __future__ import annotations

from alembic import op

revision = "20260320_todos_updated_at_trg"
down_revision = "20241205_create_todos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_todos_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_todos_set_updated_at
        BEFORE UPDATE ON todos
        FOR EACH ROW
        EXECUTE FUNCTION set_todos_updated_at();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP TRIGGER IF EXISTS trg_todos_set_updated_at ON todos;")
    op.execute("DROP FUNCTION IF EXISTS set_todos_updated_at();")
