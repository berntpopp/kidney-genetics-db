"""One retry loop that honours status codes and treats gnomAD's 400 rate limit as retryable (#364)."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core import retry_utils
from app.core.retry_utils import RetryableHTTPClient, RetryConfig, RetryStrategy
from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource

RATE_LIMITED = {
    "errors": [{"message": "Query rate limit exceeded. Please try again in a few minutes."}]
}


def _client(responses: list[httpx.Response], calls: list[httpx.Request]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return responses[min(len(calls), len(responses)) - 1]

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _gnomad(responses: list[httpx.Response], calls: list[httpx.Request]) -> GnomADAnnotationSource:
    src = GnomADAnnotationSource.__new__(GnomADAnnotationSource)
    src.requests_per_second = 1000.0
    src.http_client = RetryableHTTPClient(
        _client(responses, calls), RetryConfig(max_retries=3, initial_delay=0.0)
    )
    return src


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gnomad_400_rate_limit_is_retried_then_succeeds() -> None:
    calls: list[httpx.Request] = []
    ok = {"data": {"gene": {"symbol": "OTC"}}}
    src = _gnomad([httpx.Response(400, json=RATE_LIMITED), httpx.Response(200, json=ok)], calls)
    with patch("app.core.retry_utils.asyncio.sleep", AsyncMock()):
        assert await src._execute_query("query", {"gene_symbol": "OTC"}) == ok["data"]
    assert len(calls) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_one_503_costs_at_most_max_retries_plus_one_requests() -> None:
    calls: list[httpx.Request] = []
    src = _gnomad([httpx.Response(503)], calls)
    with (
        patch("app.core.retry_utils.asyncio.sleep", AsyncMock()),
        pytest.raises(httpx.HTTPStatusError),
    ):
        await src._execute_query("query", {"gene_symbol": "OTC"})
    assert len(calls) == 4  # max_retries=3 -> 4 requests, no nested decorator loop


@pytest.mark.unit
@pytest.mark.asyncio
async def test_plain_400_and_404_are_not_retried() -> None:
    for status in (400, 404):
        calls: list[httpx.Request] = []
        client = RetryableHTTPClient(_client([httpx.Response(status)], calls), RetryConfig())
        with pytest.raises(httpx.HTTPStatusError):
            await client.get("https://example.org")
        assert len(calls) == 1

    strategy_calls = 0

    async def not_found() -> None:
        nonlocal strategy_calls
        strategy_calls += 1
        request = httpx.Request("GET", "https://example.org")
        raise httpx.HTTPStatusError("404", request=request, response=httpx.Response(404))

    with pytest.raises(httpx.HTTPStatusError):
        await RetryStrategy(max_retries=3, initial_delay=0.0).execute_async(not_found)
    assert strategy_calls == 1


@pytest.mark.unit
def test_retry_after_is_capped_at_max_delay() -> None:
    request = httpx.Request("GET", "https://example.org")
    response = httpx.Response(429, headers={"Retry-After": "3600"}, request=request)
    error = httpx.HTTPStatusError("429", request=request, response=response)
    assert retry_utils._retry_delay(error, RetryConfig(max_delay=60.0), 0) == 60.0
