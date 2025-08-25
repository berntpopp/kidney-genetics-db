"""
Caching layer for gene annotations.
"""

import json
from datetime import datetime, timedelta
from typing import Any

import redis
from redis import Redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AnnotationCache:
    """
    Redis-based cache for gene annotations.

    Provides fast access to frequently requested annotation data.
    """

    def __init__(self):
        """Initialize Redis connection."""
        try:
            # Try to connect to Redis
            self.redis_client: Redis | None = redis.Redis(
                host=settings.REDIS_HOST if hasattr(settings, "REDIS_HOST") else "localhost",
                port=settings.REDIS_PORT if hasattr(settings, "REDIS_PORT") else 6379,
                db=settings.REDIS_DB if hasattr(settings, "REDIS_DB") else 0,
                decode_responses=True,
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.sync_info("Redis cache initialized successfully")
        except (redis.ConnectionError, AttributeError) as e:
            # Redis not available, use in-memory cache fallback
            self.redis_client = None
            self.enabled = False
            self._memory_cache = {}
            logger.sync_warning(f"Redis not available, using in-memory cache: {str(e)}")

    def _generate_key(self, key_type: str, **kwargs) -> str:
        """
        Generate a cache key based on type and parameters.

        Args:
            key_type: Type of cache key (e.g., 'annotation', 'summary')
            **kwargs: Additional parameters for the key

        Returns:
            Cache key string
        """
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        param_str = "_".join([f"{k}:{v}" for k, v in sorted_params])
        return f"gene_annotations:{key_type}:{param_str}"

    def get(self, key: str) -> dict[str, Any] | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled:
            # Use in-memory cache
            cached = self._memory_cache.get(key)
            if cached:
                # Check expiry
                if cached["expiry"] > datetime.utcnow():
                    return cached["data"]
                else:
                    del self._memory_cache[key]
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.sync_error(f"Cache get error: {str(e)}", key=key)

        return None

    def set(self, key: str, value: dict[str, Any], ttl: int = 3600):
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default 1 hour)
        """
        if not self.enabled:
            # Use in-memory cache
            self._memory_cache[key] = {
                "data": value,
                "expiry": datetime.utcnow() + timedelta(seconds=ttl),
            }
            # Limit memory cache size
            if len(self._memory_cache) > 1000:
                # Remove oldest entries
                oldest_keys = sorted(
                    self._memory_cache.keys(), key=lambda k: self._memory_cache[k]["expiry"]
                )[:100]
                for k in oldest_keys:
                    del self._memory_cache[k]
            return

        try:
            self.redis_client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.sync_error(f"Cache set error: {str(e)}", key=key)

    def delete(self, pattern: str):
        """
        Delete cache entries matching pattern.

        Args:
            pattern: Pattern to match keys (e.g., 'gene_annotations:*:gene_id:123')
        """
        if not self.enabled:
            # Delete from memory cache
            keys_to_delete = [k for k in self._memory_cache.keys() if pattern.replace("*", "") in k]
            for key in keys_to_delete:
                del self._memory_cache[key]
            return

        try:
            # Find all keys matching pattern
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.sync_info(f"Deleted {len(keys)} cache entries", pattern=pattern)
        except Exception as e:
            logger.sync_error(f"Cache delete error: {str(e)}", pattern=pattern)

    def get_annotation(self, gene_id: int, source: str | None = None) -> dict[str, Any] | None:
        """
        Get cached annotation for a gene.

        Args:
            gene_id: Gene database ID
            source: Optional source filter

        Returns:
            Cached annotation data or None
        """
        key = self._generate_key("annotation", gene_id=gene_id, source=source or "all")
        return self.get(key)

    def set_annotation(
        self, gene_id: int, data: dict[str, Any], source: str | None = None, ttl: int = 3600
    ):
        """
        Cache annotation data for a gene.

        Args:
            gene_id: Gene database ID
            data: Annotation data to cache
            source: Optional source filter
            ttl: Time to live in seconds
        """
        key = self._generate_key("annotation", gene_id=gene_id, source=source or "all")
        self.set(key, data, ttl)

    def invalidate_gene(self, gene_id: int):
        """
        Invalidate all cached data for a specific gene.

        Args:
            gene_id: Gene database ID
        """
        pattern = f"gene_annotations:*:gene_id:{gene_id}*"
        self.delete(pattern)
        logger.sync_info(f"Invalidated cache for gene {gene_id}")

    def invalidate_source(self, source: str):
        """
        Invalidate all cached data for a specific source.

        Args:
            source: Source name
        """
        pattern = f"gene_annotations:*:source:{source}*"
        self.delete(pattern)
        logger.sync_info(f"Invalidated cache for source {source}")

    def get_summary(self, gene_id: int) -> dict[str, Any] | None:
        """
        Get cached annotation summary.

        Args:
            gene_id: Gene database ID

        Returns:
            Cached summary or None
        """
        key = self._generate_key("summary", gene_id=gene_id)
        return self.get(key)

    def set_summary(self, gene_id: int, data: dict[str, Any], ttl: int = 7200):
        """
        Cache annotation summary.

        Args:
            gene_id: Gene database ID
            data: Summary data
            ttl: Time to live (default 2 hours)
        """
        key = self._generate_key("summary", gene_id=gene_id)
        self.set(key, data, ttl)

    def clear_all(self):
        """Clear all annotation cache entries."""
        if not self.enabled:
            self._memory_cache.clear()
            return

        try:
            pattern = "gene_annotations:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.sync_info(f"Cleared {len(keys)} cache entries")
        except Exception as e:
            logger.sync_error(f"Cache clear error: {str(e)}")

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.enabled:
            return {
                "type": "memory",
                "enabled": False,
                "entries": len(self._memory_cache),
                "message": "Using in-memory cache (Redis not available)",
            }

        try:
            info = self.redis_client.info()
            keys = self.redis_client.keys("gene_annotations:*")

            return {
                "type": "redis",
                "enabled": True,
                "entries": len(keys),
                "memory_used": info.get("used_memory_human", "N/A"),
                "hit_rate": info.get("keyspace_hit_ratio", 0),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            return {"type": "redis", "enabled": False, "error": str(e)}


# Global cache instance
annotation_cache = AnnotationCache()
