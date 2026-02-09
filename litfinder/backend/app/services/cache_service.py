"""
Redis Caching Service
Provides caching for search results and API responses.
"""
import json
from typing import Optional, Any
import redis.asyncio as redis
from datetime import timedelta

from app.config import settings


# --- Configuration ---

CACHE_PREFIX = "litfinder:"
DEFAULT_TTL = timedelta(hours=1)
SEARCH_CACHE_TTL = timedelta(minutes=30)
ARTICLE_CACHE_TTL = timedelta(hours=24)


# --- Cache Service ---

class CacheService:
    """Redis-based caching service."""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._initialized = False
    
    async def _get_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client."""
        if not self._initialized:
            try:
                self._client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self._client.ping()
                self._initialized = True
            except Exception as e:
                print(f"Redis connection error: {e}")
                self._client = None
                self._initialized = True
        
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        client = await self._get_client()
        if client is None:
            return None
        
        try:
            full_key = f"{CACHE_PREFIX}{key}"
            value = await client.get(full_key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[timedelta] = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        client = await self._get_client()
        if client is None:
            return False
        
        try:
            full_key = f"{CACHE_PREFIX}{key}"
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            
            if ttl:
                await client.setex(full_key, int(ttl.total_seconds()), serialized)
            else:
                await client.setex(full_key, int(DEFAULT_TTL.total_seconds()), serialized)
            
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        client = await self._get_client()
        if client is None:
            return False
        
        try:
            full_key = f"{CACHE_PREFIX}{key}"
            await client.delete(full_key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        client = await self._get_client()
        if client is None:
            return False
        
        try:
            full_key = f"{CACHE_PREFIX}{key}"
            return await client.exists(full_key) > 0
        except Exception:
            return False
    
    async def clear_search_cache(self) -> int:
        """Clear all search-related cache entries."""
        client = await self._get_client()
        if client is None:
            return 0
        
        try:
            pattern = f"{CACHE_PREFIX}search:*"
            keys = []
            async for key in client.scan_iter(pattern):
                keys.append(key)
            
            if keys:
                await client.delete(*keys)
            return len(keys)
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0
    
    # --- Specialized cache methods ---
    
    async def get_search_results(self, query_hash: str) -> Optional[dict]:
        """Get cached search results."""
        return await self.get(f"search:{query_hash}")
    
    async def set_search_results(self, query_hash: str, results: dict) -> bool:
        """Cache search results."""
        return await self.set(f"search:{query_hash}", results, SEARCH_CACHE_TTL)
    
    async def get_article(self, article_id: str) -> Optional[dict]:
        """Get cached article."""
        return await self.get(f"article:{article_id}")
    
    async def set_article(self, article_id: str, article: dict) -> bool:
        """Cache article."""
        return await self.set(f"article:{article_id}", article, ARTICLE_CACHE_TTL)
    
    async def increment_rate_limit(
        self, 
        user_id: str, 
        window_seconds: int = 60
    ) -> int:
        """Increment rate limit counter for user."""
        client = await self._get_client()
        if client is None:
            return 0
        
        try:
            key = f"{CACHE_PREFIX}ratelimit:{user_id}"
            
            # Use pipeline for atomic increment + expire
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()
            
            return results[0]  # Return the incremented count
        except Exception as e:
            print(f"Rate limit error: {e}")
            return 0
    
    async def get_rate_limit(self, user_id: str) -> int:
        """Get current rate limit count for user."""
        client = await self._get_client()
        if client is None:
            return 0
        
        try:
            key = f"{CACHE_PREFIX}ratelimit:{user_id}"
            value = await client.get(key)
            return int(value) if value else 0
        except Exception:
            return 0


# --- Helper function for query hashing ---

def hash_query(query: str, filters: Optional[dict] = None) -> str:
    """Create a hash key for caching search queries."""
    import hashlib
    
    # Normalize query
    normalized = query.lower().strip()
    
    # Include filters in hash
    if filters:
        filter_str = json.dumps(filters, sort_keys=True)
        normalized += f":{filter_str}"
    
    # Create short hash
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


# --- Singleton instance ---
cache_service = CacheService()
