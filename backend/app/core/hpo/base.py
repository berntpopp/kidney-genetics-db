"""
Base HPO API client with caching and resilience features.
"""

import hashlib
import json
import logging
from typing import Any

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.retry_utils import RetryConfig, retry_with_backoff

logger = logging.getLogger(__name__)


class HPOAPIBase:
    """Base class for HPO API interactions with caching and resilience."""

    BASE_URL = "https://ontology.jax.org/api"
    HPO_BROWSER_URL = "https://hpo.jax.org"

    def __init__(
        self, cache_service: CacheService | None = None, http_client: CachedHttpClient | None = None
    ):
        """
        Initialize the HPO API base client.

        Args:
            cache_service: Cache service instance
            http_client: HTTP client with caching
        """
        self.cache_service = cache_service
        self.http_client = http_client
        self.namespace = "hpo"

        # Default TTLs for different data types
        self.ttl_stable = 86400 * 30  # 30 days for stable ontology data
        self.ttl_annotations = 86400 * 7  # 7 days for annotations
        self.ttl_search = 86400  # 1 day for search results

    async def _get(
        self,
        endpoint: str,
        params: dict | None = None,
        cache_key: str | None = None,
        ttl: int | None = None,
        base_url: str | None = None,
    ) -> Any:
        """
        Generic GET request with intelligent caching.

        Args:
            endpoint: API endpoint
            params: Query parameters
            cache_key: Custom cache key for database fallback
            ttl: Cache TTL in seconds
            base_url: Override base URL (for browser API)

        Returns:
            JSON response data
        """
        url = f"{base_url or self.BASE_URL}/{endpoint}"

        # Generate cache key if not provided
        if not cache_key:
            cache_key = self._generate_cache_key(endpoint, params)

        # If we have an HTTP client with caching, use it
        if self.http_client:
            # Configure retry with exponential backoff for rate limiting
            retry_config = RetryConfig(
                max_retries=5,
                initial_delay=1.0,
                max_delay=32.0,
                exponential_base=2.0,
                jitter=True,
                retry_on_status_codes=(429, 500, 502, 503, 504),
            )

            @retry_with_backoff(config=retry_config)
            async def fetch_with_retry():
                response = await self.http_client.get(
                    url,
                    params=params,
                    namespace=self.namespace,
                    cache_key=cache_key,
                    fallback_ttl=ttl or self.ttl_annotations,
                )

                # Handle both Response objects and dict responses
                if hasattr(response, "json"):
                    return response.json()
                return response

            try:
                return await fetch_with_retry()
            except Exception as e:
                logger.error(f"Error fetching {url} after retries: {e}")

                # Try cache fallback if available
                if self.cache_service:
                    cached = await self.cache_service.get(cache_key, self.namespace)
                    if cached:
                        logger.info(f"Using cached data for {endpoint}")
                        return cached

                raise

        # Fallback to basic HTTP request if no cached client
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            # Cache the response if cache service is available
            if self.cache_service and ttl:
                await self.cache_service.set(cache_key, data, self.namespace, ttl)

            return data

    def _generate_cache_key(self, endpoint: str, params: dict | None = None) -> str:
        """
        Generate consistent cache keys.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            SHA256 hash of the key components
        """
        key_parts = [endpoint]
        if params:
            # Sort params for consistent keys
            key_parts.append(json.dumps(params, sort_keys=True))

        key_string = ":".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    async def test_connection(self) -> bool:
        """
        Test connection to HPO API.

        Returns:
            True if API is accessible
        """
        try:
            # Try a simple endpoint
            await self._get("hp/terms/HP:0000001", ttl=self.ttl_stable)
            return True
        except Exception as e:
            logger.error(f"HPO API connection test failed: {e}")
            return False
