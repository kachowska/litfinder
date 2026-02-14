"""
OpenAlex API Integration
https://docs.openalex.org

OpenAlex is a free and open catalog of scientific papers, authors, and institutions.
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


# --- Configuration ---

OPENALEX_BASE_URL = "https://api.openalex.org"
OPENALEX_API_KEY = settings.openalex_api_key or None
OPENALEX_EMAIL = settings.openalex_email or "litfinder.ai@gmail.com"

# Rate limit: 100 requests/minute for polite pool (with email)
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3
MAX_RETRY_AFTER = 300  # Cap retry delay at 5 minutes
DEFAULT_RETRY_AFTER = 60  # Default retry delay if header is missing/invalid


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
        """
        Make async request to OpenAlex API with robust retry logic.

        Handles:
        - Rate limiting (429) with Retry-After header
        - Timeouts with exponential backoff
        - Server errors (500+) with exponential backoff
        - Client errors (400-499) fail immediately
        """
        url = f"{self.base_url}{endpoint}"

        # Add email for polite pool
        if params is None:
            params = {}
        params["mailto"] = OPENALEX_EMAIL

        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    response = await client.get(url, params=params, headers=self.headers)

                    # Handle rate limiting
                    if response.status_code == 429:
                        # Safely parse Retry-After header with fallback and capping
                        hdr = response.headers.get("Retry-After")
                        try:
                            retry_after = int(hdr) if hdr else DEFAULT_RETRY_AFTER
                            # Validate positive value
                            if retry_after <= 0:
                                logger.warning(f"Invalid Retry-After value {retry_after}, using default {DEFAULT_RETRY_AFTER}s")
                                retry_after = DEFAULT_RETRY_AFTER
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to parse Retry-After header '{hdr}': {e}. Using default {DEFAULT_RETRY_AFTER}s")
                            retry_after = DEFAULT_RETRY_AFTER

                        # Cap retry delay to prevent unbounded sleep
                        if retry_after > MAX_RETRY_AFTER:
                            logger.warning(f"Retry-After {retry_after}s exceeds maximum, capping to {MAX_RETRY_AFTER}s")
                            retry_after = MAX_RETRY_AFTER

                        logger.warning(f"Rate limited by OpenAlex. Retrying after {retry_after}s (attempt {attempt + 1}/{MAX_RETRIES})")
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()

                    # Success
                    if attempt > 0:
                        logger.info(f"Request succeeded after {attempt + 1} attempts: {endpoint}")

                    return response.json()

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < MAX_RETRIES - 1:
                    backoff = 2 ** attempt
                    logger.warning(f"Request timeout to {endpoint}. Retrying in {backoff}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(backoff)
                    continue
                logger.error(f"Request timeout after {MAX_RETRIES} attempts: {endpoint}")
                raise

            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code

                # Client errors (400-499) - don't retry (except 429 which is handled above)
                if 400 <= status_code < 500:
                    logger.error(f"Client error {status_code} from OpenAlex: {endpoint}")
                    raise

                # Server errors (500+) - retry with backoff
                if status_code >= 500 and attempt < MAX_RETRIES - 1:
                    backoff = 2 ** attempt
                    logger.warning(f"Server error {status_code} from OpenAlex. Retrying in {backoff}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    await asyncio.sleep(backoff)
                    continue

                logger.error(f"Server error {status_code} after {MAX_RETRIES} attempts: {endpoint}")
                raise

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error requesting {endpoint}: {type(e).__name__}: {e}")
                raise

        # Should never reach here, but just in case
        error_msg = f"Failed to fetch from OpenAlex after {MAX_RETRIES} attempts: {endpoint}"
        logger.error(error_msg)
        if last_exception:
            raise last_exception
        raise Exception(error_msg)
    
    async def search_works(
        self,
        query: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        language: Optional[List[str]] = None,
        concepts: Optional[List[str]] = None,
        cited_by_count_min: Optional[int] = None,
        cited_by_count_max: Optional[int] = None,
        is_oa: Optional[bool] = None,
        publication_type: Optional[str] = None,
        per_page: int = 20,
        page: Optional[int] = None,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for academic works with advanced filtering.

        Args:
            query: Search query (title, abstract)
            year_from: Filter by publication year (from)
            year_to: Filter by publication year (to)
            language: Filter by language codes (e.g., ["ru", "en"])
            concepts: Filter by concept IDs
            cited_by_count_min: Minimum citation count
            cited_by_count_max: Maximum citation count
            is_oa: Filter for open access only
            publication_type: Filter by type (article, review, etc.)
            per_page: Results per page (max 200)
            page: Page number (for page-based pagination, max 10,000 results)
            cursor: Cursor for cursor-based pagination (unlimited results)

        Returns:
            Dict with 'meta', 'results', and optionally 'next_cursor' keys

        Note:
            - Use page for simple pagination (limited to 10,000 results / 50 pages)
            - Use cursor for deep pagination (unlimited results)
            - Cursor pagination is recommended for >10,000 results
        """
        params = {
            "search": query,
            "per_page": min(per_page, 200),
            "sort": "relevance_score:desc"
        }

        # Choose pagination method
        if cursor:
            # Cursor-based pagination (unlimited results)
            params["cursor"] = cursor
            logger.debug(f"Using cursor pagination: {cursor[:20]}...")
        elif page:
            # Page-based pagination (max 10,000 results)
            params["page"] = page
            if page > 50:
                logger.warning(f"Page {page} exceeds OpenAlex limit (max 50 pages / 10,000 results). Consider using cursor pagination.")
        else:
            # Default to page 1
            params["page"] = 1

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

        # Citation count filters
        if cited_by_count_min is not None:
            filters.append(f"cited_by_count:>{cited_by_count_min - 1}")
        if cited_by_count_max is not None:
            filters.append(f"cited_by_count:<{cited_by_count_max + 1}")

        # Open access filter
        if is_oa is not None:
            filters.append(f"is_oa:{str(is_oa).lower()}")

        # Publication type filter (article, review, book-chapter, etc.)
        if publication_type:
            filters.append(f"type:{publication_type}")

        if filters:
            params["filter"] = ",".join(filters)
            logger.debug(f"Applied filters: {params['filter']}")
        
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
                logger.warning(f"Failed to parse OpenAlex work: {e}", exc_info=True)
                continue

        # Build response
        response = {
            "meta": result.get("meta", {}),
            "results": works
        }

        # Include next_cursor if present (for cursor pagination)
        if "next_cursor" in result.get("meta", {}):
            response["next_cursor"] = result["meta"]["next_cursor"]
            logger.debug(f"Next cursor available: {response['next_cursor'][:20]}...")

        return response
    
    async def get_work(self, work_id: str) -> Optional[OpenAlexWork]:
        """Get single work by ID (e.g., W123456789)."""
        try:
            result = await self._request(f"/works/{work_id}")
            return OpenAlexWork(**result)
        except Exception as e:
            logger.error(f"Failed to fetch work {work_id}: {e}", exc_info=True)
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
