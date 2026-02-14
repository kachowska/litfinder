"""
Research Assistant API Endpoint
RAG-based semantic search with answer synthesis and citations
"""
import logging
import json
import re
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from app.database import get_db
from app.models.user import User
from app.models.article import Article
from app.utils.security import get_current_user
from app.services.llm_service import get_llm_client, LLMTask
from app.services.embedding_service import embedding_service, prepare_query_text
from app.services.cache_service import cache_service, hash_query

# Logger
logger = logging.getLogger(__name__)

router = APIRouter()


# --- Data Classes ---

@dataclass
class ArticleWithScore:
    """
    Article with similarity score from vector search.

    Separates ORM model from search result metadata to avoid dynamic attributes.
    """
    article: Article
    similarity: float


# --- Schemas ---

class ResearchRequest(BaseModel):
    """Research Assistant request."""
    query: str = Field(..., min_length=3, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)
    year_from: Optional[int] = Field(default=None, ge=1900, le=2100)
    year_to: Optional[int] = Field(default=None, ge=1900, le=2100)
    language: Optional[str] = Field(default=None, pattern="^(en|ru)$")

    @model_validator(mode='after')
    def check_year_range(self):
        """Validate that year_from is not greater than year_to."""
        if self.year_from is not None and self.year_to is not None:
            if self.year_from > self.year_to:
                raise ValueError(
                    f"year_from ({self.year_from}) must not be greater than year_to ({self.year_to})"
                )
        return self


class CitationSource(BaseModel):
    """Citation source in answer."""
    article_id: str
    title: str
    authors: List[str]
    year: Optional[int]
    relevance_score: float


class ResearchResponse(BaseModel):
    """Research Assistant response."""
    query: str
    answer: str
    citations: List[CitationSource]
    total_sources: int
    execution_time_ms: int
    from_cache: bool = False


# Cache schema version - increment when ResearchResponse or CitationSource schema changes
# to automatically invalidate old cache entries
RESEARCH_RESPONSE_CACHE_VERSION = "v1"


# --- RAG Pipeline ---

async def vector_similarity_search(
    db: AsyncSession,
    query_embedding: List[float],
    limit: int = 10,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    language: Optional[str] = None
) -> List[ArticleWithScore]:
    """
    Search for similar articles using pgvector cosine similarity.

    Args:
        db: Database session
        query_embedding: Query vector embedding
        limit: Maximum number of results
        year_from: Filter articles from this year
        year_to: Filter articles up to this year
        language: Filter by language (en, ru)

    Returns:
        List of ArticleWithScore containing articles and their similarity scores
    """
    # ⚠️ SQL INJECTION SAFETY:
    # - filter_conditions must ONLY contain hardcoded SQL strings (e.g., "year >= :year_from")
    # - ALL user-controlled values MUST go into params dict with placeholders (e.g., :year_from)
    # - NEVER interpolate user input directly into SQL strings (e.g., f"year >= {year_from}")
    # - Future changes: always use parameter placeholders (:param_name) for any dynamic values

    # Build filter conditions using parameter placeholders
    filter_conditions = []
    params = {
        "query_embedding": str(query_embedding),  # pgvector accepts string format
        "limit": limit
    }

    if year_from is not None:
        filter_conditions.append("year >= :year_from")
        params["year_from"] = year_from

    if year_to is not None:
        filter_conditions.append("year <= :year_to")
        params["year_to"] = year_to

    if language is not None:
        filter_conditions.append("language = :language")
        params["language"] = language

    where_clause = " AND ".join(filter_conditions) if filter_conditions else "1=1"

    # Vector similarity search using cosine distance (<=> operator)
    # Lower distance = higher similarity
    # Only search articles that have embeddings
    query_sql = text(f"""
        SELECT
            id,
            source,
            external_id,
            title,
            authors,
            year,
            journal_name,
            volume,
            issue,
            pages,
            doi,
            abstract,
            pdf_url,
            concepts,
            cited_by_count,
            open_access,
            language,
            1 - (embedding <=> :query_embedding) as similarity
        FROM articles
        WHERE embedding IS NOT NULL
          AND {where_clause}
        ORDER BY embedding <=> :query_embedding
        LIMIT :limit
    """)

    result = await db.execute(query_sql, params)

    results = []
    for row in result:
        article = Article(
            id=row.id,
            source=row.source,
            external_id=row.external_id,
            title=row.title,
            authors=row.authors,
            year=row.year,
            journal_name=row.journal_name,
            volume=row.volume,
            issue=row.issue,
            pages=row.pages,
            doi=row.doi,
            abstract=row.abstract,
            pdf_url=row.pdf_url,
            concepts=row.concepts,
            cited_by_count=row.cited_by_count,
            open_access=row.open_access,
            language=row.language
        )
        # Wrap article with its similarity score (no dynamic attributes)
        results.append(ArticleWithScore(
            article=article,
            similarity=float(row.similarity)
        ))

    return results


def extract_author_name(author) -> str:
    """
    Safely extract author name from various formats.

    Only accepts dict with "name" key or string as valid author representations.
    Returns empty string for any other types (int, list, None, etc.) to prevent
    garbage data in citations.

    Args:
        author: Author data (dict or str expected, other types rejected)

    Returns:
        Author name as string, or empty string for invalid types
    """
    if isinstance(author, dict):
        return author.get("name", "")
    elif isinstance(author, str):
        return author
    else:
        # Return empty string for invalid types (int, list, None, etc.)
        # This prevents garbage like "123" or "['John']" in author lists
        return ""


def get_author_names(authors) -> List[str]:
    """
    Extract list of valid author names from authors data.

    Filters out invalid/empty entries using extract_author_name.

    Args:
        authors: List of author data (dicts, strings, or mixed types)

    Returns:
        List of non-empty author name strings
    """
    if not authors:
        return []
    return [name for author in authors if (name := extract_author_name(author))]


def parse_citations_from_answer(answer: str) -> Set[int]:
    """
    Parse all citation indices from answer text.

    Handles various citation formats:
    - Single: [1]
    - Multiple: [1,2] or [1, 2]
    - Ranges: [1-3] (expands to 1, 2, 3)
    - Combined: [1,3-5,7] (expands to 1, 3, 4, 5, 7)

    Args:
        answer: Generated answer text containing bracketed citations

    Returns:
        Set of cited article indices (1-based)
    """
    cited_indices = set()

    # Find all bracketed citation groups: [1], [1,2], [1-3], etc.
    # Pattern matches: [number, number-number, spaces]
    pattern = r'\[([0-9,\-\s]+)\]'
    matches = re.findall(pattern, answer)

    for match in matches:
        # Split by commas to handle multiple citations: "1,2,3" or "1, 2, 3"
        tokens = match.split(',')

        for token in tokens:
            token = token.strip()
            if not token:
                continue

            # Check if token is a range: "1-3"
            if '-' in token:
                try:
                    start, end = token.split('-', 1)
                    start_idx = int(start.strip())
                    end_idx = int(end.strip())
                    # Expand range: 1-3 → {1, 2, 3}
                    cited_indices.update(range(start_idx, end_idx + 1))
                except (ValueError, AttributeError):
                    # Invalid range format, skip
                    continue
            else:
                # Single citation: "1"
                try:
                    cited_indices.add(int(token))
                except ValueError:
                    # Invalid number, skip
                    continue

    return cited_indices


async def synthesize_research_answer(
    query: str,
    results: List[ArticleWithScore],
    llm_client
) -> tuple[str, List[CitationSource]]:
    """
    Synthesize answer from retrieved articles using Claude.

    Args:
        query: User's research question
        results: Retrieved articles with similarity scores
        llm_client: LLM client

    Returns:
        Tuple of (answer_text, citations_list)
    """
    # Prepare articles context for LLM
    articles_data = []
    for idx, result in enumerate(results, 1):
        article = result.article
        similarity = result.similarity

        # Safely extract author names with defensive handling
        authors_list = get_author_names(article.authors)

        # Format author string (first 3 authors + et al.)
        authors_str = ", ".join(authors_list[:3])
        if len(authors_list) > 3:
            authors_str += " et al."

        article_context = {
            "id": idx,
            "article_id": str(article.id),
            "title": article.title,
            "authors": authors_str,
            "year": article.year,
            "abstract": article.abstract[:1000] if article.abstract else "No abstract available",
            "journal": article.journal_name,
            "cited_by": article.cited_by_count,
            "relevance": f"{similarity:.2f}"
        }
        articles_data.append(article_context)

    # Serialize to JSON for better LLM parsing
    articles_json = json.dumps(articles_data, ensure_ascii=False, indent=2)

    # Create prompt
    system_prompt = """You are a research assistant helping academics find and understand scientific literature.

Your task is to:
1. Analyze the provided research papers
2. Synthesize a comprehensive answer to the user's question
3. Cite specific papers using [N] notation
4. Provide accurate information based only on the given sources

Guidelines:
- Be precise and academic in tone
- Always cite sources using [1], [2], etc. notation
- If sources don't fully answer the question, state limitations clearly
- Prioritize recent papers and highly-cited works
- Include key findings, methodologies, and results
- Keep answer focused and concise (3-5 paragraphs)"""

    user_prompt = f"""Research Question: {query}

Available Sources:
{articles_json}

Instructions:
1. Read and analyze all provided sources
2. Synthesize an answer that directly addresses the research question
3. Use inline citations [1], [2], etc. when referencing specific papers
4. Structure your answer clearly with:
   - Overview of the topic
   - Key findings from the literature
   - Methods/approaches used
   - Current state of research
   - Any limitations or gaps

Provide a well-structured research answer with proper citations."""

    # Generate answer
    answer = await llm_client.generate(
        task=LLMTask.RESEARCH_ANSWER,
        prompt=user_prompt,
        system=system_prompt,
        max_tokens=2000,
        temperature=0.3  # Lower temperature for factual accuracy
    )

    # Parse all citations from answer (handles [1], [1,2], [1-3], etc.)
    cited_indices = parse_citations_from_answer(answer)

    # Extract citations for articles that were actually cited
    citations = []
    for idx, result in enumerate(results, 1):
        # Check if article index appears in any citation (exact, range, or combined)
        if idx in cited_indices:
            article = result.article
            similarity = result.similarity

            # Safely extract author names with defensive handling
            authors_list = get_author_names(article.authors)

            citations.append(CitationSource(
                article_id=str(article.id),
                title=article.title,
                authors=authors_list[:5],  # Limit to 5 authors
                year=article.year,
                relevance_score=similarity
            ))

    return answer, citations


# --- Endpoint ---

@router.post("/answer", response_model=ResearchResponse)
async def research_answer(
    request: ResearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Research Assistant: Answer research questions using RAG.

    Pipeline:
    1. Generate query embedding
    2. Vector similarity search for relevant articles
    3. Synthesize answer with citations using Claude
    4. Return formatted response

    Requires articles to have embeddings in the database.
    """
    start_time = time.time()

    # Check cache
    cache_key = hash_query(request.query, {
        "max_results": request.max_results,
        "year_from": request.year_from,
        "year_to": request.year_to,
        "language": request.language,
        "endpoint": "research_answer",
        "schema_version": RESEARCH_RESPONSE_CACHE_VERSION
    })

    cached = await cache_service.get(cache_key)
    if cached:
        # Return cached response with updated metadata (no post-construction mutation)
        try:
            return ResearchResponse(
                **{
                    **cached,
                    "from_cache": True,
                    "execution_time_ms": int((time.time() - start_time) * 1000)
                }
            )
        except ValidationError as e:
            # Schema mismatch: cached data incompatible with current ResearchResponse
            logger.warning(
                f"Cache schema mismatch for key {cache_key[:20]}...: {e}. "
                "Invalidating stale cache entry and regenerating response."
            )
            # Delete stale cache entry (non-critical, don't block regeneration on failure)
            try:
                await cache_service.delete(cache_key)
            except Exception as err:
                # Cache deletion failed, but we can still regenerate the response
                logger.error(
                    f"Failed to delete stale cache entry {cache_key[:20]}...: "
                    f"{type(err).__name__}: {err}. Proceeding with regeneration anyway."
                )
            # Fall through to regenerate response

    try:
        # Step 1: Generate query embedding
        logger.info(f"Research query: {request.query}")
        query_text = prepare_query_text(request.query)
        query_embedding = await embedding_service.get_embedding(query_text)

        # Step 2: Vector similarity search
        results = await vector_similarity_search(
            db=db,
            query_embedding=query_embedding,
            limit=request.max_results * 2,  # Fetch more for better selection
            year_from=request.year_from,
            year_to=request.year_to,
            language=request.language
        )

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No relevant articles found. Try broadening your search or check if articles have embeddings."
            )

        logger.info(f"Found {len(results)} relevant articles")

        # Step 3: Synthesize answer with Claude
        llm_client = await get_llm_client()
        answer, citations = await synthesize_research_answer(
            query=request.query,
            results=results[:request.max_results],  # Use top N for answer
            llm_client=llm_client
        )

        execution_ms = int((time.time() - start_time) * 1000)

        response = ResearchResponse(
            query=request.query,
            answer=answer,
            citations=citations,
            total_sources=len(results),
            execution_time_ms=execution_ms,
            from_cache=False
        )

        # Cache response for 1 hour
        await cache_service.set(
            cache_key,
            response.model_dump(),
            ttl=timedelta(hours=1)
        )

        logger.info(f"Research answer generated in {execution_ms}ms with {len(citations)} citations")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Research answer error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while generating research answer"
        )
