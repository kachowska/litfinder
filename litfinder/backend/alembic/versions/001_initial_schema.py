"""Initial schema with pgvector

Revision ID: 001
Revises:
Create Date: 2026-02-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('telegram_id', sa.BigInteger(), unique=True, nullable=True),
        sa.Column('email', sa.String(100), unique=True, nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('subscription_tier', sa.String(20), nullable=False, server_default='free'),
        sa.Column('subscription_expires', sa.DateTime(), nullable=True),
        sa.Column('search_limit_daily', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('searches_used_today', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('searches_reset_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    )

    # Create articles table
    op.create_table(
        'articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('external_id', sa.String(100), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('authors', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('journal_name', sa.String(255), nullable=True),
        sa.Column('volume', sa.Integer(), nullable=True),
        sa.Column('issue', sa.Integer(), nullable=True),
        sa.Column('pages', sa.String(50), nullable=True),
        sa.Column('doi', sa.String(100), unique=True, nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('abstract_snippet', sa.Text(), nullable=True),
        sa.Column('pdf_url', sa.Text(), nullable=True),
        sa.Column('concepts', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('keywords', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('language', sa.String(10), nullable=False, server_default='ru'),
        sa.Column('cited_by_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('open_access', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('harvested_from', sa.String(50), nullable=False, server_default='manual'),
    )

    # Indexes for articles
    op.create_index('idx_articles_source_external', 'articles', ['source', 'external_id'], unique=True)
    op.create_index('idx_articles_year', 'articles', ['year'])
    op.create_index('idx_articles_language', 'articles', ['language'])

    # Create bibliography_lists table
    op.create_table(
        'bibliography_lists',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('articles', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create search_history table
    op.create_table(
        'search_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('filters', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('results_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create collections table
    op.create_table(
        'collections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create collection_items table
    op.create_table(
        'collection_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('article_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ondelete='CASCADE'),
    )

    # Unique constraint: one article per collection
    op.create_index('idx_collection_items_unique', 'collection_items', ['collection_id', 'article_id'], unique=True)


def downgrade() -> None:
    op.drop_table('collection_items')
    op.drop_table('collections')
    op.drop_table('search_history')
    op.drop_table('bibliography_lists')
    op.drop_index('idx_articles_language', 'articles')
    op.drop_index('idx_articles_year', 'articles')
    op.drop_index('idx_articles_source_external', 'articles')
    op.drop_table('articles')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS vector')
