"""Regression for #336: @cache keys must not include Request/Response object addresses."""

from unittest.mock import patch

import pytest
from fastapi import Request, Response
from pydantic import BaseModel

from app.core.cache_decorator import cache


class _Body(BaseModel):
    gene_ids: list[int]


class _DictCache:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], object] = {}

    async def get(self, key: str, namespace: str) -> object:
        return self.store.get((namespace, key))

    async def set(self, key: str, value: object, namespace: str, ttl: int | None) -> None:
        self.store[(namespace, key)] = value


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/x", "headers": []})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_distinct_requests_with_same_body_share_one_cache_key():
    backend = _DictCache()
    calls: list[list[int]] = []

    @cache(namespace="t", ttl=60)
    async def endpoint(request: Request, response: Response, body: _Body) -> dict:
        calls.append(body.gene_ids)
        return {"n": len(calls)}

    with patch("app.core.cache_decorator.get_cache_service", return_value=backend):
        first = await endpoint(_request(), Response(), _Body(gene_ids=[1, 2]))
        second = await endpoint(_request(), Response(), _Body(gene_ids=[1, 2]))
        await endpoint(_request(), Response(), _Body(gene_ids=[3]))

    assert first == second == {"n": 1}  # second call is a cache hit
    assert calls == [[1, 2], [3]]
    assert len(backend.store) == 2  # one key per distinct body
