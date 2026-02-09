"""
Claude API Integration for Query Enhancement
Uses Anthropic's Claude to reformulate and expand search queries.
"""
import asyncio
from typing import List, Optional
from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.config import settings


# --- Configuration ---

CLAUDE_MODEL = "claude-3-haiku-20240307"  # Fast and cost-effective for query reformulation
MAX_TOKENS = 500
TEMPERATURE = 0.3  # Lower temperature for more consistent outputs


# --- Response Models ---

class EnhancedQuery(BaseModel):
    """Enhanced search query with variations."""
    original: str
    reformulated: str
    keywords: List[str]
    synonyms: List[str]
    english_translation: Optional[str] = None
    russian_translation: Optional[str] = None


# --- Claude Client ---

class ClaudeQueryEnhancer:
    """Use Claude to enhance and reformulate search queries."""
    
    def __init__(self):
        self.client = None
        self._initialized = False
    
    def _ensure_client(self):
        """Lazily initialize Anthropic client."""
        if not self._initialized:
            api_key = settings.anthropic_api_key
            if api_key:
                self.client = AsyncAnthropic(api_key=api_key)
            self._initialized = True
    
    async def enhance_query(self, query: str, language: str = "auto") -> EnhancedQuery:
        """
        Enhance a search query using Claude.
        
        Args:
            query: Original search query
            language: Query language ("ru", "en", or "auto")
            
        Returns:
            EnhancedQuery with reformulated query, keywords, and translations
        """
        self._ensure_client()
        
        # If no API key, return basic enhancement
        if self.client is None:
            return self._basic_enhance(query)
        
        try:
            prompt = f"""You are an academic search query optimizer. Your task is to enhance the search query for finding academic papers.

Original query: "{query}"

Provide:
1. A reformulated, more precise academic search query
2. 5-7 relevant academic keywords
3. 3-5 synonyms or related terms
4. English translation (if query is in Russian)
5. Russian translation (if query is in English)

Respond in JSON format:
{{
  "reformulated": "enhanced query here",
  "keywords": ["keyword1", "keyword2", ...],
  "synonyms": ["synonym1", "synonym2", ...],
  "english_translation": "translation or null",
  "russian_translation": "перевод или null"
}}

Important: Keep the reformulated query concise and focused on academic terminology."""

            message = await self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse response
            response_text = message.content[0].text
            
            # Try to extract JSON from response
            import json
            try:
                # Handle potential markdown code blocks
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                
                data = json.loads(response_text.strip())
                
                return EnhancedQuery(
                    original=query,
                    reformulated=data.get("reformulated", query),
                    keywords=data.get("keywords", []),
                    synonyms=data.get("synonyms", []),
                    english_translation=data.get("english_translation"),
                    russian_translation=data.get("russian_translation")
                )
            except json.JSONDecodeError:
                # If JSON parsing fails, return basic enhancement
                return self._basic_enhance(query)
                
        except Exception as e:
            print(f"Claude query enhancement error: {e}")
            return self._basic_enhance(query)
    
    def _basic_enhance(self, query: str) -> EnhancedQuery:
        """Basic query enhancement without AI."""
        # Simple keyword extraction
        words = query.lower().split()
        keywords = [w for w in words if len(w) > 3]
        
        return EnhancedQuery(
            original=query,
            reformulated=query,
            keywords=keywords[:7],
            synonyms=[],
            english_translation=None,
            russian_translation=None
        )
    
    async def generate_search_suggestions(
        self, 
        query: str, 
        results_count: int
    ) -> List[str]:
        """
        Generate search suggestions based on query and results.
        
        Args:
            query: Current search query
            results_count: Number of results found
            
        Returns:
            List of suggested alternative queries
        """
        self._ensure_client()
        
        if self.client is None:
            return []
        
        try:
            prompt = f"""Based on the academic search query "{query}" which returned {results_count} results,
suggest 3 alternative or refined search queries that might yield better academic results.

Respond with just the queries, one per line, no numbering or explanations."""

            message = await self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=200,
                temperature=0.5,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            suggestions = message.content[0].text.strip().split("\n")
            return [s.strip() for s in suggestions if s.strip()][:3]
            
        except Exception as e:
            print(f"Claude suggestions error: {e}")
            return []


# --- Singleton instance ---
query_enhancer = ClaudeQueryEnhancer()
