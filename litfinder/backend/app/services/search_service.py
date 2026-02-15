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
        cursor: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        language: Optional[List[str]] = None,
        cited_by_count_min: Optional[int] = None,
        cited_by_count_max: Optional[int] = None,
        is_oa: Optional[bool] = None,
        publication_type: Optional[str] = None,
        sources: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> dict:
        """
        Search for articles across all sources.

        Returns dict with total, results, next_cursor, and execution_time_ms.
        """
        start_time = time.time()
        
        # Check cache first (skip cache for cursor pagination)
        if use_cache and not cursor:
            cache_key = hash_query(query, {
                "limit": limit,
                "offset": offset,
                "year_from": year_from,
                "year_to": year_to,
                "language": language,
                "cited_by_count_min": cited_by_count_min,
                "cited_by_count_max": cited_by_count_max,
                "is_oa": is_oa,
                "publication_type": publication_type,
                "sources": sources
            })

            cached = await cache_service.get_search_results(cache_key)
            if cached:
                cached["from_cache"] = True
                cached["execution_time_ms"] = int((time.time() - start_time) * 1000)
                return cached
        
        results = []
        total = 0
        next_cursor = None

        # Determine which sources to search
        search_sources = sources or ["openalex", "cyberleninka"]

        # Search sources in parallel
        tasks = []

        if "openalex" in search_sources:
            tasks.append(self._search_openalex(
                query, limit, offset, cursor,
                year_from, year_to, language,
                cited_by_count_min, cited_by_count_max,
                is_oa, publication_type
            ))

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
                    # Capture next_cursor from OpenAlex (first source with cursor)
                    if not next_cursor and res.get("next_cursor"):
                        next_cursor = res["next_cursor"]
        
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
            "next_cursor": next_cursor,
            "execution_time_ms": execution_ms,
            "from_cache": False
        }

        # Cache results (skip caching for cursor pagination)
        if use_cache and results and not cursor:
            await cache_service.set_search_results(cache_key, response)

        return response
    
    async def _search_openalex(
        self,
        query: str,
        limit: int,
        offset: int,
        cursor: Optional[str],
        year_from: Optional[int],
        year_to: Optional[int],
        language: Optional[List[str]],
        cited_by_count_min: Optional[int],
        cited_by_count_max: Optional[int],
        is_oa: Optional[bool],
        publication_type: Optional[str]
    ) -> dict:
        """Search OpenAlex source with advanced filtering."""
        try:
            # Choose pagination method
            if cursor:
                # Use cursor-based pagination
                page = None
            else:
                # Use page-based pagination
                page = (offset // limit) + 1

            openalex_results = await openalex_client.search_works(
                query=query,
                year_from=year_from,
                year_to=year_to,
                language=language,
                cited_by_count_min=cited_by_count_min,
                cited_by_count_max=cited_by_count_max,
                is_oa=is_oa,
                publication_type=publication_type,
                per_page=limit,
                page=page,
                cursor=cursor
            )

            articles = []
            for work in openalex_results.get("results", []):
                article_dict = work_to_article_dict(work)
                article_dict["relevance_score"] = 0.9
                articles.append(article_dict)

            meta = openalex_results.get("meta", {})
            response = {
                "total": meta.get("count", 0),
                "results": articles
            }

            # Include next_cursor if available
            if "next_cursor" in openalex_results:
                response["next_cursor"] = openalex_results["next_cursor"]

            return response

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

    async def get_articles_by_ids(self, article_ids: List[str]) -> dict[str, dict]:
        """
        Batch fetch articles by IDs (from cache, DB, or external sources).

        More efficient than calling get_article_by_id in a loop (avoids N+1 queries).

        Args:
            article_ids: List of article IDs to fetch

        Returns:
            Dictionary mapping article_id -> article_dict for found articles
        """
        if not article_ids:
            return {}

        results = {}
        missing_ids = []

        # Step 1: Check cache for all IDs
        for article_id in article_ids:
            cached = await cache_service.get_article(article_id)
            if cached:
                results[article_id] = cached
            else:
                missing_ids.append(article_id)

        if not missing_ids:
            return results

        # Step 2: Batch query DB for uncached IDs
        db_result = await self.db.execute(
            select(Article).where(Article.id.in_(missing_ids))
        )
        db_articles = db_result.scalars().all()

        # Store DB results and cache them
        db_found_ids = set()
        for article in db_articles:
            article_dict = article.to_dict()
            results[article.id] = article_dict
            db_found_ids.add(article.id)
            await cache_service.set_article(article.id, article_dict)

        # Step 3: Fetch remaining IDs from OpenAlex (in parallel)
        still_missing = [aid for aid in missing_ids if aid not in db_found_ids]

        if still_missing:
            # Filter for OpenAlex-like IDs
            openalex_ids = [
                aid for aid in still_missing
                if aid.startswith("W") or aid.startswith("openalex_")
            ]

            if openalex_ids:
                # Fetch in parallel using asyncio.gather
                async def fetch_one(article_id: str):
                    work_id = article_id.replace("openalex_", "")
                    work = await openalex_client.get_work(work_id)
                    if work:
                        article_dict = work_to_article_dict(work)
                        await cache_service.set_article(article_id, article_dict)
                        return (article_id, article_dict)
                    return (article_id, None)

                openalex_results = await asyncio.gather(
                    *[fetch_one(aid) for aid in openalex_ids],
                    return_exceptions=True
                )

                # Process results
                for result in openalex_results:
                    if isinstance(result, tuple) and result[1] is not None:
                        article_id, article_dict = result
                        results[article_id] = article_dict

        return results
