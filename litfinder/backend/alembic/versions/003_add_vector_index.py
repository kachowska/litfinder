"""Add HNSW index for vector similarity search

Revision ID: 003
Revises: 002
Create Date: 2026-02-13

PRODUCTION NOTES:
- Uses CREATE INDEX CONCURRENTLY for zero-downtime deployment
- Runs in autocommit mode (required for CONCURRENTLY)
- Does not block writes during index creation
- Build time: ~1-5 min per 100K articles (monitor with pg_stat_progress_create_index)
- Trade-off: Slower build time vs. no write locks

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create HNSW index for cosine similarity search using CONCURRENTLY
    # to avoid blocking writes during index creation (zero-downtime deployment)
    #
    # HNSW parameters:
    # - m=16: number of connections per layer (higher = better recall, more memory)
    # - ef_construction=64: size of dynamic candidate list (higher = better quality, slower build)
    #
    # CONCURRENTLY requires:
    # 1. Autocommit mode (cannot run in transaction)
    # 2. Manual idempotency check (IF NOT EXISTS not supported with CONCURRENTLY)

    # Get connection
    conn = op.get_bind()

    # Check if index exists and whether it's valid
    # pg_index.indisvalid = false indicates a failed CONCURRENTLY build
    result = conn.execute(sa.text("""
        SELECT pg_index.indisvalid
        FROM pg_class
        JOIN pg_index ON pg_class.oid = pg_index.indexrelid
        WHERE pg_class.relname = 'idx_articles_embedding_hnsw'
    """))

    row = result.fetchone()

    if row is None:
        # Index doesn't exist, create it
        should_create = True
    elif row[0] is False:
        # Index exists but is invalid (failed CONCURRENTLY build)
        # Must drop it before recreating
        print("⚠️  Found invalid index from previous failed build, dropping...")

        autocommit_conn = conn.execution_options(isolation_level="AUTOCOMMIT")

        # Try CONCURRENTLY first, fall back to regular DROP if it fails
        try:
            autocommit_conn.execute(sa.text("""
                DROP INDEX CONCURRENTLY idx_articles_embedding_hnsw
            """))
        except Exception as e:
            print(f"   CONCURRENTLY drop failed ({e}), using regular DROP...")
            autocommit_conn.execute(sa.text("""
                DROP INDEX idx_articles_embedding_hnsw
            """))

        should_create = True
    else:
        # Index exists and is valid, skip creation
        print("✓ Valid index already exists, skipping creation")
        should_create = False

    if should_create:
        # Create index concurrently
        autocommit_conn = conn.execution_options(isolation_level="AUTOCOMMIT")

        autocommit_conn.execute(sa.text("""
            CREATE INDEX CONCURRENTLY idx_articles_embedding_hnsw
            ON articles
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """))

        print("✓ Index created successfully")
        # Note: CONCURRENTLY allows writes during index creation
        # Monitor progress: SELECT * FROM pg_stat_progress_create_index;
        # Build time: ~1-5 minutes per 100K articles (hardware dependent)


def downgrade() -> None:
    # Drop index concurrently to avoid blocking queries during rollback
    conn = op.get_bind()

    # Check if index exists (valid or invalid)
    result = conn.execute(sa.text("""
        SELECT pg_index.indisvalid
        FROM pg_class
        JOIN pg_index ON pg_class.oid = pg_index.indexrelid
        WHERE pg_class.relname = 'idx_articles_embedding_hnsw'
    """))

    row = result.fetchone()

    if row is not None:
        # Index exists (either valid or invalid), drop it
        autocommit_conn = conn.execution_options(isolation_level="AUTOCOMMIT")

        # Try CONCURRENTLY first, fall back to regular DROP if it fails
        try:
            autocommit_conn.execute(sa.text("""
                DROP INDEX CONCURRENTLY idx_articles_embedding_hnsw
            """))
            print("✓ Index dropped successfully (CONCURRENTLY)")
        except Exception as e:
            print(f"   CONCURRENTLY drop failed ({e}), using regular DROP...")
            autocommit_conn.execute(sa.text("""
                DROP INDEX idx_articles_embedding_hnsw
            """))
            print("✓ Index dropped successfully")
    else:
        # Index doesn't exist, nothing to drop
        print("✓ Index doesn't exist, nothing to drop")
