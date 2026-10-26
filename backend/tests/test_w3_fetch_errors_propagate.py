"""PanelApp/ClinGen fetch errors must propagate, not become a cached partial result (#366)."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.retry_utils import RetryStrategy
from app.pipeline.sources.unified.clingen import ClinGenUnifiedSource
from app.pipeline.sources.unified.panelapp import PanelAppUnifiedSource


def _response(status: int, payload: dict) -> httpx.Response:
    return httpx.Response(status, json=payload, request=httpx.Request("GET", "https://x"))


def _cache() -> MagicMock:
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.mark.unit
@pytest.mark.asyncio
async def test_panelapp_region_timeout_raises_and_caches_nothing_partial():
    async def get(url, **kwargs):
        if "aus" in url:
            raise httpx.ConnectTimeout("Australia timed out")
        if url.endswith("/panels/"):
            return _response(200, {"results": [{"id": 1, "name": "Renal panel"}]})
        return _response(200, {"id": 1, "name": "Renal panel", "genes": []})

    cache = _cache()
    source = PanelAppUnifiedSource(
        cache_service=cache,
        http_client=MagicMock(get=AsyncMock(side_effect=get)),
        retry_strategy=RetryStrategy(max_retries=0),
    )

    with pytest.raises(httpx.ConnectTimeout):
        await source.fetch_raw_data()

    cached_keys = [c.args[0] for c in cache.set.call_args_list]
    assert not any("Australia" in key for key in cached_keys)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_panelapp_panel_detail_error_raises():
    async def get(url, **kwargs):
        if url.endswith("/panels/"):
            return _response(200, {"results": [{"id": 7, "name": "Renal panel"}]})
        return _response(503, {})

    source = PanelAppUnifiedSource(
        cache_service=_cache(),
        http_client=MagicMock(get=AsyncMock(side_effect=get)),
        retry_strategy=RetryStrategy(max_retries=0),
        regions=["UK"],
    )

    with pytest.raises(httpx.HTTPStatusError):
        await source.fetch_raw_data()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clingen_csv_error_raises():
    source = ClinGenUnifiedSource(
        cache_service=_cache(),
        http_client=MagicMock(get=AsyncMock(return_value=_response(503, {}))),
        retry_strategy=RetryStrategy(max_retries=0),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await source.fetch_raw_data()
