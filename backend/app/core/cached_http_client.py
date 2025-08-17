"""
HTTP client wrapper with intelligent caching support.

This module provides an HTTP client that combines:
- Hishel for RFC 9111 compliant HTTP caching
- Custom cache policies per data source
- Fallback to database cache for offline scenarios
- Intelligent retry logic and error handling
"""

import asyncio
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import hishel
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService, get_cache_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class CachedHttpClient:
    """
    HTTP client with intelligent caching capabilities.

    Features:
    - RFC 9111 compliant HTTP caching via Hishel
    - Custom cache policies per data source
    - Database fallback for offline scenarios
    - Automatic retry logic with exponential backoff
    - Circuit breaker pattern for resilience
    """

    def __init__(
        self,
        cache_service: CacheService | None = None,
        db_session: Session | AsyncSession | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.cache_service = cache_service or get_cache_service(db_session)
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Create cache directory
        self.cache_dir = Path(settings.HTTP_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Configure Hishel controller for intelligent caching
        self.controller = hishel.Controller(
            cacheable_methods=["GET", "HEAD"],
            cacheable_status_codes=[200, 301, 302, 304, 404],
            allow_stale=True,  # Serve stale content during outages
            always_revalidate=False,  # Only revalidate when necessary
            allow_heuristics=True,  # Use heuristic caching for responses without cache headers
        )

        # Configure Hishel storage - use AsyncFileStorage for async client compatibility
        self.storage = hishel.AsyncFileStorage(
            base_path=str(self.cache_dir),
            ttl=settings.HTTP_CACHE_TTL_DEFAULT,
            check_ttl_every=3600  # Check for expired entries every hour
        )

        # Create async HTTP client with caching
        self.http_client = hishel.AsyncCacheClient(
            controller=self.controller,
            storage=self.storage,
            timeout=httpx.Timeout(timeout)
        )

        # Circuit breaker state per domain
        self.circuit_breakers: dict[str, dict[str, Any]] = {}

        logger.info(f"CachedHttpClient initialized with cache dir: {self.cache_dir}")

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL for circuit breaker tracking."""
        return urlparse(url).netloc

    def _is_circuit_open(self, domain: str) -> bool:
        """Check if circuit breaker is open for a domain."""
        if domain not in self.circuit_breakers:
            return False

        breaker = self.circuit_breakers[domain]
        if breaker.get("state") == "open":
            # Check if enough time has passed to try again
            import time
            if time.time() - breaker.get("opened_at", 0) > 60:  # 1 minute cooldown
                breaker["state"] = "half_open"
                logger.info(f"Circuit breaker for {domain} moved to half-open state")
            return breaker["state"] == "open"

        return False

    def _record_success(self, domain: str) -> None:
        """Record successful request for circuit breaker."""
        if domain in self.circuit_breakers:
            self.circuit_breakers[domain] = {"state": "closed", "failures": 0}

    def _record_failure(self, domain: str) -> None:
        """Record failed request for circuit breaker."""
        if domain not in self.circuit_breakers:
            self.circuit_breakers[domain] = {"state": "closed", "failures": 0}

        breaker = self.circuit_breakers[domain]
        breaker["failures"] = breaker.get("failures", 0) + 1

        # Open circuit after 5 consecutive failures
        if breaker["failures"] >= 5:
            import time
            breaker["state"] = "open"
            breaker["opened_at"] = time.time()
            logger.warning(f"Circuit breaker opened for {domain} after {breaker['failures']} failures")

    async def get(
        self,
        url: str,
        namespace: str = "http",
        cache_key: str | None = None,
        fallback_ttl: int = 3600,
        force_refresh: bool = False,
        **kwargs
    ) -> httpx.Response:
        """
        Perform GET request with intelligent caching.

        Args:
            url: Request URL
            namespace: Cache namespace for database fallback
            cache_key: Custom cache key (defaults to URL)
            fallback_ttl: TTL for database cache fallback
            force_refresh: Force refresh bypassing cache
            **kwargs: Additional arguments for httpx
        """
        domain = self._get_domain(url)

        # Check circuit breaker
        if self._is_circuit_open(domain):
            logger.warning(f"Circuit breaker open for {domain}, attempting cache fallback")
            return await self._get_from_fallback_cache(url, namespace, cache_key)

        # Prepare request headers
        headers = kwargs.get("headers", {})
        if force_refresh:
            headers.update({
                "Cache-Control": "no-cache, must-revalidate",
                "Pragma": "no-cache"
            })
            kwargs["headers"] = headers

        # Attempt HTTP request with retries
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.http_client.get(url, **kwargs)

                # Record success for circuit breaker
                self._record_success(domain)

                # Store successful response in database cache as fallback
                if response.status_code == 200:
                    await self._store_fallback_cache(
                        url, response, namespace, cache_key, fallback_ttl
                    )

                return response

            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
                last_exception = e
                logger.warning(f"HTTP request attempt {attempt + 1} failed for {url}: {e}")

                if attempt < self.max_retries:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    # All retries failed, record failure and try cache fallback
                    self._record_failure(domain)
                    logger.error(f"All retry attempts failed for {url}, trying cache fallback")
                    return await self._get_from_fallback_cache(url, namespace, cache_key)

            except Exception as e:
                # Non-recoverable error
                logger.error(f"Non-recoverable error for {url}: {e}")
                self._record_failure(domain)
                raise

        # This should not be reached, but just in case
        if last_exception:
            raise last_exception
        else:
            raise httpx.RequestError(f"Request failed after {self.max_retries} retries")

    async def post(
        self,
        url: str,
        namespace: str = "http",
        cache_response: bool = False,
        **kwargs
    ) -> httpx.Response:
        """
        Perform POST request with optional response caching.

        Args:
            url: Request URL
            namespace: Cache namespace
            cache_response: Whether to cache the response
            **kwargs: Additional arguments for httpx
        """
        domain = self._get_domain(url)

        # Check circuit breaker
        if self._is_circuit_open(domain):
            raise httpx.RequestError(f"Circuit breaker open for {domain}")

        try:
            response = await self.http_client.post(url, **kwargs)
            self._record_success(domain)

            # Optionally cache successful POST responses
            if cache_response and response.status_code == 200:
                cache_key = f"post:{url}:{hash(str(kwargs))}"
                await self._store_fallback_cache(
                    cache_key, response, namespace, cache_key, 300  # 5 minute TTL
                )

            return response

        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
            self._record_failure(domain)
            logger.error(f"POST request failed for {url}: {e}")
            raise

    async def download_file(
        self,
        url: str,
        namespace: str = "files",
        cache_key: str | None = None,
        etag_check: bool = True,
        **kwargs
    ) -> bytes:
        """
        Download file with intelligent caching using ETags.

        Args:
            url: File URL
            namespace: Cache namespace
            cache_key: Custom cache key
            etag_check: Whether to use ETag for cache validation
            **kwargs: Additional arguments for httpx
        """
        if not cache_key:
            cache_key = f"file:{url}"

        # Check if we have cached file with ETag
        cached_data = None
        cached_etag = None

        if etag_check:
            cached_entry = await self.cache_service.get(
                f"{cache_key}:metadata", namespace
            )
            if cached_entry:
                cached_etag = cached_entry.get("etag")
                cached_data = await self.cache_service.get(cache_key, namespace)

        # Prepare conditional request headers
        headers = kwargs.get("headers", {})
        if cached_etag:
            headers["If-None-Match"] = cached_etag

        try:
            kwargs["headers"] = headers
            response = await self.get(url, namespace=namespace, **kwargs)

            # If content not modified, return cached data
            if response.status_code == 304 and cached_data:
                logger.info(f"File not modified (304), using cached version: {url}")
                return cached_data

            # Download and cache new content
            if response.status_code == 200:
                content = response.content

                # Cache the file content
                await self.cache_service.set(
                    cache_key, content, namespace,
                    self.cache_service._get_ttl_for_namespace(namespace)
                )

                # Cache metadata including ETag
                etag = response.headers.get("etag")
                if etag:
                    metadata = {
                        "etag": etag,
                        "last_modified": response.headers.get("last-modified"),
                        "content_length": len(content),
                        "content_type": response.headers.get("content-type")
                    }
                    await self.cache_service.set(
                        f"{cache_key}:metadata", metadata, namespace
                    )

                logger.info(f"Downloaded and cached file: {url} ({len(content)} bytes)")
                return content

            response.raise_for_status()

        except Exception as e:
            logger.error(f"Error downloading file {url}: {e}")

            # Try to return cached data if available
            if cached_data:
                logger.warning(f"Using stale cached file for {url}")
                return cached_data

            raise

    async def _get_from_fallback_cache(
        self,
        url: str,
        namespace: str,
        cache_key: str | None = None
    ) -> httpx.Response:
        """Get response from database cache as fallback."""
        if not cache_key:
            cache_key = f"fallback:{url}"

        cached_response = await self.cache_service.get(cache_key, namespace)

        if cached_response and isinstance(cached_response, dict):
            logger.info(f"Using fallback cache for {url}")
            # Reconstruct response from cached data
            content = cached_response.get("content", "")
            # Handle content that might be string or bytes
            if isinstance(content, str):
                content = content.encode("utf-8")
            elif not isinstance(content, bytes):
                content = str(content).encode("utf-8")

            response = httpx.Response(
                status_code=cached_response.get("status_code", 200),
                headers=cached_response.get("headers", {}),
                content=content,
                request=httpx.Request("GET", url)
            )
            return response
        else:
            # No cached data available or corrupted
            if cached_response is not None:
                logger.warning(f"Corrupted fallback cache for {url}, clearing it")
                await self.cache_service.delete(cache_key, namespace)
            logger.error(f"No fallback cache available for {url}")
            raise httpx.RequestError(f"No cached data available for {url}")

    async def _store_fallback_cache(
        self,
        url: str,
        response: httpx.Response,
        namespace: str,
        cache_key: str | None = None,
        ttl: int = 3600
    ) -> None:
        """Store response in database cache as fallback."""
        if not cache_key:
            cache_key = f"fallback:{url}"

        # Only cache successful responses
        if response.status_code != 200:
            return

        # Skip caching binary content in database (too large and problematic)
        content_type = response.headers.get("content-type", "").lower()
        if any(binary_type in content_type for binary_type in [
            "application/octet-stream",
            "application/vnd.ms-excel", 
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/zip",
            "application/pdf",
            "image/",
            "video/",
            "audio/"
        ]):
            logger.debug(f"Skipping database cache for binary content: {url} (type: {content_type})")
            return
            
        # Skip very large responses (> 1MB) to avoid database bloat
        if len(response.content) > 1024 * 1024:
            logger.debug(f"Skipping database cache for large response: {url} ({len(response.content)} bytes)")
            return

        try:
            # Try to decode as text
            try:
                content_text = response.content.decode("utf-8")
            except UnicodeDecodeError:
                # If it can't be decoded as UTF-8, it's likely binary - skip database caching
                logger.debug(f"Skipping database cache for non-UTF-8 content: {url}")
                return
                
            cached_response = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": content_text,
                "url": url,
                "cached_at": response.headers.get("date", "unknown")
            }

            await self.cache_service.set(cache_key, cached_response, namespace, ttl)
            logger.debug(f"Stored fallback cache for {url}")

        except Exception as e:
            logger.error(f"Error storing fallback cache for {url}: {e}")

    async def clear_cache(self, namespace: str | None = None) -> int:
        """Clear HTTP cache."""
        count = 0

        # Clear Hishel cache
        try:
            # Hishel doesn't provide a direct clear method, so we'll remove files
            if self.cache_dir.exists():
                for cache_file in self.cache_dir.glob("*"):
                    if cache_file.is_file():
                        cache_file.unlink()
                        count += 1
                logger.info(f"Cleared {count} HTTP cache files")
        except Exception as e:
            logger.error(f"Error clearing HTTP cache files: {e}")

        # Clear database fallback cache
        if namespace:
            db_count = await self.cache_service.clear_namespace(namespace)
            count += db_count

        return count

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats = {}

        # HTTP cache file stats
        try:
            if self.cache_dir.exists():
                cache_files = list(self.cache_dir.glob("*"))
                total_size = sum(f.stat().st_size for f in cache_files if f.is_file())
                stats["http_cache"] = {
                    "files": len(cache_files),
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "cache_dir": str(self.cache_dir)
                }
        except Exception as e:
            logger.error(f"Error getting HTTP cache stats: {e}")
            stats["http_cache"] = {"error": str(e)}

        # Circuit breaker stats
        stats["circuit_breakers"] = self.circuit_breakers.copy()

        # Database cache stats
        try:
            db_stats = await self.cache_service.get_stats()
            stats["database_cache"] = db_stats
        except Exception as e:
            logger.error(f"Error getting database cache stats: {e}")
            stats["database_cache"] = {"error": str(e)}

        return stats

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        if hasattr(self.http_client, 'aclose'):
            await self.http_client.aclose()
        elif hasattr(self.http_client, 'close'):
            await self.http_client.close()


# Global cached HTTP client instance
_cached_http_client: CachedHttpClient | None = None


def get_cached_http_client(
    cache_service: CacheService | None = None,
    db_session: Session | AsyncSession | None = None
) -> CachedHttpClient:
    """Get or create the global cached HTTP client instance."""
    global _cached_http_client

    if _cached_http_client is None:
        _cached_http_client = CachedHttpClient(cache_service, db_session)

    return _cached_http_client


# Convenience functions

async def cached_get(
    url: str,
    namespace: str = "http",
    cache_key: str | None = None,
    **kwargs
) -> httpx.Response:
    """Perform cached GET request."""
    client = get_cached_http_client()
    return await client.get(url, namespace, cache_key, **kwargs)


async def cached_download(
    url: str,
    namespace: str = "files",
    cache_key: str | None = None,
    **kwargs
) -> bytes:
    """Download file with caching."""
    client = get_cached_http_client()
    return await client.download_file(url, namespace, cache_key, **kwargs)
