"""Add updated_at trigger for collections

Revision ID: 25a22eabcf5f
Revises: 004
Create Date: 2026-02-14 07:57:40.476499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25a22eabcf5f'
down_revision: Union[str, Sequence[str], None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add PostgreSQL trigger to auto-update updated_at column.

    Creates a reusable trigger function and attaches it to the collections table.
    This ensures updated_at is automatically refreshed on every UPDATE.
    """
    # Create reusable trigger function for updating updated_at column
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Attach trigger to collections table
    op.execute("""
        CREATE TRIGGER update_collections_updated_at
        BEFORE UPDATE ON collections
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Remove the updated_at trigger and function."""
    # Drop trigger first (depends on function)
    op.execute("DROP TRIGGER IF EXISTS update_collections_updated_at ON collections")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
