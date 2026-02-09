"""
Search API Endpoints
POST /api/v1/search - Main semantic search
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


router = APIRouter()


# --- Request/Response Schemas ---

class SearchFilters(BaseModel):
    """Search filters."""
    year_from: Optional[int] = Field(None, ge=1900, le=2030)
    year_to: Optional[int] = Field(None, ge=1900, le=2030)
    language: Optional[List[str]] = Field(default=["ru", "en"])
    concepts: Optional[List[str]] = None
    source: Optional[List[str]] = Field(default=["openalex", "cyberleninka"])


class SearchRequest(BaseModel):
    """Search request schema."""
    query: str = Field(..., min_length=3, max_length=500, description="Search query")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
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
    filters_applied: Optional[dict] = None
    execution_time_ms: int


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
        year_from=filters.year_from,
        year_to=filters.year_to,
        language=filters.language,
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
        filters_applied=filters.model_dump() if filters else None,
        execution_time_ms=result["execution_time_ms"]
    )


@router.get("/search/suggestions")
async def search_suggestions(q: str = ""):
    """Get search query suggestions based on popular queries."""
    # TODO: Implement based on search history
    return {"suggestions": []}
