"""
Per-domain rate limiter for outgoing HTTP requests.

Uses aiolimiter (leaky bucket) + asyncio.Semaphore for per-domain
rate limiting and concurrency control. Designed for annotation
pipeline sources that hit multiple external APIs.
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

from aiolimiter import AsyncLimiter

from app.core.logging import get_logger

logger = get_logger(__name__)


class DomainLimiter:
    """Rate limiter + concurrency control for a single domain."""

    def __init__(self, max_rate: float = 5.0, max_concurrent: int = 3):
        self.max_rate = max_rate
        self._rate_limiter = AsyncLimiter(max_rate=max_rate, time_period=1.0)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._paused_until: float = 0.0

    @property
    def is_paused(self) -> bool:
        return time.monotonic() < self._paused_until

    def pause(self, seconds: float) -> None:
        """Pause all requests to this domain (e.g., on 429 Retry-After)."""
        self._paused_until = time.monotonic() + seconds
        logger.sync_info(
            "Domain paused",
            pause_seconds=seconds,
        )

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[None, None]:
        """Acquire rate limit slot + concurrency semaphore."""
        if self.is_paused:
            wait_time = self._paused_until - time.monotonic()
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        async with self._semaphore:
            await self._rate_limiter.acquire()
            yield


class DomainRateLimiterRegistry:
    """
    Registry of per-domain rate limiters.

    Usage:
        registry = DomainRateLimiterRegistry(
            domain_configs={
                "rest.ensembl.org": {"max_rate": 15.0, "max_concurrent": 5},
            },
        )
        limiter = registry.get("rest.ensembl.org")
        async with limiter.acquire():
            response = await client.get(url)
    """

    def __init__(
        self,
        domain_configs: dict[str, dict[str, Any]] | None = None,
        default_max_rate: float = 5.0,
        default_max_concurrent: int = 3,
    ):
        self._configs = domain_configs or {}
        self._default_max_rate = default_max_rate
        self._default_max_concurrent = default_max_concurrent
        self._limiters: dict[str, DomainLimiter] = {}

    def get(self, domain: str) -> DomainLimiter:
        """Get or create a rate limiter for a domain."""
        if domain not in self._limiters:
            config = self._configs.get(domain, {})
            self._limiters[domain] = DomainLimiter(
                max_rate=config.get("max_rate", self._default_max_rate),
                max_concurrent=config.get("max_concurrent", self._default_max_concurrent),
            )
        return self._limiters[domain]

    def get_for_url(self, url: str) -> DomainLimiter:
        """Extract domain from URL and return its limiter."""
        domain = urlparse(url).hostname or "unknown"
        return self.get(domain)

    def pause_domain(self, domain: str, seconds: float) -> None:
        """Pause all requests to a domain (call on 429 response)."""
        self.get(domain).pause(seconds)


# Default domain rate limits for annotation sources
DEFAULT_DOMAIN_CONFIGS: dict[str, dict[str, Any]] = {
    "ontology.jax.org": {"max_rate": 2.0, "max_concurrent": 2},
    "www.ncbi.nlm.nih.gov": {"max_rate": 3.0, "max_concurrent": 3},
    "eutils.ncbi.nlm.nih.gov": {"max_rate": 10.0, "max_concurrent": 3},
    "rest.ensembl.org": {"max_rate": 15.0, "max_concurrent": 5},
    "rest.uniprot.org": {"max_rate": 5.0, "max_concurrent": 3},
    "www.genenames.org": {"max_rate": 5.0, "max_concurrent": 3},
    "gnomad.broadinstitute.org": {"max_rate": 5.0, "max_concurrent": 3},
    "search.thegencc.org": {"max_rate": 10.0, "max_concurrent": 5},
    "panelapp.genomicsengland.co.uk": {"max_rate": 5.0, "max_concurrent": 3},
    "clinicalgenome.org": {"max_rate": 5.0, "max_concurrent": 3},
    "string-db.org": {"max_rate": 5.0, "max_concurrent": 3},
}

# Singleton registry — shared across all annotation sources
_registry: DomainRateLimiterRegistry | None = None


def get_domain_rate_limiter_registry() -> DomainRateLimiterRegistry:
    """Get the shared domain rate limiter registry."""
    global _registry
    if _registry is None:
        _registry = DomainRateLimiterRegistry(
            domain_configs=DEFAULT_DOMAIN_CONFIGS,
            default_max_rate=5.0,
            default_max_concurrent=3,
        )
    return _registry
