"""
Generate embeddings for all articles in database.
Run this script to backfill embeddings for existing articles.
"""
import asyncio
import sys
import logging
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.article import Article
from app.services.embedding_service import (
    embedding_service,
    prepare_article_text,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def generate_embeddings_for_all_articles():
    """Generate embeddings for all articles that don't have them."""

    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with async_session() as session:
            # Count total articles without embeddings (memory-efficient)
            count_result = await session.execute(
                select(func.count()).select_from(Article).where(Article.embedding.is_(None))
            )
            total_articles = count_result.scalar_one()

            if total_articles == 0:
                logger.info("✅ All articles already have embeddings")
                return

            logger.info(f"📊 Found {total_articles} articles without embeddings")
            logger.info(f"⏱️  Estimated time: ~{total_articles / 50:.1f} seconds (50 articles/sec)")

            # Process in pages to avoid loading all articles into memory (OOM prevention)
            page_size = 1000  # Fetch 1000 articles at a time
            batch_size = 50   # Process 50 articles per embedding batch
            total_processed = 0
            total_failed = 0

            # Always fetch from offset=0 because WHERE clause excludes processed articles
            # After each commit, articles with embeddings are filtered out automatically
            while True:
                # Fetch first page_size articles without embeddings (always offset=0)
                result = await session.execute(
                    select(Article)
                    .where(Article.embedding.is_(None))
                    .limit(page_size)
                )
                page_articles = result.scalars().all()

                if not page_articles:
                    # No more articles to process
                    break

                # Process page in smaller batches
                for i in range(0, len(page_articles), batch_size):
                    batch = page_articles[i:i + batch_size]

                    try:
                        # Prepare article texts
                        texts = [prepare_article_text(article.to_dict()) for article in batch]

                        # Generate embeddings in batch
                        embeddings = await embedding_service.get_embeddings_batch(texts)

                        # Update articles
                        for article, embedding in zip(batch, embeddings):
                            article.embedding = embedding

                        # Commit batch
                        await session.commit()

                        total_processed += len(batch)
                        progress = (total_processed / total_articles) * 100
                        logger.info(
                            f"✓ Processed batch: "
                            f"{total_processed}/{total_articles} ({progress:.1f}%)"
                        )

                    except Exception as e:
                        await session.rollback()
                        total_failed += len(batch)
                        logger.error(f"❌ Batch failed: {type(e).__name__}: {str(e)}")

            logger.info(f"\n{'='*60}")
            logger.info(f"✅ Embedding generation complete!")
            logger.info(f"   Successfully processed: {total_processed}")
            logger.info(f"   Failed: {total_failed}")
            logger.info(f"   Total: {total_articles}")
            logger.info(f"{'='*60}\n")

    finally:
        await engine.dispose()


async def main():
    """Main entry point."""
    logger.info("🚀 Starting embedding generation...")
    logger.info(f"📍 Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'local'}")

    # Get embedding model info dynamically
    model_name = EMBEDDING_MODEL.replace("models/", "")  # Strip API prefix for readability
    logger.info(f"🤖 Embedding model: {model_name} ({EMBEDDING_DIMENSION} dimensions)\n")

    try:
        await generate_embeddings_for_all_articles()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {type(e).__name__}: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
