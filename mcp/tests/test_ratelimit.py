"""Tests for the layered rate limiter and its optional Redis backend."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from fastmcp import Client

from kidney_genetics_mcp.config import Settings, get_settings
from kidney_genetics_mcp.server import RateLimitMiddleware, build_app
from kidney_genetics_mcp.server_ratelimit import RateLimiter, get_limiter


class _FailingRedis:
    """Async Redis stand-in whose every operation fails."""

    async def incr(self, key: str) -> int:
        raise ConnectionError("redis down")

    async def expire(self, key: str, seconds: int) -> bool:
        raise ConnectionError("redis down")


class _GatedRedis:
    """Async Redis stand-in that blocks INCR until the test releases it."""

    def __init__(self) -> None:
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.closed = False

    async def incr(self, key: str) -> int:
        self.entered.set()
        await self.release.wait()
        return 2

    async def expire(self, key: str, seconds: int) -> bool:
        return True

    async def aclose(self) -> None:
        self.closed = True


def _frozen_limiter(**kwargs: Any) -> RateLimiter:
    return RateLimiter(
        global_rps=10.0, tool_capacity=1000.0, clock=lambda: 0.0, **kwargs
    )


async def test_failing_redis_falls_back_to_local_global_bucket() -> None:
    local = _frozen_limiter()
    local_allowed = sum([await local.allow("kgdb_get_gene") for _ in range(30)])

    failing = _frozen_limiter()
    failing._redis = _FailingRedis()
    failing_allowed = sum([await failing.allow("kgdb_get_gene") for _ in range(30)])

    assert local_allowed == 20
    assert failing_allowed == local_allowed


async def test_slow_redis_does_not_block_the_event_loop() -> None:
    limiter = _frozen_limiter()
    redis = _GatedRedis()
    limiter._redis = redis
    middleware = RateLimitMiddleware(limiter)
    context: Any = SimpleNamespace(message=SimpleNamespace(name="kgdb_get_gene"))

    async def call_next(_context: Any) -> str:
        return "ok"

    call = asyncio.create_task(middleware.on_call_tool(context, call_next))
    await asyncio.wait_for(redis.entered.wait(), timeout=1)
    # Other work on the loop progresses while the Redis call is in flight.
    heartbeat = await asyncio.wait_for(asyncio.sleep(0, result="beat"), timeout=1)
    assert heartbeat == "beat"
    assert not call.done()

    redis.release.set()
    assert await asyncio.wait_for(call, timeout=1) == "ok"


async def test_server_lifespan_closes_redis_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KGDB_MCP_API_BASE_URL", "http://test-backend:8000")
    monkeypatch.setenv("KGDB_MCP_REDIS_URL", "redis://127.0.0.1:1/0")
    get_settings.cache_clear()
    settings: Settings = get_settings()
    get_settings.cache_clear()

    mcp = build_app(settings)
    limiter = get_limiter()
    assert limiter is not None and limiter._redis is not None
    await limiter._redis.aclose()  # release the real lazy client before swapping
    redis = _GatedRedis()
    limiter._redis = redis

    async with Client(mcp):
        assert not redis.closed
    assert redis.closed
