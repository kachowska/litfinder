"""
OpenAlex API Integration
https://docs.openalex.org

OpenAlex is a free and open catalog of scientific papers, authors, and institutions.
"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
from pydantic import BaseModel, Field

from app.config import settings


# --- Configuration ---

OPENALEX_BASE_URL = "https://api.openalex.org"
OPENALEX_API_KEY = "AjuwfQEpWFSV0JcNLrTlYr"
OPENALEX_EMAIL = settings.openalex_email or "litfinder.ai@gmail.com"

# Rate limit: 100 requests/minute for polite pool (with email)
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3


# --- Response Models ---

class OpenAlexAuthor(BaseModel):
    """Author from OpenAlex."""
    id: str
    display_name: str
    orcid: Optional[str] = None


class OpenAlexAuthorship(BaseModel):
    """Authorship info from OpenAlex."""
    author: OpenAlexAuthor
    author_position: str = "unknown"
    institutions: List[dict] = []


class OpenAlexVenue(BaseModel):
    """Venue/journal from OpenAlex."""
    id: Optional[str] = None
    display_name: Optional[str] = None
    issn: Optional[List[str]] = None
    type: Optional[str] = None


class OpenAlexConcept(BaseModel):
    """Concept/topic from OpenAlex."""
    id: str
    display_name: str
    level: int = 0
    score: float = 0.0


class OpenAlexWork(BaseModel):
    """Work (article) from OpenAlex."""
    id: str
    doi: Optional[str] = None
    title: Optional[str] = None
    display_name: Optional[str] = None
    publication_year: Optional[int] = None
    publication_date: Optional[str] = None
    
    authorships: List[OpenAlexAuthorship] = []
    primary_location: Optional[dict] = None
    
    abstract_inverted_index: Optional[dict] = None
    
    cited_by_count: int = 0
    open_access: Optional[dict] = None  # {is_oa, oa_status, oa_url}
    best_oa_location: Optional[dict] = None
    
    concepts: List[OpenAlexConcept] = []
    
    biblio: Optional[dict] = None  # volume, issue, pages
    
    def get_abstract(self) -> Optional[str]:
        """Reconstruct abstract from inverted index."""
        if not self.abstract_inverted_index:
            return None
        
        # OpenAlex stores abstracts as inverted index: {word: [positions]}
        words = []
        for word, positions in self.abstract_inverted_index.items():
            for pos in positions:
                words.append((pos, word))
        
        words.sort(key=lambda x: x[0])
        return " ".join(word for _, word in words)
    
    def get_authors_formatted(self) -> List[dict]:
        """Get authors with initials for GOST formatting."""
        authors = []
        for authorship in self.authorships:
            name = authorship.author.display_name
            # Try to extract initials from name
            parts = name.split()
            if len(parts) >= 2:
                # Last name + initials (e.g., "John Smith" -> "Smith J.")
                last_name = parts[-1]
                initials = ".".join(p[0].upper() for p in parts[:-1]) + "."
                authors.append({
                    "name": name,
                    "last_name": last_name,
                    "initials": initials,
                    "formatted": f"{last_name} {initials}"
                })
            else:
                authors.append({
                    "name": name,
                    "last_name": name,
                    "initials": "",
                    "formatted": name
                })
        return authors


# --- API Client ---

class OpenAlexClient:
    """Async client for OpenAlex API."""
    
    def __init__(self):
        self.base_url = OPENALEX_BASE_URL
        self.headers = {
            "User-Agent": f"LitFinder/1.0 (mailto:{OPENALEX_EMAIL})",
            "Accept": "application/json"
        }
        # Add API key if available
        if OPENALEX_API_KEY:
            self.headers["api_key"] = OPENALEX_API_KEY
    
    async def _request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make async request to OpenAlex API."""
        url = f"{self.base_url}{endpoint}"
        
        # Add email for polite pool
        if params is None:
            params = {}
        params["mailto"] = OPENALEX_EMAIL
        
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    response = await client.get(url, params=params, headers=self.headers)
                    
                    if response.status_code == 429:
                        # Rate limited - wait and retry
                        retry_after = int(response.headers.get("Retry-After", 60))
                        await asyncio.sleep(retry_after)
                        continue
                    
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.TimeoutException:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception(f"Failed to fetch from OpenAlex after {MAX_RETRIES} attempts")
    
    async def search_works(
        self,
        query: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        language: Optional[List[str]] = None,
        concepts: Optional[List[str]] = None,
        per_page: int = 20,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Search for academic works.
        
        Args:
            query: Search query (title, abstract)
            year_from: Filter by publication year (from)
            year_to: Filter by publication year (to)
            language: Filter by language codes (e.g., ["ru", "en"])
            concepts: Filter by concept IDs
            per_page: Results per page (max 200)
            page: Page number
            
        Returns:
            Dict with 'meta' and 'results' keys
        """
        params = {
            "search": query,
            "per_page": min(per_page, 200),
            "page": page,
            "sort": "relevance_score:desc"
        }
        
        # Build filters
        filters = []
        
        if year_from:
            filters.append(f"publication_year:>{year_from - 1}")
        if year_to:
            filters.append(f"publication_year:<{year_to + 1}")
        # Note: OpenAlex language filter requires specific format, skip for now
        # if language:
        #     lang_filter = "|".join(language)
        #     filters.append(f"language:{lang_filter}")
        if concepts:
            concept_filter = "|".join(concepts)
            filters.append(f"concepts.id:{concept_filter}")
        
        # Note: is_oa filter limits results too much for MVP
        # filters.append("is_oa:true")
        
        if filters:
            params["filter"] = ",".join(filters)
        
        # Select specific fields to reduce response size
        params["select"] = ",".join([
            "id", "doi", "title", "display_name", "publication_year",
            "authorships", "primary_location", "abstract_inverted_index",
            "cited_by_count", "open_access", "best_oa_location",
            "concepts", "biblio"
        ])
        
        result = await self._request("/works", params)
        
        # Parse works
        works = []
        for item in result.get("results", []):
            try:
                work = OpenAlexWork(**item)
                works.append(work)
            except Exception as e:
                print(f"Error parsing work: {e}")
                continue
        
        return {
            "meta": result.get("meta", {}),
            "results": works
        }
    
    async def get_work(self, work_id: str) -> Optional[OpenAlexWork]:
        """Get single work by ID (e.g., W123456789)."""
        try:
            result = await self._request(f"/works/{work_id}")
            return OpenAlexWork(**result)
        except Exception as e:
            print(f"Error fetching work {work_id}: {e}")
            return None
    
    async def search_concepts(self, query: str, per_page: int = 10) -> List[OpenAlexConcept]:
        """Search for concepts/topics."""
        params = {
            "search": query,
            "per_page": per_page
        }
        
        result = await self._request("/concepts", params)
        
        concepts = []
        for item in result.get("results", []):
            try:
                concept = OpenAlexConcept(
                    id=item.get("id", ""),
                    display_name=item.get("display_name", ""),
                    level=item.get("level", 0)
                )
                concepts.append(concept)
            except Exception:
                continue
        
        return concepts


# --- Helper functions ---

def work_to_article_dict(work: OpenAlexWork) -> dict:
    """Convert OpenAlex work to article dict for database."""
    
    # Extract venue info
    venue_name = None
    if work.primary_location:
        source = work.primary_location.get("source", {})
        if source:
            venue_name = source.get("display_name")
    
    # Extract biblio info
    volume = None
    issue = None
    pages = None
    if work.biblio:
        volume = work.biblio.get("volume")
        issue = work.biblio.get("issue")
        first_page = work.biblio.get("first_page")
        last_page = work.biblio.get("last_page")
        if first_page and last_page:
            pages = f"{first_page}-{last_page}"
        elif first_page:
            pages = str(first_page)
    
    # Clean DOI
    doi = work.doi
    if doi and doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "")
    
    # Extract OA info
    is_oa = work.open_access.get("is_oa", False) if work.open_access else False
    pdf_url = None
    if work.best_oa_location:
        pdf_url = work.best_oa_location.get("pdf_url")
    
    return {
        "source": "openalex",
        "external_id": work.id.replace("https://openalex.org/", ""),
        "title": work.display_name or work.title or "",
        "authors": work.get_authors_formatted(),
        "year": work.publication_year,
        "journal_name": venue_name,
        "volume": int(volume) if volume and volume.isdigit() else None,
        "issue": int(issue) if issue and issue.isdigit() else None,
        "pages": pages,
        "doi": doi,
        "pdf_url": pdf_url,
        "abstract": work.get_abstract(),
        "concepts": [{"id": c.id, "name": c.display_name, "score": c.score} for c in work.concepts[:10]],
        "cited_by_count": work.cited_by_count,
        "open_access": is_oa,
        "language": "en"  # OpenAlex doesn't always provide this reliably
    }


# --- Singleton client ---
openalex_client = OpenAlexClient()
