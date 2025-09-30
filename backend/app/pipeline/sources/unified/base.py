"""
Enhanced unified base class for all data sources.

This module extends the existing DataSourceClient with unified patterns for:
- Automatic caching with TTL management
- Retry logic with exponential backoff
- Batch processing capabilities
- Consistent error handling
"""

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.data_source_base import DataSourceClient
from app.core.logging import get_logger
from app.core.retry_utils import RetryStrategy

logger = get_logger(__name__)


class UnifiedDataSource(DataSourceClient, ABC):
    """
    Enhanced unified base class for all data sources.

    Extends DataSourceClient with:
    - Unified caching patterns
    - Configurable retry strategies
    - Batch processing capabilities
    - Consistent logging and monitoring
    """

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | None = None,
        retry_strategy: RetryStrategy | None = None,
        cache_ttl: int | None = None,
        batch_size: int = 50,
        force_refresh: bool = False,
    ):
        """
        Initialize unified data source with enhanced capabilities.

        Args:
            cache_service: Cache service instance
            http_client: HTTP client with caching
            db_session: Database session
            retry_strategy: Retry strategy for failed operations
            cache_ttl: Cache TTL in seconds (overrides default)
            batch_size: Size for batch processing
            force_refresh: Force refresh of cached data
        """
        # Create dependencies if not provided
        if cache_service is None:
            from app.core.cache_service import get_cache_service

            cache_service = get_cache_service(db_session)
            logger.sync_info("Created cache service", source_class=self.__class__.__name__)

        if http_client is None:
            from app.core.cached_http_client import get_cached_http_client

            http_client = get_cached_http_client(cache_service, db_session)
            logger.sync_info("Created HTTP client", source_class=self.__class__.__name__)

        super().__init__(cache_service, http_client, db_session)

        self.retry_strategy = retry_strategy or RetryStrategy(
            max_retries=3, initial_delay=1.0, max_delay=30.0, exponential_base=2.0
        )
        self.cache_ttl = cache_ttl or self._get_default_ttl()
        self.batch_size = batch_size
        self.force_refresh = force_refresh

        # Statistics tracking
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls": 0,
            "retries": 0,
            "errors": 0,
        }

    @abstractmethod
    def _get_default_ttl(self) -> int:
        """Get default TTL for this data source."""
        pass

    async def fetch_with_cache(
        self,
        cache_key: str,
        fetch_func: Callable,
        ttl: int | None = None,
        force_refresh: bool = False,
    ) -> Any:
        """
        Unified caching pattern for all data fetching.

        Args:
            cache_key: Key for caching
            fetch_func: Async function to fetch data
            ttl: Cache TTL (uses default if not provided)
            force_refresh: Force refresh ignoring cache

        Returns:
            Fetched or cached data
        """
        effective_ttl = ttl or self.cache_ttl
        should_refresh = force_refresh or self.force_refresh

        # Generate full cache key with namespace
        full_key = f"{self.namespace}:{cache_key}"

        # Check cache first (unless forcing refresh)
        if not should_refresh and self.cache_service:
            try:
                cached_data = await self.cache_service.get(full_key)
                if cached_data is not None:
                    self.stats["cache_hits"] += 1
                    logger.sync_debug("Cache hit", cache_key=full_key)
                    return cached_data
            except Exception as e:
                logger.sync_warning("Cache retrieval failed", cache_key=full_key, error=e)

        self.stats["cache_misses"] += 1

        # Fetch fresh data with retry logic
        try:
            self.stats["api_calls"] += 1
            data = await self.retry_strategy.execute_async(fetch_func)

            # Validate fetched data
            if data is None:
                logger.sync_warning("Fetch function returned None", cache_key=full_key)
                return None

            # Cache the data
            if self.cache_service and data is not None:
                try:
                    await self.cache_service.set(
                        full_key, data, namespace="default", ttl=effective_ttl
                    )
                    logger.sync_debug("Cached data", cache_key=full_key, ttl_seconds=effective_ttl)
                except Exception as e:
                    logger.sync_warning("Failed to cache data", cache_key=full_key, error=e)
                    # Continue anyway - caching failure shouldn't break the fetch

            return data

        except Exception as e:
            self.stats["errors"] += 1

            # Provide specific error handling for common issues
            if "timeout" in str(e).lower():
                logger.sync_error("Timeout while fetching data", cache_key=full_key, error=e)
            elif "connection" in str(e).lower():
                logger.sync_error(
                    "Connection error while fetching data", cache_key=full_key, error=e
                )
            elif "permission" in str(e).lower() or "unauthorized" in str(e).lower():
                logger.sync_error("Authentication/authorization error", cache_key=full_key, error=e)
            else:
                logger.sync_error("Failed to fetch data", cache_key=full_key, error=e)

            raise

    async def fetch_batch_with_cache(
        self,
        items: list,
        cache_key_func: Callable[[Any], str],
        fetch_func: Callable[[list], dict],
        ttl: int | None = None,
    ) -> dict:
        """
        Fetch multiple items with intelligent caching.

        This method:
        1. Checks cache for each item
        2. Fetches missing items in batch
        3. Caches individual results

        Args:
            items: List of items to fetch
            cache_key_func: Function to generate cache key for each item
            fetch_func: Async function to fetch batch of items
            ttl: Cache TTL

        Returns:
            Dictionary mapping items to their data
        """
        effective_ttl = ttl or self.cache_ttl
        results = {}
        missing_items = []

        # Check cache for each item
        for item in items:
            cache_key = f"{self.namespace}:{cache_key_func(item)}"

            if not self.force_refresh and self.cache_service:
                try:
                    cached = await self.cache_service.get(cache_key)
                    if cached is not None:
                        results[item] = cached
                        self.stats["cache_hits"] += 1
                        continue
                except Exception as e:
                    logger.sync_warning("Cache check failed", cache_key=cache_key, error=e)

            missing_items.append(item)
            self.stats["cache_misses"] += 1

        # Fetch missing items in batches
        if missing_items:
            for i in range(0, len(missing_items), self.batch_size):
                batch = missing_items[i : i + self.batch_size]

                try:
                    self.stats["api_calls"] += 1
                    batch_data = await self.retry_strategy.execute_async(
                        lambda b=batch: fetch_func(b)
                    )

                    # Cache individual results
                    for item in batch:
                        if item in batch_data:
                            data = batch_data[item]
                            results[item] = data

                            if self.cache_service:
                                cache_key = f"{self.namespace}:{cache_key_func(item)}"
                                try:
                                    await self.cache_service.set(
                                        cache_key, data, namespace="default", ttl=effective_ttl
                                    )
                                except Exception as e:
                                    logger.sync_warning(
                                        "Failed to cache item", cache_key=cache_key, error=e
                                    )

                except Exception as e:
                    self.stats["errors"] += 1
                    logger.sync_error("Failed to fetch batch", error=e, batch_size=len(batch))
                    # Continue with next batch

        return results

    async def invalidate_cache(self, pattern: str | None = None) -> int:
        """
        Invalidate cached data for this source.

        Args:
            pattern: Optional pattern to match (default: all cache for this source)

        Returns:
            Number of cache entries invalidated
        """
        if not self.cache_service:
            return 0

        cache_pattern = f"{self.namespace}:{pattern or '*'}"

        try:
            count = await self.cache_service.delete_pattern(cache_pattern)
            logger.sync_info("Invalidated cache entries", count=count, pattern=cache_pattern)
            return count
        except Exception as e:
            logger.sync_error("Failed to invalidate cache", pattern=cache_pattern, error=e)
            return 0

    def _get_source_detail(self, evidence_data: dict[str, Any]) -> str:
        """
        Generate source detail string for evidence.
        Override in subclasses for custom formatting.
        """
        count = evidence_data.get("evidence_count", 0)
        return f"{self.source_name}: {count} evidence items"

    def get_cache_key(self, *parts: Any) -> str:
        """
        Generate a cache key from parts.

        Args:
            *parts: Parts to include in cache key

        Returns:
            Generated cache key
        """
        # Create a string representation of all parts
        key_parts = [str(p) for p in parts]
        key_string = ":".join(key_parts)

        # If key is too long, hash it
        if len(key_string) > 200:
            hash_obj = hashlib.sha256(key_string.encode())
            return hash_obj.hexdigest()[:32]

        return key_string

    async def get_last_update_time(self) -> datetime | None:
        """
        Get the last update time for this data source.

        Returns:
            Last update datetime or None
        """
        if not self.cache_service:
            return None

        cache_key = f"{self.namespace}:last_update"

        try:
            timestamp = await self.cache_service.get(cache_key)
            if timestamp:
                return datetime.fromisoformat(timestamp)
        except Exception as e:
            logger.sync_warning("Failed to get last update time", error=e)

        return None

    async def set_last_update_time(self, update_time: datetime | None = None) -> None:
        """
        Set the last update time for this data source.

        Args:
            update_time: Update time (defaults to current time)
        """
        if not self.cache_service:
            return

        cache_key = f"{self.namespace}:last_update"
        timestamp = (update_time or datetime.now(timezone.utc)).isoformat()

        try:
            # Store with long TTL (30 days)
            await self.cache_service.set(cache_key, timestamp, 30 * 24 * 3600)
        except Exception as e:
            logger.sync_warning("Failed to set last update time", error=e)

    async def should_update(self, max_age_hours: int = 24) -> bool:
        """
        Check if data source should be updated based on age.

        Args:
            max_age_hours: Maximum age in hours before update is needed

        Returns:
            True if update is needed
        """
        if self.force_refresh:
            return True

        last_update = await self.get_last_update_time()

        if not last_update:
            return True

        age = datetime.now(timezone.utc) - last_update
        return age > timedelta(hours=max_age_hours)

    def get_statistics(self) -> dict:
        """
        Get statistics for this data source session.

        Returns:
            Dictionary of statistics
        """
        stats = self.stats.copy()

        # Calculate hit rate
        total_requests = stats["cache_hits"] + stats["cache_misses"]
        if total_requests > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / total_requests
        else:
            stats["cache_hit_rate"] = 0.0

        return stats

    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls": 0,
            "retries": 0,
            "errors": 0,
        }

    async def warmup_cache(self, items: list | None = None) -> dict:
        """
        Pre-populate cache with commonly accessed data.

        Args:
            items: Optional list of items to warm up

        Returns:
            Statistics about warmup process
        """
        warmup_stats = {
            "items_processed": 0,
            "items_cached": 0,
            "errors": 0,
            "duration_seconds": 0,
        }

        start_time = datetime.now(timezone.utc)

        # Default implementation - subclasses should override
        logger.sync_info("Starting cache warmup", source_name=self.source_name)

        # Fetch and cache raw data
        try:
            data = await self.fetch_raw_data()
            if data:
                warmup_stats["items_cached"] += 1
        except Exception as e:
            logger.sync_error("Cache warmup failed", error=e)
            warmup_stats["errors"] += 1

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        warmup_stats["duration_seconds"] = duration

        logger.sync_info(
            "Cache warmup completed",
            source_name=self.source_name,
            items_cached=warmup_stats["items_cached"],
            duration_seconds=round(duration, 2),
        )

        return warmup_stats
