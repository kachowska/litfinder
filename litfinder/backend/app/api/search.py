"""
Search API Endpoints
POST /api/v1/search - Main semantic search
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db


router = APIRouter()


# --- Request/Response Schemas ---

class SearchFilters(BaseModel):
    """Search filters."""
    year_from: Optional[int] = Field(None, ge=1900, le=2030, description="Filter by publication year (from)")
    year_to: Optional[int] = Field(None, ge=1900, le=2030, description="Filter by publication year (to)")
    language: Optional[List[str]] = Field(default=["ru", "en"], description="Language codes")
    concepts: Optional[List[str]] = Field(None, description="OpenAlex concept IDs")
    cited_by_count_min: Optional[int] = Field(None, ge=0, description="Minimum citation count")
    cited_by_count_max: Optional[int] = Field(None, ge=0, description="Maximum citation count")
    is_oa: Optional[bool] = Field(None, description="Filter for open access articles only")
    publication_type: Optional[str] = Field(None, description="Publication type (article, review, book-chapter, etc.)")
    source: Optional[List[str]] = Field(default=["openalex", "cyberleninka"], description="Sources to search")

    @model_validator(mode='after')
    def validate_ranges(self) -> 'SearchFilters':
        """Validate that min <= max for citation counts and year ranges."""
        # Validate citation count range
        if self.cited_by_count_min is not None and self.cited_by_count_max is not None:
            if self.cited_by_count_min > self.cited_by_count_max:
                raise ValueError(
                    f"cited_by_count_min ({self.cited_by_count_min}) must be <= "
                    f"cited_by_count_max ({self.cited_by_count_max})"
                )

        # Validate year range
        if self.year_from is not None and self.year_to is not None:
            if self.year_from > self.year_to:
                raise ValueError(
                    f"year_from ({self.year_from}) must be <= year_to ({self.year_to})"
                )

        return self


class SearchRequest(BaseModel):
    """Search request schema."""
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    limit: int = Field(20, ge=1, le=100, description="Results per page")
    offset: int = Field(0, ge=0, description="Offset for page-based pagination")
    cursor: Optional[str] = Field(None, description="Cursor for cursor-based pagination (use instead of offset for >10k results)")
    filters: Optional[SearchFilters] = None


class AuthorResponse(BaseModel):
    """Author info."""
    id: Optional[str] = None
    name: str
    initials: Optional[str] = None


class ArticleResponse(BaseModel):
    """Article in search results."""
    id: str
    source: str
    title: str
    authors: List[AuthorResponse]
    year: Optional[int]
    journal: Optional[str]
    volume: Optional[int]
    issue: Optional[int]
    pages: Optional[str]
    doi: Optional[str]
    pdf_url: Optional[str]
    abstract: Optional[str]
    abstract_snippet: Optional[str]
    cited_by_count: int = 0
    concepts: List[dict] = []
    relevance_score: float = 0.0
    open_access: bool = False
    keywords: List[str] = []


class SearchResponse(BaseModel):
    """Search response schema."""
    total: int
    results: List[ArticleResponse]
    next_cursor: Optional[str] = Field(None, description="Cursor for next page (if available)")
    filters_applied: Optional[dict] = None
    execution_time_ms: int


class SuggestionsResponse(BaseModel):
    """Search suggestions response schema."""
    suggestions: List[str] = Field(
        ...,
        description="List of suggested search queries ordered by popularity and recency"
    )


# --- Endpoints ---

@router.post("/search", response_model=SearchResponse)
async def search_articles(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Search for academic articles.
    
    Performs semantic search across OpenAlex and CyberLeninka sources.
    Returns articles sorted by relevance score.
    """
    from app.services.search_service import SearchService
    
    service = SearchService(db)
    
    # Extract filters
    filters = request.filters or SearchFilters()
    
    # Perform search
    result = await service.search(
        query=request.query,
        limit=request.limit,
        offset=request.offset,
        cursor=request.cursor,
        year_from=filters.year_from,
        year_to=filters.year_to,
        language=filters.language,
        cited_by_count_min=filters.cited_by_count_min,
        cited_by_count_max=filters.cited_by_count_max,
        is_oa=filters.is_oa,
        publication_type=filters.publication_type,
        sources=filters.source
    )
    
    # Convert results to response format
    articles = []
    for item in result["results"]:
        authors = [
            AuthorResponse(
                id=a.get("id"),
                name=a.get("name", ""),
                initials=a.get("initials")
            ) for a in item.get("authors", [])
        ]
        
        articles.append(ArticleResponse(
            id=item.get("external_id", ""),
            source=item.get("source", "openalex"),
            title=item.get("title", ""),
            authors=authors,
            year=item.get("year"),
            journal=item.get("journal_name"),
            volume=item.get("volume"),
            issue=item.get("issue"),
            pages=item.get("pages"),
            doi=item.get("doi"),
            pdf_url=item.get("pdf_url"),
            abstract=item.get("abstract"),
            abstract_snippet=item.get("abstract", "")[:200] if item.get("abstract") else None,
            cited_by_count=item.get("cited_by_count", 0),
            concepts=item.get("concepts", []),
            relevance_score=item.get("relevance_score", 0.0),
            open_access=item.get("open_access", False),
            keywords=[]
        ))
    
    return SearchResponse(
        total=result["total"],
        results=articles,
        next_cursor=result.get("next_cursor"),
        filters_applied=filters.model_dump() if filters else None,
        execution_time_ms=result["execution_time_ms"]
    )


@router.get("/search/suggestions", response_model=SuggestionsResponse)
async def search_suggestions(
    q: str = Query(
        "",
        min_length=0,
        max_length=200,
        description="Query prefix to match (case-insensitive). Leave empty to get popular searches.",
        example="machine learning"
    ),
    limit: int = Query(
        5,
        ge=1,
        le=10,
        description="Maximum number of suggestions to return",
        example=5
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Get search query suggestions based on popular queries.

    Returns suggestions from search history that match the query prefix.
    Ordered by frequency (primary) and recency (secondary tie-breaker).

    If no query prefix is provided, returns the most popular recent searches.
    """
    from app.models.search_history import SearchHistory

    if not q or len(q) < 2:
        # Return most popular recent searches if no query
        # Group by case-normalized query to avoid duplicates like "ML" and "ml"
        # Use func.min to return one representative original-cased version
        result = await db.execute(
            select(
                func.min(SearchHistory.query).label('query'),
                func.count(SearchHistory.id).label('count'),
                func.max(SearchHistory.created_at).label('last_used')
            )
            .group_by(func.lower(SearchHistory.query))
            .order_by(
                func.count(SearchHistory.id).desc(),
                func.max(SearchHistory.created_at).desc()
            )
            .limit(limit)
        )
        suggestions = [row[0] for row in result.all()]
    else:
        # Escape LIKE metacharacters to prevent injection and unexpected matching
        # Must escape backslash first, then percent and underscore
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"{escaped.lower()}%"

        # Return queries matching the prefix, ordered by frequency then recency
        # Group by case-normalized query to collapse "Machine Learning" and "machine learning"
        result = await db.execute(
            select(
                func.min(SearchHistory.query).label('query'),
                func.count(SearchHistory.id).label('count'),
                func.max(SearchHistory.created_at).label('last_used')
            )
            .where(func.lower(SearchHistory.query).like(pattern, escape="\\"))
            .group_by(func.lower(SearchHistory.query))
            .order_by(
                func.count(SearchHistory.id).desc(),
                func.max(SearchHistory.created_at).desc()
            )
            .limit(limit)
        )
        suggestions = [row[0] for row in result.all()]

    return {"suggestions": suggestions}
