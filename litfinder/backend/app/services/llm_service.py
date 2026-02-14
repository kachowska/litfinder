"""
LLM Service
Claude AI client with task-based model routing and retry logic
"""
import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any, List, AsyncIterator
from enum import Enum
import anthropic
from anthropic import AsyncAnthropic, APIError, APIConnectionError, RateLimitError

from app.config import settings

# Logger
logger = logging.getLogger(__name__)


# --- Task Types ---

class LLMTask(str, Enum):
    """LLM task types with associated model routing."""
    RESEARCH_ANSWER = "research_answer"  # Sonnet 4 - complex synthesis
    DATA_EXTRACTION = "data_extraction"  # Haiku 4.5 - structured extraction
    CHAT_LIBRARY = "chat_library"  # Sonnet 4 - conversational RAG
    SCREENING = "screening"  # Haiku 4.5 - quick decision
    CONCEPT_MAP = "concept_map"  # Sonnet 4 - deep analysis
    REFERENCE_CHECK = "reference_check"  # Haiku 4.5 - validation
    GOST_FORMATTER = "gost_formatter"  # Haiku 4.5 - rule application
    SUMMARY = "summary"  # Haiku 4.5 - quick summary


# --- Model Configuration ---

MODEL_ROUTING = {
    # High-complexity tasks → Sonnet 4
    LLMTask.RESEARCH_ANSWER: "claude-sonnet-4-20250514",
    LLMTask.CHAT_LIBRARY: "claude-sonnet-4-20250514",
    LLMTask.CONCEPT_MAP: "claude-sonnet-4-20250514",

    # Low-complexity tasks → Haiku 4.5
    LLMTask.DATA_EXTRACTION: "claude-haiku-4.5-20250219",
    LLMTask.SCREENING: "claude-haiku-4.5-20250219",
    LLMTask.REFERENCE_CHECK: "claude-haiku-4.5-20250219",
    LLMTask.GOST_FORMATTER: "claude-haiku-4.5-20250219",
    LLMTask.SUMMARY: "claude-haiku-4.5-20250219",
}

# Timeout per task (seconds)
TASK_TIMEOUTS = {
    LLMTask.RESEARCH_ANSWER: 120,  # 2 min for complex synthesis
    LLMTask.DATA_EXTRACTION: 60,
    LLMTask.CHAT_LIBRARY: 90,
    LLMTask.SCREENING: 30,
    LLMTask.CONCEPT_MAP: 120,
    LLMTask.REFERENCE_CHECK: 30,
    LLMTask.GOST_FORMATTER: 45,
    LLMTask.SUMMARY: 30,
}

# Max retries
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff (seconds)


# --- LLM Client ---

class LLMClient:
    """
    Claude AI client with task-based routing and retry logic.

    Features:
    - Automatic model selection based on task complexity
    - Retry logic for rate limits and transient errors
    - Timeout handling per task type
    - Response streaming support
    - Cost tracking
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM client.

        Args:
            api_key: Claude API key (defaults to settings.claude_api_key)
        """
        self.api_key = api_key or settings.claude_api_key
        if not self.api_key:
            raise ValueError("Claude API key is required")

        self.client = AsyncAnthropic(api_key=self.api_key)
        self.request_counts: Dict[str, int] = {}  # Track requests per task

    def get_model_for_task(self, task: LLMTask) -> str:
        """Get the appropriate model for a task."""
        return MODEL_ROUTING.get(task, "claude-sonnet-4-20250514")

    def get_timeout_for_task(self, task: LLMTask) -> int:
        """Get timeout for a task in seconds."""
        return TASK_TIMEOUTS.get(task, 60)

    async def generate(
        self,
        task: LLMTask,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate response using Claude AI with automatic retry.

        Args:
            task: Task type for model routing
            prompt: User prompt
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            metadata: Optional metadata for tracking

        Returns:
            Generated text response

        Raises:
            APIError: If all retries fail
        """
        model = self.get_model_for_task(task)
        timeout = self.get_timeout_for_task(task)

        # Track request
        task_name = task.value
        self.request_counts[task_name] = self.request_counts.get(task_name, 0) + 1

        for attempt in range(MAX_RETRIES):
            try:
                # Create message
                response = await asyncio.wait_for(
                    self.client.messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=system or "",
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        metadata=metadata or {}
                    ),
                    timeout=timeout
                )

                # Extract text from response
                text_content = ""
                for block in response.content:
                    if block.type == "text":
                        text_content += block.text

                return text_content

            except RateLimitError:
                # Rate limited - wait longer
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt] * 2
                    await asyncio.sleep(delay)
                    continue
                # Last attempt failed - re-raise to preserve stack trace
                raise

            except (APIConnectionError, asyncio.TimeoutError):
                # Transient error - retry with backoff
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    await asyncio.sleep(delay)
                    continue
                # Last attempt failed - re-raise to preserve stack trace
                raise

            except APIError:
                # Non-retryable error - re-raise immediately
                raise

    async def generate_stream(
        self,
        task: LLMTask,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 1.0
    ) -> AsyncIterator[str]:
        """
        Generate response with streaming.

        Note: This method does NOT implement automatic retries for transient errors
        (RateLimitError, APIConnectionError) since streaming cannot be resumed mid-stream.
        Callers should handle transient errors and re-request from the start if needed.

        Args:
            task: Task type for model routing
            prompt: User prompt
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Yields:
            Text chunks as they are generated

        Raises:
            asyncio.TimeoutError: If stream exceeds timeout for the task
            APIError: For API-related errors
        """
        model = self.get_model_for_task(task)
        timeout = self.get_timeout_for_task(task)

        # Track request
        task_name = task.value
        self.request_counts[task_name] = self.request_counts.get(task_name, 0) + 1

        start_time = time.monotonic()

        try:
            async with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system or "",
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                async for text in stream.text_stream:
                    # Check timeout before yielding each chunk
                    elapsed = time.monotonic() - start_time
                    if elapsed > timeout:
                        raise asyncio.TimeoutError(
                            f"Stream timeout after {elapsed:.1f}s (limit: {timeout}s) for task {task_name}"
                        )
                    yield text

        except asyncio.TimeoutError:
            # Re-raise timeout errors as-is
            raise
        except (RateLimitError, APIConnectionError) as e:
            # Preserve original exception type in cause chain for caller inspection
            raise APIError(f"Streaming failed for task {task_name}: {str(e)}") from e

    async def generate_structured(
        self,
        task: LLMTask,
        prompt: str,
        system: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response.

        Args:
            task: Task type for model routing
            prompt: User prompt
            system: Optional system prompt
            schema: JSON schema for validation

        Returns:
            Parsed JSON object
        """
        # Add JSON formatting instruction
        json_prompt = f"{prompt}\n\nRespond with valid JSON only."

        response_text = await self.generate(
            task=task,
            prompt=json_prompt,
            system=system,
            max_tokens=4000,
            temperature=0.0  # Lower temperature for structured output
        )

        # Parse JSON
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)

            # Validate against schema if provided
            if schema is not None:
                try:
                    from jsonschema import validate, ValidationError
                    validate(instance=result, schema=schema)
                except ValidationError as e:
                    raise ValueError(f"Response does not match schema: {e.message}")
                except ImportError:
                    # jsonschema not installed, skip validation
                    logger.warning(
                        f"Schema validation skipped - jsonschema library not available. "
                        f"Schema: {schema.get('title', schema.get('$id', 'untitled'))}"
                    )

            return result

        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {str(e)}")

    def get_request_stats(self) -> Dict[str, int]:
        """Get request counts per task type."""
        return self.request_counts.copy()


# --- Singleton client (lazy initialization) ---

_llm_client: Optional[LLMClient] = None
_llm_lock = asyncio.Lock()


async def get_llm_client() -> LLMClient:
    """
    Get or create the singleton LLM client instance.

    Lazy initialization ensures the client is only created when needed,
    avoiding import-time errors if API key is missing.

    Uses asyncio.Lock to prevent race conditions during concurrent initialization.

    Returns:
        LLMClient instance

    Raises:
        ValueError: If Claude API key is not configured
    """
    global _llm_client

    # Fast path: return if already initialized (no lock needed)
    if _llm_client is not None:
        return _llm_client

    # Slow path: acquire lock for initialization
    async with _llm_lock:
        # Double-check after acquiring lock (another coroutine may have initialized)
        if _llm_client is None:
            _llm_client = LLMClient()
        return _llm_client


# --- Helper functions ---

async def research_answer(query: str, context: str, max_tokens: int = 2000) -> str:
    """Generate research answer from papers."""
    system = """You are an academic research assistant. Analyze the provided papers
    and synthesize a comprehensive answer to the user's question. Cite sources with [1], [2], etc."""

    prompt = f"""Question: {query}

Context from papers:
{context}

Provide a detailed answer citing the relevant papers."""

    client = await get_llm_client()
    return await client.generate(
        task=LLMTask.RESEARCH_ANSWER,
        prompt=prompt,
        system=system,
        max_tokens=max_tokens
    )


async def extract_data(papers: List[Dict[str, Any]], schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract structured data from papers.

    Args:
        papers: List of paper dictionaries
        schema: JSON schema for extraction

    Returns:
        List of extracted data dictionaries (one per paper)

    Raises:
        ValueError: If response is not a list or doesn't contain expected array key
    """
    system = "Extract the requested information from each paper into structured JSON."

    # Serialize papers to proper JSON format
    papers_json = json.dumps(papers, ensure_ascii=False, indent=2)

    prompt = f"""Papers:
{papers_json}

Extract the following fields: {schema}

Return a JSON array with one object per paper."""

    client = await get_llm_client()
    result = await client.generate_structured(
        task=LLMTask.DATA_EXTRACTION,
        prompt=prompt,
        system=system,
        schema=schema
    )

    # Handle both list and dict responses
    if isinstance(result, list):
        # Direct array response
        return result
    elif isinstance(result, dict):
        # Try common keys that might contain the array
        for key in ["data", "papers", "results", "items", "extracted"]:
            if key in result and isinstance(result[key], list):
                return result[key]
        # If no known key found, wrap single dict in list
        return [result]
    else:
        raise ValueError(f"Unexpected response type: {type(result)}")


async def format_gost(citations: List[Dict[str, Any]], standard: str = "GOST") -> List[str]:
    """
    Format citations according to GOST standard.

    Args:
        citations: List of citation dictionaries
        standard: Citation standard (default: "GOST")

    Returns:
        List of formatted citation strings

    Raises:
        ValueError: If response format is invalid
    """
    system = f"Format bibliographic citations according to {standard} 7.0.100-2018 standard."

    # Serialize citations to proper JSON format
    citations_json = json.dumps(citations, ensure_ascii=False, indent=2)

    prompt = f"""Citations to format:
{citations_json}

Return formatted citations as a JSON array of strings."""

    client = await get_llm_client()
    result = await client.generate_structured(
        task=LLMTask.GOST_FORMATTER,
        prompt=prompt,
        system=system
    )

    # Handle both list and dict responses
    if isinstance(result, list):
        # Direct array response - validate entries are strings
        return [str(item) for item in result]
    elif isinstance(result, dict):
        # Dict response - extract citations array
        citations_list = result.get("citations")
        if citations_list is None:
            raise ValueError("Response dict missing 'citations' key")
        if not isinstance(citations_list, list):
            raise ValueError(f"Invalid type for citations: expected list, got {type(citations_list).__name__}")
        return [str(item) for item in citations_list]
    else:
        raise ValueError(f"Unexpected response type from GOST formatter: {type(result)}")
