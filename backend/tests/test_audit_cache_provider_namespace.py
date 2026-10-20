"""#297: provider payloads must live in the provider namespace that operators clear."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.cache_service import CacheService
from app.pipeline.sources.unified.base import UnifiedDataSource


class _Provider(UnifiedDataSource):
    source_name = "AuditProvider"  # type: ignore[assignment]
    namespace = "auditprovider"  # type: ignore[assignment]

    def _get_default_ttl(self) -> int:
        return 3600

    async def fetch_raw_data(self, tracker=None, mode: str = "smart") -> Any:
        return None

    async def process_data(self, raw_data: Any) -> dict[str, Any]:
        return {}

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        return True


@pytest.fixture
def provider():
    cache = CacheService(db_session=None)  # memory layer is enough to show namespace placement
    return _Provider(cache_service=cache, http_client=MagicMock()), cache


@pytest.mark.asyncio
async def test_single_fetch_refetches_after_provider_namespace_clear(provider):
    source, cache = provider
    upstream = AsyncMock(return_value={"payload": 1})

    await source.fetch_with_cache("all", upstream)
    await source.fetch_with_cache("all", upstream)
    assert upstream.await_count == 1  # served from cache

    assert await cache.clear_namespace("auditprovider") >= 1
    await source.fetch_with_cache("all", upstream)
    assert upstream.await_count == 2


@pytest.mark.asyncio
async def test_batch_fetch_refetches_after_provider_namespace_clear(provider):
    source, cache = provider
    upstream = AsyncMock(side_effect=lambda batch: {item: {"v": item} for item in batch})

    await source.fetch_batch_with_cache(["A", "B"], str, upstream)
    await source.fetch_batch_with_cache(["A", "B"], str, upstream)
    assert upstream.await_count == 1

    assert await cache.clear_namespace("auditprovider") >= 2
    assert await source.fetch_batch_with_cache(["A", "B"], str, upstream) == {
        "A": {"v": "A"},
        "B": {"v": "B"},
    }
    assert upstream.await_count == 2
