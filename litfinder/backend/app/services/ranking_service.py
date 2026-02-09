"""
Ranking Service
Combines multiple signals to rank search results.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import math


# --- Configuration ---

# Weights for different ranking signals
WEIGHTS = {
    "semantic_similarity": 0.35,   # Vector similarity (primary)
    "keyword_match": 0.20,         # Text keyword overlap
    "citation_score": 0.15,        # Citation count (normalized)
    "recency_score": 0.10,         # Publication year freshness
    "open_access": 0.05,           # Open access bonus
    "source_quality": 0.10,        # Source reliability (OpenAlex vs CyberLeninka)
    "language_match": 0.05         # Query-result language match
}


# --- Ranking Functions ---

class RankingService:
    """Combine multiple signals to rank search results."""
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or WEIGHTS
    
    def rank_results(
        self,
        results: List[Dict[str, Any]],
        query: str,
        query_embedding: Optional[List[float]] = None,
        preferred_language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Rank search results using multiple signals.
        
        Args:
            results: List of article dicts
            query: Original search query
            query_embedding: Query embedding vector (optional)
            preferred_language: User's preferred language
            
        Returns:
            Ranked results with relevance_score
        """
        if not results:
            return []
        
        # Compute scores for each result
        scored_results = []
        
        # Find max citation count for normalization
        max_citations = max(r.get("cited_by_count", 0) for r in results) or 1
        
        for result in results:
            scores = {}
            
            # 1. Semantic similarity (if embedding provided)
            if query_embedding and result.get("embedding"):
                scores["semantic_similarity"] = self._compute_similarity(
                    query_embedding, result["embedding"]
                )
            else:
                scores["semantic_similarity"] = result.get("relevance_score", 0.5)
            
            # 2. Keyword match
            scores["keyword_match"] = self._compute_keyword_match(
                query, result.get("title", ""), result.get("abstract", "")
            )
            
            # 3. Citation score (logarithmic scale)
            citations = result.get("cited_by_count", 0)
            scores["citation_score"] = self._normalize_citations(citations, max_citations)
            
            # 4. Recency score
            year = result.get("year")
            scores["recency_score"] = self._compute_recency(year)
            
            # 5. Open access bonus
            scores["open_access"] = 1.0 if result.get("open_access") else 0.0
            
            # 6. Source quality
            source = result.get("source", "")
            scores["source_quality"] = self._source_quality_score(source)
            
            # 7. Language match
            lang = result.get("language", "en")
            scores["language_match"] = 1.0 if lang == preferred_language else 0.5
            
            # Compute weighted sum
            final_score = sum(
                scores.get(signal, 0) * weight 
                for signal, weight in self.weights.items()
            )
            
            # Add scores to result
            result["relevance_score"] = round(final_score, 4)
            result["ranking_signals"] = scores
            scored_results.append(result)
        
        # Sort by final score
        scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return scored_results
    
    def _compute_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """Compute cosine similarity between two embeddings."""
        if len(embedding1) != len(embedding2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a * a for a in embedding1) ** 0.5
        norm2 = sum(b * b for b in embedding2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Convert to [0, 1] range
        return (dot_product / (norm1 * norm2) + 1) / 2
    
    def _compute_keyword_match(
        self, 
        query: str, 
        title: str, 
        abstract: str
    ) -> float:
        """Compute keyword overlap score."""
        query_words = set(query.lower().split())
        query_words = {w for w in query_words if len(w) > 2}  # Filter short words
        
        if not query_words:
            return 0.5
        
        text = f"{title} {abstract}".lower()
        
        # Count matches
        matches = sum(1 for word in query_words if word in text)
        
        # Title match bonus
        title_lower = title.lower()
        title_matches = sum(1 for word in query_words if word in title_lower)
        
        base_score = matches / len(query_words)
        title_bonus = (title_matches / len(query_words)) * 0.3
        
        return min(base_score + title_bonus, 1.0)
    
    def _normalize_citations(self, citations: int, max_citations: int) -> float:
        """Normalize citations using logarithmic scale."""
        if citations <= 0:
            return 0.0
        
        # Log scale to prevent very high-cited papers from dominating
        log_citations = math.log1p(citations)
        log_max = math.log1p(max_citations)
        
        return log_citations / log_max if log_max > 0 else 0.0
    
    def _compute_recency(self, year: Optional[int]) -> float:
        """Compute recency score based on publication year."""
        if not year:
            return 0.3  # Unknown year gets neutral score
        
        current_year = datetime.now().year
        age = current_year - year
        
        if age < 0:
            return 1.0  # Future publication (preprints)
        elif age == 0:
            return 1.0
        elif age <= 2:
            return 0.9
        elif age <= 5:
            return 0.7
        elif age <= 10:
            return 0.5
        else:
            # Decay for older papers
            return max(0.1, 0.5 - (age - 10) * 0.02)
    
    def _source_quality_score(self, source: str) -> float:
        """Score source reliability."""
        scores = {
            "openalex": 0.9,      # High quality, peer-reviewed
            "cyberleninka": 0.8,  # Russian academic repository
            "crossref": 0.85,
            "pubmed": 0.95,
            "arxiv": 0.7,         # Preprints, not peer-reviewed
        }
        return scores.get(source.lower(), 0.5)


# --- Semantic Search with pgvector ---

async def vector_search(
    db,
    query_embedding: List[float],
    limit: int = 20,
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Search articles using pgvector similarity.
    
    Args:
        db: Database session
        query_embedding: Query embedding vector
        limit: Maximum number of results
        similarity_threshold: Minimum similarity score
        
    Returns:
        List of articles with similarity scores
    """
    from sqlalchemy import text
    
    # pgvector cosine distance query
    # Note: pgvector uses <=> for cosine distance (1 - similarity)
    query = text("""
        SELECT 
            id, source, external_id, title, authors, year, journal_name,
            doi, abstract, language, cited_by_count, open_access,
            1 - (embedding <=> :query_embedding) as similarity
        FROM articles
        WHERE embedding IS NOT NULL
        AND 1 - (embedding <=> :query_embedding) > :threshold
        ORDER BY embedding <=> :query_embedding
        LIMIT :limit
    """)
    
    result = await db.execute(
        query,
        {
            "query_embedding": str(query_embedding),
            "threshold": similarity_threshold,
            "limit": limit
        }
    )
    
    articles = []
    for row in result.fetchall():
        articles.append({
            "id": str(row.id),
            "source": row.source,
            "external_id": row.external_id,
            "title": row.title,
            "authors": row.authors,
            "year": row.year,
            "journal_name": row.journal_name,
            "doi": row.doi,
            "abstract": row.abstract[:500] if row.abstract else None,
            "language": row.language,
            "cited_by_count": row.cited_by_count,
            "open_access": row.open_access,
            "similarity": float(row.similarity)
        })
    
    return articles


# --- Singleton instance ---
ranking_service = RankingService()
