"""Tests for per-domain rate limiter registry."""

import asyncio
import time

import pytest

from app.core.domain_rate_limiter import DomainLimiter, DomainRateLimiterRegistry


class TestDomainRateLimiterRegistry:
    """Test per-domain rate limiting."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rate_limits_applied_per_domain(self):
        """Requests to the same domain are rate-limited."""
        registry = DomainRateLimiterRegistry(
            domain_configs={
                "api.example.com": {"max_rate": 10.0, "max_concurrent": 2},
            },
            default_max_rate=5.0,
            default_max_concurrent=3,
        )

        limiter = registry.get("api.example.com")
        assert limiter is not None
        assert limiter.max_rate == 10.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_domain_gets_default(self):
        """Unknown domains get default rate limiter."""
        registry = DomainRateLimiterRegistry(
            domain_configs={},
            default_max_rate=5.0,
            default_max_concurrent=3,
        )

        limiter = registry.get("unknown.example.com")
        assert limiter.max_rate == 5.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_same_domain_returns_same_limiter(self):
        """Same domain always returns the same limiter instance."""
        registry = DomainRateLimiterRegistry(
            domain_configs={},
            default_max_rate=5.0,
            default_max_concurrent=3,
        )

        limiter1 = registry.get("api.example.com")
        limiter2 = registry.get("api.example.com")
        assert limiter1 is limiter2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_acquire_respects_rate_limit(self):
        """Acquire should enforce rate limiting."""
        registry = DomainRateLimiterRegistry(
            domain_configs={
                "slow.api.com": {"max_rate": 5.0, "max_concurrent": 1},
            },
        )

        limiter = registry.get("slow.api.com")

        start = time.monotonic()
        async with limiter.acquire():
            pass
        first_duration = time.monotonic() - start
        assert first_duration < 0.5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_concurrency_semaphore(self):
        """Max concurrent requests should be enforced."""
        registry = DomainRateLimiterRegistry(
            domain_configs={
                "api.example.com": {"max_rate": 100.0, "max_concurrent": 2},
            },
        )

        limiter = registry.get("api.example.com")
        active = 0
        max_active = 0

        async def worker():
            nonlocal active, max_active
            async with limiter.acquire():
                active += 1
                max_active = max(max_active, active)
                await asyncio.sleep(0.05)
                active -= 1

        await asyncio.gather(*[worker() for _ in range(5)])
        assert max_active <= 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pause_domain(self):
        """pause() should set paused state."""
        registry = DomainRateLimiterRegistry(
            domain_configs={
                "api.example.com": {"max_rate": 100.0, "max_concurrent": 5},
            },
        )

        limiter = registry.get("api.example.com")
        limiter.pause(seconds=0.5)
        assert limiter.is_paused

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_for_url(self):
        """get_for_url extracts domain and returns limiter."""
        registry = DomainRateLimiterRegistry(
            domain_configs={
                "rest.ensembl.org": {"max_rate": 15.0, "max_concurrent": 5},
            },
        )

        limiter = registry.get_for_url("https://rest.ensembl.org/lookup/symbol/homo_sapiens/PKD1")
        assert limiter.max_rate == 15.0

    @pytest.mark.unit
    def test_domain_limiter_init(self):
        """DomainLimiter stores max_rate correctly."""
        limiter = DomainLimiter(max_rate=10.0, max_concurrent=5)
        assert limiter.max_rate == 10.0
        assert not limiter.is_paused
