"""Update embedding dimension 1536 -> 768 for Gemini

Revision ID: 002
Revises: 001
Create Date: 2026-02-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing embedding column
    op.drop_column('articles', 'embedding')

    # Add new embedding column with 768 dimensions (Gemini text-embedding-004)
    op.execute('ALTER TABLE articles ADD COLUMN embedding vector(768)')


def downgrade() -> None:
    # Revert to OpenAI 1536 dimensions
    op.drop_column('articles', 'embedding')
    op.execute('ALTER TABLE articles ADD COLUMN embedding vector(1536)')
