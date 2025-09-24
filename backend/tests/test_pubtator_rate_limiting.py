"""
Test suite for PubTator rate limiting implementation.

Tests that the PubTator source respects API rate limits (3 req/s)
and uses database-based PMID checking instead of loading all into memory.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource


@pytest.mark.asyncio
async def test_rate_limiter_enforces_3_requests_per_second():
    """Verify that rate limiter enforces 3 req/s limit."""
    from app.core.retry_utils import SimpleRateLimiter

    limiter = SimpleRateLimiter(requests_per_second=3.0)

    # Make 10 requests and measure time
    start = time.monotonic()
    for _ in range(10):
        await limiter.wait()
    elapsed = time.monotonic() - start

    # 10 requests at 3 req/s should take at least 3 seconds
    # (first request is immediate, then 9 more at 1/3 second intervals = 3 seconds)
    assert elapsed >= 3.0, f"Rate limiter should enforce 3 req/s, but took only {elapsed:.2f}s"
    assert elapsed < 4.0, f"Rate limiter too conservative, took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_pubtator_uses_rate_limiter():
    """Test that PubTator source uses rate limiter before API calls."""
    # Mock dependencies
    mock_cache = MagicMock(spec=CacheService)
    mock_http = AsyncMock(spec=CachedHttpClient)
    mock_db = MagicMock(spec=Session)

    # Create PubTator source
    source = PubTatorUnifiedSource(
        cache_service=mock_cache,
        http_client=mock_http,
        db_session=mock_db
    )

    # Verify rate limiter was initialized
    assert hasattr(source, 'rate_limiter')
    assert source.rate_limiter.min_interval == 1.0 / 3.0  # 3 req/s

    # Mock the HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [], "total_pages": 1}
    mock_http.get.return_value = mock_response

    # Test that _fetch_page uses rate limiter
    with patch.object(source.rate_limiter, 'wait', new=AsyncMock()) as mock_wait:
        await source._fetch_page(1, "test query")

        # Verify rate limiter was called before HTTP request
        mock_wait.assert_called_once()
        mock_http.get.assert_called_once()


@pytest.mark.asyncio
async def test_database_based_pmid_checking():
    """Test that PMID checking uses database queries, not memory."""
    # Mock dependencies
    mock_db = MagicMock(spec=Session)
    mock_cache = MagicMock(spec=CacheService)
    mock_http = AsyncMock(spec=CachedHttpClient)

    source = PubTatorUnifiedSource(
        cache_service=mock_cache,
        http_client=mock_http,
        db_session=mock_db
    )

    # Test PMIDs
    test_pmids = ["12345", "67890", "11111"]

    # Mock database response - say first two exist
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("12345",), ("67890",)]
    mock_db.execute.return_value = mock_result

    # Call the batch check method
    existing = await source._check_pmids_exist_batch(test_pmids)

    # Verify database was queried
    mock_db.execute.assert_called_once()

    # Verify correct PMIDs returned
    assert existing == {"12345", "67890"}

    # Verify SQL query contains proper JSONB operations
    executed_query = str(mock_db.execute.call_args[0][0])
    assert "jsonb_array_elements_text" in executed_query
    assert "evidence_data->'pmids'" in executed_query


def test_chunk_size_configuration():
    """Test that chunk size is properly configured from datasource_config."""
    mock_db = MagicMock(spec=Session)
    mock_cache = MagicMock(spec=CacheService)
    mock_http = MagicMock(spec=CachedHttpClient)

    source = PubTatorUnifiedSource(
        cache_service=mock_cache,
        http_client=mock_http,
        db_session=mock_db
    )

    # Verify chunk sizes are reduced as per configuration
    assert source.chunk_size == 300  # Reduced from 1000
    assert source.transaction_size == 1000  # Reduced from 5000


@pytest.mark.asyncio
async def test_smart_mode_does_not_load_all_pmids():
    """Verify smart mode doesn't load all PMIDs into memory."""
    mock_db = MagicMock(spec=Session)
    mock_cache = MagicMock(spec=CacheService)
    mock_http = AsyncMock(spec=CachedHttpClient)

    source = PubTatorUnifiedSource(
        cache_service=mock_cache,
        http_client=mock_http,
        db_session=mock_db
    )

    # The old _get_existing_pmids_from_db method should not exist
    # or should not be called in the new implementation
    assert not hasattr(source, '_get_existing_pmids_from_db') or \
           '_get_existing_pmids_from_db' not in [m for m in dir(source) if not m.startswith('_check')]

    # The new method should exist
    assert hasattr(source, '_check_pmids_exist_batch')


if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_rate_limiter_enforces_3_requests_per_second())
    asyncio.run(test_pubtator_uses_rate_limiter())
    asyncio.run(test_database_based_pmid_checking())
    test_chunk_size_configuration()
    asyncio.run(test_smart_mode_does_not_load_all_pmids())
    print("All tests passed!")
