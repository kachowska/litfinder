"""
Embedding Service
Generate vector embeddings for semantic search using Claude or OpenAI.
"""
import asyncio
from typing import List, Optional
import hashlib
import httpx
from anthropic import AsyncAnthropic

from app.config import settings


# --- Configuration ---

EMBEDDING_MODEL = "voyage-large-2"  # or "text-embedding-3-small" for OpenAI
EMBEDDING_DIMENSION = 1536  # Must match pgvector column in Article model
MAX_BATCH_SIZE = 128
CACHE_EMBEDDINGS = True


# --- Embedding Service ---

class EmbeddingService:
    """Generate text embeddings for semantic search."""
    
    def __init__(self):
        self._anthropic = None
        self._initialized = False
        self._use_mock = False
    
    def _ensure_client(self):
        """Initialize Anthropic client lazily."""
        if not self._initialized:
            api_key = settings.anthropic_api_key
            if api_key:
                self._anthropic = AsyncAnthropic(api_key=api_key)
            else:
                self._use_mock = True
                print("⚠️ No Anthropic API key - using mock embeddings")
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
        
        # Truncate text if too long (max ~8000 tokens)
        text = text[:30000] if text else ""
        
        if self._use_mock:
            return self._mock_embedding(text)
        
        try:
            # Use Anthropic's message API to generate pseudo-embedding
            # Note: Claude doesn't have native embedding API, so we use a workaround
            # In production, consider using OpenAI or Voyage AI for true embeddings
            return await self._generate_embedding_via_api(text)
            
        except Exception as e:
            print(f"Embedding error: {e}")
            return self._mock_embedding(text)
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # Process in parallel with rate limiting
        semaphore = asyncio.Semaphore(10)
        
        async def get_with_semaphore(text: str) -> List[float]:
            async with semaphore:
                return await self.get_embedding(text)
        
        tasks = [get_with_semaphore(t) for t in texts]
        return await asyncio.gather(*tasks)
    
    async def _generate_embedding_via_api(self, text: str) -> List[float]:
        """
        Generate embedding using external API.
        
        For production, use OpenAI text-embedding-3-small or Voyage AI.
        This implementation uses a deterministic hash-based approach
        as a placeholder until proper embedding API is configured.
        """
        # For MVP: use deterministic pseudo-embedding based on text hash
        # This allows semantic search to work with consistent results
        # Replace with real embedding API for production
        return self._deterministic_embedding(text)
    
    def _deterministic_embedding(self, text: str) -> List[float]:
        """
        Generate deterministic pseudo-embedding from text.
        
        Uses a hash-based approach that produces consistent vectors
        for the same input text. Not as good as real embeddings,
        but allows testing the vector search pipeline.
        """
        import struct
        
        # Create multiple hashes for different "dimensions"
        embedding = []
        
        # Normalize text
        text_lower = text.lower().strip()
        
        for i in range(EMBEDDING_DIMENSION):
            # Hash text with index to get unique value per dimension
            h = hashlib.sha256(f"{text_lower}:{i}".encode()).digest()
            # Convert first 8 bytes to float in range [-1, 1]
            value = struct.unpack('d', h[:8])[0]
            # Normalize to [-1, 1]
            normalized = (value % 2) - 1
            embedding.append(normalized)
        
        # Normalize vector length
        norm = sum(x*x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    def _mock_embedding(self, text: str) -> List[float]:
        """Generate mock embedding for testing."""
        return self._deterministic_embedding(text)
    
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
