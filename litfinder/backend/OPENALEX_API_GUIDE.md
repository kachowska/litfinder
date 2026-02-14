# OpenAlex Integration Guide

## Overview

LitFinder integrates with the OpenAlex API to provide comprehensive academic article search. This guide covers the enhanced features, filtering options, and pagination strategies.

## Features

### 1. Advanced Filtering

#### Year Range
```python
# Filter by publication year range
await search_works(
    query="machine learning",
    year_from=2020,
    year_to=2024
)
```

#### Citation Count
```python
# Filter by citation count (min/max)
await search_works(
    query="neural networks",
    cited_by_count_min=100,      # At least 100 citations
    cited_by_count_max=1000      # At most 1000 citations
)
```

#### Open Access
```python
# Filter for open access articles only
await search_works(
    query="climate change",
    is_oa=True
)
```

#### Publication Type
```python
# Filter by publication type
await search_works(
    query="artificial intelligence",
    publication_type="article"  # article, review, book-chapter, etc.
)
```

#### Concepts (Topics)
```python
# Filter by OpenAlex concept IDs
await search_works(
    query="deep learning",
    concepts=["C41008148", "C154945302"]  # Computer Science, Machine Learning
)
```

### 2. Pagination Strategies

#### Page-Based Pagination (Simple)
Best for: First 10,000 results (50 pages × 200 per page)

```python
# Page 1
result = await search_works(
    query="python",
    per_page=20,
    page=1
)

# Page 2
result = await search_works(
    query="python",
    per_page=20,
    page=2
)
```

**Limitations:**
- Maximum 10,000 results (50 pages @ 200 per page)
- Page 51+ returns empty results

#### Cursor-Based Pagination (Advanced)
Best for: >10,000 results, deep pagination

```python
# First page - use cursor="*" to start
result = await search_works(
    query="python",
    per_page=20,
    cursor="*"
)

# Get next_cursor from response
next_cursor = result.get("next_cursor")

# Fetch next page using cursor
result2 = await search_works(
    query="python",
    per_page=20,
    cursor=next_cursor
)
```

**Advantages:**
- No 10,000 result limit
- Consistent results (no duplicates/skips)
- Better for batch processing

**Note:** Cursor strings are opaque and query-specific. Cannot reuse cursors across different queries.

### 3. Combined Filtering

```python
# Combine multiple filters for precise results
result = await search_works(
    query="deep learning",
    year_from=2020,
    year_to=2024,
    cited_by_count_min=50,
    is_oa=True,
    publication_type="article",
    per_page=20
)
```

## API Endpoint Usage

### Search Request

```json
POST /api/v1/search
{
  "query": "machine learning",
  "limit": 20,
  "cursor": null,
  "filters": {
    "year_from": 2020,
    "year_to": 2024,
    "cited_by_count_min": 100,
    "is_oa": true,
    "publication_type": "article",
    "source": ["openalex"]
  }
}
```

### Search Response

```json
{
  "total": 125000,
  "results": [...],
  "next_cursor": "IlsxMTc0Ljc0NjgsICctSW5maW5pdHknL...",
  "filters_applied": {...},
  "execution_time_ms": 450
}
```

## Error Handling

The OpenAlex client includes robust error handling:

### Retry Logic
- **Rate limiting (429):** Automatically waits for `Retry-After` duration
- **Timeouts:** Exponential backoff (2^attempt seconds)
- **Server errors (500+):** Exponential backoff with 3 retries
- **Client errors (400-499):** Fail immediately (no retry)

### Logging
All errors are logged with context:
```python
logger.error(f"Failed to fetch work {work_id}: {e}", exc_info=True)
```

## Performance Tips

### 1. Use Appropriate Pagination
- **<10k results:** Page-based pagination (simpler)
- **>10k results:** Cursor-based pagination (required)
- **Batch processing:** Always use cursor pagination

### 2. Filter Early
Apply filters to reduce result set:
```python
# Good - filtered to ~1000 results
await search_works(
    query="AI",
    year_from=2023,
    cited_by_count_min=50,
    is_oa=True
)

# Bad - 2M+ results, slow
await search_works(query="AI")
```

### 3. Limit Result Size
Use smaller `per_page` for faster responses:
```python
# Fast - 20 results
await search_works(query="AI", per_page=20)

# Slow - 200 results
await search_works(query="AI", per_page=200)
```

### 4. Cache Results
Results are automatically cached (skipped for cursor pagination)

## OpenAlex Rate Limits

- **Polite Pool (with email):** 100 requests/minute
- **Premium (with API key):** Higher limits (contact OpenAlex)

LitFinder uses the polite pool by default. Configure API key in `.env` for premium access:
```bash
OPENALEX_API_KEY=your-api-key-here
OPENALEX_EMAIL=your-email@example.com
```

## Field Selection

OpenAlex returns only selected fields to reduce response size:
- id, doi, title, display_name
- publication_year, authorships
- abstract_inverted_index
- cited_by_count, open_access
- concepts, biblio, primary_location

Full field documentation: https://docs.openalex.org/api-entities/works

## Examples

### Highly-Cited Recent Papers
```python
result = await search_works(
    query="climate change",
    year_from=2020,
    cited_by_count_min=100,
    is_oa=True,
    publication_type="article",
    per_page=20
)
```

### Deep Pagination for Export
```python
all_results = []
cursor = "*"

while cursor:
    result = await search_works(
        query="machine learning",
        cursor=cursor,
        per_page=200
    )

    all_results.extend(result["results"])
    cursor = result.get("next_cursor")

    # Safety: limit to 10,000 results
    if len(all_results) >= 10000:
        break
```

### Open Access Reviews Only
```python
result = await search_works(
    query="systematic review",
    publication_type="review",
    is_oa=True,
    per_page=50
)
```

## Troubleshooting

### Issue: Empty results on page 51+
**Solution:** Switch to cursor pagination
```python
# Instead of page=51
result = await search_works(query="AI", page=51)  # Empty

# Use cursor
result = await search_works(query="AI", cursor="*")  # Works
```

### Issue: Slow queries
**Solution:** Add filters to reduce result set
```python
# Add year range, citation threshold, or publication type
result = await search_works(
    query="AI",
    year_from=2023,
    cited_by_count_min=10
)
```

### Issue: Rate limiting errors
**Solution:** System automatically retries with backoff. For sustained high volume, get API key.

## References

- [OpenAlex API Documentation](https://docs.openalex.org)
- [OpenAlex Filters Reference](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/filter-entity-lists)
- [OpenAlex Pagination Guide](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/paging)
