"""Add collections and collection_items tables

Revision ID: 004
Revises: 003
Create Date: 2026-02-13

"""
from typing import Sequence, Union
import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SAFETY GUARD: Prevent accidental execution in production
    db_url = os.getenv('DATABASE_URL', '')
    environment = os.getenv('ENVIRONMENT', 'development')

    # Abort if running in production environment
    if environment.lower() == 'production' or 'prod' in db_url.lower():
        raise RuntimeError(
            "Migration 004 cannot run in production environment. "
            "This migration changes the collections schema from article_id (UUID FK) to work_id (string). "
            "Manual data migration is required. Contact DevOps."
        )

    # Check if old tables exist
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()

    # Rename old tables to preserve data instead of dropping
    if 'collection_items' in existing_tables:
        op.rename_table('collection_items', 'collection_items_old')
        print("INFO: Renamed 'collection_items' to 'collection_items_old' (data preserved)")

    if 'collections' in existing_tables:
        op.rename_table('collections', 'collections_old')
        print("INFO: Renamed 'collections' to 'collections_old' (data preserved)")

    # NOTE: Manual data migration required if old tables had data
    # Old schema: collections.name, collection_items.article_id (UUID FK to articles)
    # New schema: collections.title, collection_items.work_id (string, OpenAlex ID)
    #
    # To migrate data:
    # 1. Copy collections: INSERT INTO collections (id, user_id, title, description, tags, created_at, updated_at)
    #                      SELECT id, user_id, name, description, '{}', created_at, updated_at FROM collections_old
    # 2. Copy items: Requires mapping article_id → work_id via articles.openalex_id
    #                INSERT INTO collection_items (id, collection_id, work_id, notes, added_at)
    #                SELECT ci.id, ci.collection_id, a.openalex_id, ci.notes, ci.added_at
    #                FROM collection_items_old ci JOIN articles a ON ci.article_id = a.id
    # 3. Drop old tables: DROP TABLE collection_items_old; DROP TABLE collections_old;

    # Create collections table with new schema
    op.create_table(
        'collections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'))
    )

    # Create index on user_id for faster collection lookups
    op.create_index('idx_collections_user_id', 'collections', ['user_id'])

    # Create collection_items table with new schema (work_id instead of article_id)
    op.create_table(
        'collection_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('work_id', sa.String(255), nullable=False),  # OpenAlex work ID (e.g., "W2741809807")
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('notes', sa.Text(), nullable=True)
    )

    # Create compound index for collection_id + work_id (ensures uniqueness and fast lookups)
    op.create_index('idx_collection_items_collection_work', 'collection_items', ['collection_id', 'work_id'], unique=True)

    # Create index on work_id for reverse lookups (which collections contain this work)
    op.create_index('idx_collection_items_work_id', 'collection_items', ['work_id'])


def downgrade() -> None:
    # SAFETY GUARD: Prevent accidental execution in production
    environment = os.getenv('ENVIRONMENT', 'development')
    db_url = os.getenv('DATABASE_URL', '')

    if environment.lower() == 'production' or 'prod' in db_url.lower():
        raise RuntimeError(
            "Migration 004 downgrade cannot run in production. "
            "Manual intervention required. Contact DevOps."
        )

    # Drop new schema tables
    op.drop_index('idx_collection_items_work_id', table_name='collection_items')
    op.drop_index('idx_collection_items_collection_work', table_name='collection_items')
    op.drop_index('idx_collections_user_id', table_name='collections')
    op.drop_table('collection_items')
    op.drop_table('collections')

    # Restore old tables if they exist
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = inspector.get_table_names()

    if 'collections_old' in existing_tables:
        op.rename_table('collections_old', 'collections')
        print("INFO: Restored 'collections' from 'collections_old'")

    if 'collection_items_old' in existing_tables:
        op.rename_table('collection_items_old', 'collection_items')
        print("INFO: Restored 'collection_items' from 'collection_items_old'")
