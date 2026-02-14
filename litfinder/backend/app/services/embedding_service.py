"""
Embedding Service
Generate vector embeddings for semantic search using Google Gemini.
"""
import asyncio
from typing import List, Optional
import hashlib
import google.generativeai as genai

from app.config import settings


# --- Configuration ---

EMBEDDING_MODEL = "models/text-embedding-004"  # Gemini embedding model
EMBEDDING_DIMENSION = 768  # Gemini text-embedding-004 dimension
MAX_BATCH_SIZE = 100  # Gemini batch limit
MAX_TEXT_LENGTH = 8000  # ~8000 tokens max


# --- Embedding Service ---

class EmbeddingService:
    """Generate text embeddings for semantic search using Google Gemini."""

    def __init__(self):
        self._initialized = False
        self._use_mock = False

    def _ensure_client(self):
        """Initialize Gemini client lazily."""
        if not self._initialized:
            api_key = settings.gemini_api_key
            if api_key:
                genai.configure(api_key=api_key)
            else:
                self._use_mock = True
                print("⚠️  No Gemini API key - using mock embeddings")
            self._initialized = True

    async def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding vector for a single text.

        Args:
            text: Text to embed (will be truncated if too long)

        Returns:
            List of float values (dimension = EMBEDDING_DIMENSION)
        """
        self._ensure_client()

        # Truncate text if too long
        text = text[:MAX_TEXT_LENGTH] if text else ""

        if not text.strip():
            # Return zero vector for empty text
            return [0.0] * EMBEDDING_DIMENSION

        if self._use_mock:
            return self._mock_embedding(text)

        try:
            # Use Gemini embeddings API
            # Note: genai is sync, so we run it in executor
            import asyncio
            loop = asyncio.get_event_loop()

            result = await loop.run_in_executor(
                None,
                lambda: genai.embed_content(
                    model=EMBEDDING_MODEL,
                    content=text,
                    task_type="retrieval_document"
                )
            )

            embedding = result['embedding']

            # Verify dimension
            if len(embedding) != EMBEDDING_DIMENSION:
                raise ValueError(
                    f"Expected embedding dimension {EMBEDDING_DIMENSION}, "
                    f"got {len(embedding)}"
                )

            return embedding

        except Exception as e:
            print(f"❌ Embedding error: {e}")
            return self._mock_embedding(text)

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        self._ensure_client()

        if not texts:
            return []

        # Truncate texts
        texts = [t[:MAX_TEXT_LENGTH] if t else "" for t in texts]

        # Replace empty texts with placeholder
        processed_texts = [t if t.strip() else "empty" for t in texts]

        if self._use_mock:
            return [self._mock_embedding(t) for t in processed_texts]

        try:
            # Process in batches
            all_embeddings = []
            import asyncio
            loop = asyncio.get_event_loop()

            for i in range(0, len(processed_texts), MAX_BATCH_SIZE):
                batch = processed_texts[i:i + MAX_BATCH_SIZE]

                # Gemini batch embedding
                result = await loop.run_in_executor(
                    None,
                    lambda b=batch: genai.embed_content(
                        model=EMBEDDING_MODEL,
                        content=b,
                        task_type="retrieval_document"
                    ),
                    batch
                )

                # Extract embeddings
                if isinstance(result['embedding'][0], list):
                    # Batch returned multiple embeddings
                    batch_embeddings = result['embedding']
                else:
                    # Single embedding returned as flat list
                    batch_embeddings = [result['embedding']]

                all_embeddings.extend(batch_embeddings)

            # Replace embeddings for empty texts with zero vectors
            for i, text in enumerate(texts):
                if not text.strip():
                    all_embeddings[i] = [0.0] * EMBEDDING_DIMENSION

            return all_embeddings

        except Exception as e:
            print(f"❌ Batch embedding error: {e}")
            return [self._mock_embedding(t) for t in processed_texts]

    def _mock_embedding(self, text: str) -> List[float]:
        """
        Generate deterministic mock embedding from text.

        Uses hash-based approach for consistent results.
        Not as good as real embeddings, but allows testing.
        """
        import struct

        embedding = []
        text_lower = text.lower().strip()

        for i in range(EMBEDDING_DIMENSION):
            # Hash text with index to get unique value per dimension
            h = hashlib.sha256(f"{text_lower}:{i}".encode()).digest()
            # Convert first 8 bytes to float
            value = struct.unpack('d', h[:8])[0]
            # Normalize to [-1, 1]
            normalized = (value % 2) - 1
            embedding.append(normalized)

        # Normalize vector length to unit sphere
        norm = sum(x*x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    async def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Returns:
            Similarity score between -1 and 1
        """
        if len(embedding1) != len(embedding2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a * a for a in embedding1) ** 0.5
        norm2 = sum(b * b for b in embedding2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


# --- Text Preparation ---

def prepare_article_text(article: dict) -> str:
    """
    Prepare article text for embedding.
    Combines title, abstract, and concepts for richer embedding.
    """
    parts = []

    # Title (most important)
    if article.get("title"):
        parts.append(article["title"])

    # Abstract
    if article.get("abstract"):
        parts.append(article["abstract"][:2000])  # Limit abstract length

    # Concepts/keywords
    concepts = article.get("concepts", [])
    if concepts:
        concept_names = [c.get("name", "") for c in concepts[:10]]
        parts.append("Keywords: " + ", ".join(concept_names))

    # Authors (less weight but useful for author search)
    authors = article.get("authors", [])
    if authors:
        author_names = [a.get("name", "") for a in authors[:5] if a.get("name")]
        if author_names:
            parts.append("Authors: " + ", ".join(author_names))

    return " ".join(parts)


def prepare_query_text(query: str, enhanced_keywords: List[str] = None) -> str:
    """
    Prepare search query text for embedding.
    Optionally include enhanced keywords from Claude.
    """
    parts = [query]

    if enhanced_keywords:
        parts.append("Keywords: " + ", ".join(enhanced_keywords))

    return " ".join(parts)


# --- Singleton instance ---
embedding_service = EmbeddingService()


# --- Text Preparation ---

def prepare_article_text(article: dict) -> str:
    """
    Prepare article text for embedding.
    Combines title, abstract, and concepts for richer embedding.
    """
    parts = []
    
    # Title (most important)
    if article.get("title"):
        parts.append(article["title"])
    
    # Abstract
    if article.get("abstract"):
        parts.append(article["abstract"][:2000])  # Limit abstract length
    
    # Concepts/keywords
    concepts = article.get("concepts", [])
    if concepts:
        concept_names = [c.get("name", "") for c in concepts[:10]]
        parts.append("Keywords: " + ", ".join(concept_names))
    
    # Authors (less weight but useful for author search)
    authors = article.get("authors", [])
    if authors:
        author_names = [a.get("name", "") for a in authors[:5] if a.get("name")]
        if author_names:
            parts.append("Authors: " + ", ".join(author_names))
    
    return " ".join(parts)


def prepare_query_text(query: str, enhanced_keywords: List[str] = None) -> str:
    """
    Prepare search query text for embedding.
    Optionally include enhanced keywords from Claude.
    """
    parts = [query]
    
    if enhanced_keywords:
        parts.append("Keywords: " + ", ".join(enhanced_keywords))
    
    return " ".join(parts)


# --- Singleton instance ---
embedding_service = EmbeddingService()
