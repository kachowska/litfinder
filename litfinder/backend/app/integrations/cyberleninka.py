"""
CyberLeninka OAI-PMH Integration
https://cyberleninka.ru/oai

CyberLeninka is the largest Russian open access repository of scientific articles.
Uses OAI-PMH 2.0 protocol for harvesting metadata.
"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
from xml.etree import ElementTree as ET
from pydantic import BaseModel

from app.config import settings


# --- Configuration ---

CYBERLENINKA_OAI_URL = "https://cyberleninka.ru/oai"
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3

# OAI-PMH namespaces
NAMESPACES = {
    "oai": "http://www.openarchives.org/OAI/2.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/"
}


# --- Response Models ---

class CyberLeninkaArticle(BaseModel):
    """Article from CyberLeninka."""
    identifier: str
    title: Optional[str] = None
    creators: List[str] = []
    subjects: List[str] = []
    description: Optional[str] = None
    publisher: Optional[str] = None
    date: Optional[str] = None
    type: Optional[str] = None
    format: Optional[str] = None
    source: Optional[str] = None  # Journal name
    language: Optional[str] = None
    rights: Optional[str] = None
    
    def get_year(self) -> Optional[int]:
        """Extract year from date field."""
        if not self.date:
            return None
        try:
            # Date can be in various formats: YYYY, YYYY-MM, YYYY-MM-DD
            return int(self.date[:4])
        except (ValueError, IndexError):
            return None
    
    def get_authors_formatted(self) -> List[dict]:
        """Get authors formatted for GOST."""
        authors = []
        for creator in self.creators:
            # CyberLeninka usually has format: "Фамилия И.О." or "Фамилия Имя Отчество"
            parts = creator.strip().split()
            if len(parts) >= 1:
                last_name = parts[0]
                initials = ""
                if len(parts) >= 2:
                    # Check if already initials (И.О.) or full names
                    if all(len(p) <= 3 and "." in p for p in parts[1:]):
                        initials = "".join(parts[1:])
                    else:
                        initials = ".".join(p[0].upper() for p in parts[1:]) + "."
                
                authors.append({
                    "name": creator,
                    "last_name": last_name,
                    "initials": initials,
                    "formatted": f"{last_name} {initials}".strip()
                })
        return authors


# --- OAI-PMH Client ---

class CyberLeninkaClient:
    """Async client for CyberLeninka OAI-PMH API."""
    
    def __init__(self):
        self.base_url = CYBERLENINKA_OAI_URL
        self.headers = {
            "User-Agent": "LitFinder/1.0 (Academic Search Platform)",
            "Accept": "application/xml"
        }
    
    async def _request(self, params: Dict[str, str]) -> Optional[ET.Element]:
        """Make async OAI-PMH request."""
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    response = await client.get(
                        self.base_url, 
                        params=params, 
                        headers=self.headers
                    )
                    response.raise_for_status()
                    
                    # Parse XML
                    root = ET.fromstring(response.content)
                    
                    # Check for OAI-PMH errors
                    error = root.find(".//oai:error", NAMESPACES)
                    if error is not None:
                        error_code = error.get("code", "unknown")
                        error_msg = error.text or "Unknown error"
                        print(f"OAI-PMH error: {error_code} - {error_msg}")
                        return None
                    
                    return root
                    
            except httpx.TimeoutException:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                print(f"CyberLeninka timeout after {MAX_RETRIES} attempts")
                return None
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                print(f"CyberLeninka HTTP error: {e.response.status_code}")
                return None
            except ET.ParseError as e:
                print(f"CyberLeninka XML parse error: {e}")
                return None
        
        return None
    
    def _parse_record(self, record: ET.Element) -> Optional[CyberLeninkaArticle]:
        """Parse OAI-PMH record to CyberLeninkaArticle."""
        try:
            # Get identifier
            header = record.find("oai:header", NAMESPACES)
            if header is None:
                return None
            
            identifier_elem = header.find("oai:identifier", NAMESPACES)
            if identifier_elem is None or not identifier_elem.text:
                return None
            
            identifier = identifier_elem.text
            
            # Get metadata
            metadata = record.find(".//oai_dc:dc", NAMESPACES)
            if metadata is None:
                return None
            
            # Extract Dublin Core fields
            def get_text(tag: str) -> Optional[str]:
                elem = metadata.find(f"dc:{tag}", NAMESPACES)
                return elem.text if elem is not None and elem.text else None
            
            def get_all_text(tag: str) -> List[str]:
                elems = metadata.findall(f"dc:{tag}", NAMESPACES)
                return [e.text for e in elems if e.text]
            
            return CyberLeninkaArticle(
                identifier=identifier,
                title=get_text("title"),
                creators=get_all_text("creator"),
                subjects=get_all_text("subject"),
                description=get_text("description"),
                publisher=get_text("publisher"),
                date=get_text("date"),
                type=get_text("type"),
                format=get_text("format"),
                source=get_text("source"),
                language=get_text("language"),
                rights=get_text("rights")
            )
            
        except Exception as e:
            print(f"Error parsing CyberLeninka record: {e}")
            return None
    
    async def search(
        self,
        query: str,
        from_date: Optional[str] = None,
        until_date: Optional[str] = None,
        set_spec: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search CyberLeninka articles via OAI-PMH ListRecords.
        
        Note: OAI-PMH doesn't support text search natively.
        This method lists records and filters client-side.
        For production, consider using CyberLeninka's search API if available.
        
        Args:
            query: Search query (for client-side filtering)
            from_date: Filter by date (YYYY-MM-DD)
            until_date: Filter by date (YYYY-MM-DD)
            set_spec: OAI-PMH set specification
            limit: Maximum results
            
        Returns:
            Dict with 'total' and 'results' keys
        """
        params = {
            "verb": "ListRecords",
            "metadataPrefix": "oai_dc"
        }
        
        if from_date:
            params["from"] = from_date
        if until_date:
            params["until"] = until_date
        if set_spec:
            params["set"] = set_spec
        
        root = await self._request(params)
        if root is None:
            return {"total": 0, "results": []}
        
        # Parse records
        records = root.findall(".//oai:record", NAMESPACES)
        articles = []
        query_lower = query.lower()
        
        for record in records:
            article = self._parse_record(record)
            if article is None:
                continue
            
            # Client-side text filtering
            searchable = " ".join([
                article.title or "",
                article.description or "",
                " ".join(article.subjects),
                " ".join(article.creators)
            ]).lower()
            
            if query_lower in searchable:
                articles.append(article)
                if len(articles) >= limit:
                    break
        
        return {
            "total": len(articles),
            "results": articles
        }
    
    async def get_record(self, identifier: str) -> Optional[CyberLeninkaArticle]:
        """Get single record by OAI identifier."""
        params = {
            "verb": "GetRecord",
            "metadataPrefix": "oai_dc",
            "identifier": identifier
        }
        
        root = await self._request(params)
        if root is None:
            return None
        
        record = root.find(".//oai:record", NAMESPACES)
        if record is None:
            return None
        
        return self._parse_record(record)
    
    async def list_sets(self) -> List[Dict[str, str]]:
        """List available OAI-PMH sets (categories/journals)."""
        params = {"verb": "ListSets"}
        
        root = await self._request(params)
        if root is None:
            return []
        
        sets = []
        for set_elem in root.findall(".//oai:set", NAMESPACES):
            spec = set_elem.find("oai:setSpec", NAMESPACES)
            name = set_elem.find("oai:setName", NAMESPACES)
            if spec is not None and name is not None:
                sets.append({
                    "spec": spec.text,
                    "name": name.text
                })
        
        return sets


# --- Helper functions ---

def article_to_dict(article: CyberLeninkaArticle) -> dict:
    """Convert CyberLeninka article to standard dict format."""
    return {
        "source": "cyberleninka",
        "external_id": article.identifier.replace("oai:cyberleninka.ru:", ""),
        "title": article.title or "",
        "authors": article.get_authors_formatted(),
        "year": article.get_year(),
        "journal_name": article.source,
        "volume": None,
        "issue": None,
        "pages": None,
        "doi": None,
        "pdf_url": f"https://cyberleninka.ru/article/n/{article.identifier.split(':')[-1]}/pdf" if article.identifier else None,
        "abstract": article.description,
        "concepts": [{"id": "", "name": subj, "score": 0.5} for subj in article.subjects[:10]],
        "cited_by_count": 0,
        "open_access": True,  # CyberLeninka is always open access
        "language": article.language or "ru"
    }


# --- Singleton client ---
cyberleninka_client = CyberLeninkaClient()
