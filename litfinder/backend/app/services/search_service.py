"""
Search Service
Core business logic for article search with caching and multiple sources.
"""
import time
import asyncio
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.article import Article
from app.integrations.openalex import openalex_client, work_to_article_dict
from app.integrations.cyberleninka import cyberleninka_client, article_to_dict as cl_article_to_dict
from app.services.cache_service import cache_service, hash_query
from app.services.ranking_service import ranking_service


class SearchService:
    """Service for searching academic articles."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        language: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> dict:
        """
        Search for articles across all sources.
        
        Returns dict with total, results, and execution_time_ms.
        """
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = hash_query(query, {
                "limit": limit,
                "offset": offset,
                "year_from": year_from,
                "year_to": year_to,
                "language": language,
                "sources": sources
            })
            
            cached = await cache_service.get_search_results(cache_key)
            if cached:
                cached["from_cache"] = True
                cached["execution_time_ms"] = int((time.time() - start_time) * 1000)
                return cached
        
        results = []
        total = 0
        
        # Determine which sources to search
        search_sources = sources or ["openalex", "cyberleninka"]
        
        # Search sources in parallel
        tasks = []
        
        if "openalex" in search_sources:
            tasks.append(self._search_openalex(query, limit, offset, year_from, year_to, language))
        
        if "cyberleninka" in search_sources:
            tasks.append(self._search_cyberleninka(query, limit, year_from, year_to))
        
        if tasks:
            source_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in source_results:
                if isinstance(res, Exception):
                    print(f"Search source error: {res}")
                    continue
                if res:
                    results.extend(res.get("results", []))
                    total += res.get("total", 0)
        
        # Rank results using multi-signal scoring
        if results:
            results = ranking_service.rank_results(
                results=results,
                query=query,
                preferred_language=language[0] if language else "en"
            )
        
        execution_ms = int((time.time() - start_time) * 1000)
        
        response = {
            "total": total,
            "results": results[:limit],
            "execution_time_ms": execution_ms,
            "from_cache": False
        }
        
        # Cache results
        if use_cache and results:
            await cache_service.set_search_results(cache_key, response)
        
        return response
    
    async def _search_openalex(
        self,
        query: str,
        limit: int,
        offset: int,
        year_from: Optional[int],
        year_to: Optional[int],
        language: Optional[List[str]]
    ) -> dict:
        """Search OpenAlex source."""
        try:
            page = (offset // limit) + 1
            openalex_results = await openalex_client.search_works(
                query=query,
                year_from=year_from,
                year_to=year_to,
                language=language,
                per_page=limit,
                page=page
            )
            
            articles = []
            for work in openalex_results.get("results", []):
                article_dict = work_to_article_dict(work)
                article_dict["relevance_score"] = 0.9
                articles.append(article_dict)
            
            meta = openalex_results.get("meta", {})
            return {
                "total": meta.get("count", 0),
                "results": articles
            }
            
        except Exception as e:
            print(f"OpenAlex search error: {e}")
            return {"total": 0, "results": []}
    
    async def _search_cyberleninka(
        self,
        query: str,
        limit: int,
        year_from: Optional[int],
        year_to: Optional[int]
    ) -> dict:
        """Search CyberLeninka source."""
        try:
            # Convert years to dates for OAI-PMH
            from_date = f"{year_from}-01-01" if year_from else None
            until_date = f"{year_to}-12-31" if year_to else None
            
            cl_results = await cyberleninka_client.search(
                query=query,
                from_date=from_date,
                until_date=until_date,
                limit=limit
            )
            
            articles = []
            for article in cl_results.get("results", []):
                article_dict = cl_article_to_dict(article)
                article_dict["relevance_score"] = 0.8
                articles.append(article_dict)
            
            return {
                "total": cl_results.get("total", 0),
                "results": articles
            }
            
        except Exception as e:
            print(f"CyberLeninka search error: {e}")
            return {"total": 0, "results": []}
    
    async def get_article_by_id(self, article_id: str) -> Optional[dict]:
        """Get article by ID (from cache, DB, or fetch from source)."""
        # Try cache first
        cached = await cache_service.get_article(article_id)
        if cached:
            return cached
        
        # Try DB
        result = await self.db.execute(
            select(Article).where(Article.id == article_id)
        )
        article = result.scalar_one_or_none()
        
        if article:
            article_dict = article.to_dict()
            await cache_service.set_article(article_id, article_dict)
            return article_dict
        
        # Try OpenAlex if ID looks like OpenAlex ID
        if article_id.startswith("W") or article_id.startswith("openalex_"):
            work_id = article_id.replace("openalex_", "")
            work = await openalex_client.get_work(work_id)
            if work:
                article_dict = work_to_article_dict(work)
                await cache_service.set_article(article_id, article_dict)
                return article_dict
        
        return None
