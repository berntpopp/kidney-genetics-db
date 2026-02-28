# PubTator Pipeline Performance Refactor - KISS Implementation

## Problem

PubTator pipeline violates API rate limit (3 req/s), causing server throttling and disconnections. Additional issues: loading 50k+ PMIDs into memory, large uncommitted chunks risking data loss.

## Solution

Simple rate limiting and database-based duplicate checking using existing infrastructure.

## Implementation

### 1. Add Rate Limiting (Reuse Existing Patterns)

```python
# Extend existing retry_utils.py with rate limiting
# app/core/retry_utils.py - ADD to existing file

class SimpleRateLimiter:
    """Simple rate limiter - no bursts, just consistent rate."""

    def __init__(self, requests_per_second: float = 3.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request = 0

    async def wait(self):
        """Wait if needed to maintain rate limit."""
        now = time.monotonic()
        elapsed = now - self.last_request
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_request = time.monotonic()
```

### 2. Update PubTator to Use Rate Limiter

```python
# pubtator.py - Minimal changes to existing code

class PubTatorUnifiedSource(UnifiedDataSource):
    def __init__(self, ...):
        super().__init__(...)

        # Add rate limiter (reuse from retry_utils)
        from app.core.retry_utils import SimpleRateLimiter
        self.rate_limiter = SimpleRateLimiter(
            requests_per_second=get_source_parameter("PubTator", "requests_per_second", 3.0)
        )

        # Reduce chunk size for more frequent saves
        self.chunk_size = get_source_parameter("PubTator", "chunk_size", 300)

    async def _fetch_page(self, page: int, query: str) -> dict | None:
        """Add rate limiting to existing fetch."""
        # Rate limit BEFORE request
        await self.rate_limiter.wait()

        # Rest of existing code unchanged...
        params = {"text": query, "page": page, "sort": self.sort_order, "filters": "{}"}
        response = await self.http_client.get(...)
```

### 3. Database-Based Duplicate Checking (Replace Memory Loading)

```python
# Replace _get_existing_pmids_from_db() with database checks

async def _check_pmids_exist_batch(self, pmids: list[str]) -> set[str]:
    """Check which PMIDs already exist using database query."""
    if not pmids:
        return set()

    from sqlalchemy import text

    # Use PostgreSQL's efficient JSONB containment
    result = self.db_session.execute(
        text("""
            SELECT DISTINCT pmid
            FROM gene_evidence,
                 LATERAL jsonb_array_elements_text(evidence_data->'pmids') AS pmid
            WHERE source_name = 'PubTator'
            AND pmid = ANY(:pmid_list)
        """),
        {"pmid_list": pmids}
    ).fetchall()

    return {row[0] for row in result}

# In _stream_process_pubtator, replace memory-based checking:
# OLD: if mode == "smart" and pmid in existing_pmids:
# NEW: Check in batches every N articles

if mode == "smart" and len(article_buffer) >= 50:
    # Check batch of PMIDs
    pmids_to_check = [a.get("pmid") for a in article_buffer]
    existing = await self._check_pmids_exist_batch(pmids_to_check)

    # Filter out existing
    article_buffer = [a for a in article_buffer if str(a.get("pmid")) not in existing]
```

### 4. Configuration Update (datasource_config.py)

```python
"PubTator": {
    # ... existing config ...

    # Add rate limiting
    "requests_per_second": 3.0,  # PubTator3 official limit

    # Optimize chunking
    "chunk_size": 300,  # Reduced from 1000
    "transaction_size": 1000,  # Reduced from 5000
}
```

### 5. Reuse Existing Systems

- **CachedHttpClient**: Already handles HTTP caching, circuit breakers ✅
- **RetryConfig**: Already handles exponential backoff ✅
- **UnifiedLogger**: Already handles structured logging ✅
- **CacheService**: Already handles multi-layer caching ✅
- **ProgressTracker**: Already handles WebSocket updates ✅

## Testing

```python
# Simple test for rate limiting
async def test_rate_limiting():
    """Verify 3 req/s rate limit is enforced."""
    source = PubTatorUnifiedSource(db_session=db)

    start = time.monotonic()
    for i in range(10):
        await source._fetch_page(i, "test query")
    elapsed = time.monotonic() - start

    assert elapsed >= 3.0, f"10 requests should take 3+ seconds, took {elapsed}"

# Test database duplicate checking
async def test_database_dedup():
    """Verify database-based PMID checking works."""
    source = PubTatorUnifiedSource(db_session=db)

    # Insert test PMID
    test_pmid = "12345"
    # ... insert test data ...

    # Check it's detected
    existing = await source._check_pmids_exist_batch([test_pmid, "99999"])
    assert test_pmid in existing
    assert "99999" not in existing
```

## Benefits

- **Simple**: ~50 lines of code changes total
- **Reuses**: All existing infrastructure (no new systems)
- **Efficient**: Database does heavy lifting for deduplication
- **Reliable**: Respects API limits, prevents disconnections
- **Memory**: O(1) instead of O(n) memory usage

## No New Systems Required

Everything uses existing infrastructure:
- `retry_utils.py` - Add rate limiter here
- `CachedHttpClient` - Already has caching
- `UnifiedDataSource` - Already has batch processing
- PostgreSQL JSONB - Already indexed for fast queries