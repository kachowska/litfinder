"""
Bibliography API Endpoints
GOST bibliography generation and export
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import base64

from app.database import get_db
from app.services.gost_formatter import (
    gost_formatter, 
    article_to_bibliography_entry,
    BibliographyEntry
)
from app.services.export_service import export_service, export_articles
from app.services.search_service import SearchService


router = APIRouter()


# --- Schemas ---

class BibliographyRequest(BaseModel):
    """Bibliography generation request."""
    article_ids: List[str] = Field(default=[], max_length=100)
    articles: List[dict] = Field(default=[])  # Direct article data
    style: str = Field("GOST_R_7_0_100_2018")
    sort_by: str = Field("author")  # author, year, title
    language: str = Field("ru")
    numbered: bool = True


class ExportRequest(BaseModel):
    """Export request."""
    articles: List[dict]
    format: str = Field("gost")  # gost, bibtex, ris, docx
    sort_by: str = Field("author")


class ValidationResult(BaseModel):
    """Validation result."""
    status: str
    errors: List[str] = []
    warnings: List[str] = []


class BibliographyResponse(BaseModel):
    """Bibliography generation response."""
    status: str
    formatted_list: List[str]
    bibtex: Optional[str] = None
    ris: Optional[str] = None
    validation: ValidationResult
    metadata: dict = {}


# --- Endpoints ---

@router.post("/bibliography", response_model=BibliographyResponse)
async def generate_bibliography(
    request: BibliographyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate formatted bibliography list.
    
    Formats articles according to ГОСТ Р 7.0.100-2018.
    Returns formatted text + export formats (BibTeX, RIS).
    """
    articles = request.articles
    warnings = []
    errors = []
    
    # If article_ids provided, fetch from search service
    if request.article_ids and not articles:
        search_service = SearchService(db)
        for article_id in request.article_ids:
            article = await search_service.get_article_by_id(article_id)
            if article:
                articles.append(article)
            else:
                warnings.append(f"Article not found: {article_id}")
    
    if not articles:
        return BibliographyResponse(
            status="error",
            formatted_list=[],
            validation=ValidationResult(status="error", errors=["No articles provided"]),
            metadata={}
        )
    
    # Convert to bibliography entries
    entries = []
    for article in articles:
        try:
            entry = article_to_bibliography_entry(article)
            entries.append(entry)
            
            # Validation warnings
            if not entry.authors:
                warnings.append(f"Missing authors: {entry.title[:50]}")
            if not entry.year:
                warnings.append(f"Missing year: {entry.title[:50]}")
        except Exception as e:
            errors.append(f"Failed to parse: {str(e)}")
    
    # Format according to style
    formatted = gost_formatter.format_list(entries, request.sort_by)
    
    # Generate export formats
    bibtex = export_service.export_to_bibtex(entries)
    ris = export_service.export_to_ris(entries)
    
    return BibliographyResponse(
        status="success",
        formatted_list=formatted,
        bibtex=bibtex,
        ris=ris,
        validation=ValidationResult(
            status="warning" if warnings else "success",
            warnings=warnings,
            errors=errors
        ),
        metadata={
            "total_sources": len(entries),
            "style": request.style,
            "sort_by": request.sort_by
        }
    )


@router.post("/export/{format}")
async def export_bibliography(
    format: str,
    request: ExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Export bibliography to file format.
    
    Supported formats: gost, bibtex, ris, docx
    """
    if format not in ["gost", "text", "bibtex", "ris", "docx", "word"]:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    
    if not request.articles:
        raise HTTPException(status_code=400, detail="No articles provided")
    
    result = export_articles(
        articles=request.articles,
        format=format,
        sort_by=request.sort_by
    )
    
    # For binary formats, return as file download
    if result.get("is_binary"):
        content = base64.b64decode(result["content"])
        return Response(
            content=content,
            media_type=result["mime_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{result["filename"]}"'
            }
        )
    
    return result


@router.post("/format/preview")
async def preview_format(
    article: dict,
    style: str = "GOST_R_7_0_100_2018"
):
    """
    Preview formatting for a single article.
    
    Useful for testing without full bibliography generation.
    """
    try:
        entry = article_to_bibliography_entry(article)
        formatted = gost_formatter.format(entry)
        
        return {
            "formatted": formatted,
            "style": style,
            "entry_type": entry.source_type.value
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/styles")
async def list_styles():
    """List available bibliography styles."""
    return {
        "styles": [
            {
                "id": "GOST_R_7_0_100_2018",
                "name": "ГОСТ Р 7.0.100-2018",
                "description": "Российский стандарт библиографического описания",
                "default": True
            },
            {
                "id": "VAK",
                "name": "ВАК",
                "description": "Формат для диссертаций ВАК",
                "default": False
            }
        ],
        "export_formats": ["gost", "bibtex", "ris", "docx"]
    }
