"""
Modern cache service for the kidney genetics database.

This module provides a unified caching interface that combines:
- L1 (Memory): Fast in-memory LRU cache for hot data
- L2 (Database): PostgreSQL-backed persistent cache for sharing across instances
- Intelligent TTL management per data source
- Cache statistics and monitoring
"""

import asyncio
import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar

import cachetools
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datasource_config import get_source_cache_ttl
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CacheEntry:
    """Represents a cache entry with metadata."""

    def __init__(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        ttl: int | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.key = key
        self.value = value
        self.namespace = namespace
        self.created_at = datetime.now(timezone.utc)
        self.ttl = ttl
        self.expires_at = self.created_at + timedelta(seconds=ttl) if ttl is not None else None
        self.last_accessed = self.created_at
        self.access_count = 1
        self.metadata = metadata or {}

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def touch(self) -> None:
        """Update access statistics."""
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1


class CacheStats:
    """Cache statistics container."""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.total_size = 0
        self.memory_entries = 0
        self.db_entries = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "hit_rate": self.hit_rate,
            "total_size": self.total_size,
            "memory_entries": self.memory_entries,
            "db_entries": self.db_entries,
        }


class CacheService:
    """
    Unified cache service with multi-layer caching strategy.

    Features:
    - L1 (Memory): Fast LRU cache for hot data
    - L2 (Database): Persistent PostgreSQL storage
    - Intelligent TTL management per namespace
    - Cache statistics and monitoring
    - Graceful error handling and fallback
    """

    def __init__(self, db_session: Session | AsyncSession | None = None):
        self.db_session = db_session
        self.enabled = settings.CACHE_ENABLED

        # L1 Cache: In-memory LRU cache
        self.memory_cache: cachetools.LRUCache = cachetools.LRUCache(
            maxsize=settings.CACHE_MAX_MEMORY_SIZE
        )

        # Cache statistics
        self.stats = CacheStats()

        # TTL mapping per namespace from datasource config
        self.namespace_ttls = {
            "hgnc": get_source_cache_ttl("HGNC"),
            "pubtator": get_source_cache_ttl("PubTator"),
            "gencc": get_source_cache_ttl("GenCC"),
            "panelapp": get_source_cache_ttl("PanelApp"),
            "hpo": get_source_cache_ttl("HPO"),
            "clingen": get_source_cache_ttl("ClinGen"),
            "default": settings.CACHE_DEFAULT_TTL,
        }

        logger.sync_info("CacheService initialized", enabled=self.enabled)

    def _generate_cache_key(self, key: Any, namespace: str = "default") -> str:
        """Generate a unique cache key with type normalization."""
        # Normalize key to string
        if isinstance(key, str):
            normalized_key = key
        elif isinstance(key, int | float):
            normalized_key = str(key)
        elif isinstance(key, list | dict | tuple):
            # Serialize complex types to JSON for consistent hashing
            normalized_key = json.dumps(key, sort_keys=True, default=str)
        else:
            normalized_key = str(key)

        # Create a hash of the key for consistent length and safety
        key_hash = hashlib.sha256(f"{namespace}:{normalized_key}".encode()).hexdigest()
        return f"{namespace}:{key_hash}"

    def _get_ttl_for_namespace(self, namespace: str) -> int:
        """Get TTL for a specific namespace."""
        return self.namespace_ttls.get(namespace, self.namespace_ttls["default"])

    def _serialize_value(self, value: Any) -> str:
        """Serialize a value for storage with pandas DataFrame support."""
        try:
            # Handle pandas DataFrames
            try:
                import pandas as pd

                if isinstance(value, pd.DataFrame):
                    # Convert DataFrame to JSON-serializable dict
                    return json.dumps(
                        {
                            "_type": "dataframe",
                            "data": value.to_dict(orient="records"),
                            "columns": list(value.columns),
                            "index": list(value.index),
                        },
                        default=str,
                        ensure_ascii=False,
                    )
            except ImportError:
                # pandas not available, continue with regular serialization
                pass

            return json.dumps(value, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.sync_error(
                "Error serializing value",
                error=str(e),
                value_type=str(type(value)),
                value_repr=repr(value)[:200] if value else 'None'
            )
            raise

    def _deserialize_value(self, serialized: Any) -> Any:
        """Deserialize a value from storage with type safety and DataFrame support."""
        try:
            # Handle None
            if serialized is None:
                return None

            # If it's already a dict/list/bool/number, check for DataFrame format
            if isinstance(serialized, dict):
                if serialized.get("_type") == "dataframe":
                    # Reconstruct DataFrame
                    try:
                        import pandas as pd

                        return pd.DataFrame(serialized["data"])
                    except ImportError:
                        # pandas not available, return as dict
                        return serialized
                return serialized

            if isinstance(serialized, list | bool | int | float):
                return serialized

            # Handle string serialization
            if isinstance(serialized, str):
                if not serialized or serialized.strip() == "":
                    logger.sync_warning("Attempted to deserialize empty string value, returning None")
                    return None

                data = json.loads(serialized)
                # Check if it's a serialized DataFrame
                if isinstance(data, dict) and data.get("_type") == "dataframe":
                    try:
                        import pandas as pd

                        return pd.DataFrame(data["data"])
                    except ImportError:
                        # pandas not available, return as dict
                        return data
                return data

            # Handle other types by converting to string first
            logger.sync_warning(
                "Unexpected type for cache value, converting to string",
                value_type=str(type(serialized))
            )
            return json.loads(str(serialized))

        except (TypeError, ValueError) as e:
            logger.sync_error(
                "Error deserializing value",
                error=str(e),
                serialized_preview=str(serialized)[:100] if serialized else repr(serialized)
            )
            # Return None instead of raising to allow graceful recovery
            return None

    async def get(self, key: Any, namespace: str = "default", default: Any = None) -> Any:
        """
        Get a value from cache.

        Checks L1 (memory) first, then L2 (database).
        """
        if not self.enabled:
            return default

        cache_key = self._generate_cache_key(key, namespace)

        try:
            # L1 Cache: Check memory first
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                if not entry.is_expired():
                    entry.touch()
                    self.stats.hits += 1
                    logger.sync_debug("Cache hit (memory)", namespace=namespace, key=str(key))
                    return entry.value
                else:
                    # Remove expired entry
                    del self.memory_cache[cache_key]

            # L2 Cache: Check database
            if self.db_session:
                db_entry = await self._get_from_db(cache_key)
                if db_entry:
                    # Update access statistics in DB
                    await self._update_access_stats(cache_key)

                    # Store in memory cache for future hits
                    ttl = self._get_ttl_for_namespace(namespace)
                    memory_entry = CacheEntry(key, db_entry, namespace, ttl)
                    self.memory_cache[cache_key] = memory_entry

                    self.stats.hits += 1
                    logger.sync_debug("Cache hit (database)", namespace=namespace, key=str(key))
                    return db_entry

            # Cache miss
            self.stats.misses += 1
            logger.sync_debug("Cache miss", namespace=namespace, key=str(key))
            return default

        except Exception as e:
            self.stats.errors += 1
            logger.sync_error(
                "Error getting cache entry",
                namespace=namespace,
                key=str(key),
                error=str(e)
            )
            return default

    async def set(
        self, key: Any, value: Any, namespace: str = "default", ttl: int | None = None
    ) -> bool:
        """
        Set a value in cache.

        Stores in both L1 (memory) and L2 (database).
        """
        if not self.enabled:
            return False

        cache_key = self._generate_cache_key(key, namespace)

        if ttl is None:
            ttl = self._get_ttl_for_namespace(namespace)

        try:
            # Create cache entry
            entry = CacheEntry(key, value, namespace, ttl)

            # L1 Cache: Store in memory
            self.memory_cache[cache_key] = entry

            # L2 Cache: Store in database
            if self.db_session:
                await self._set_in_db(cache_key, entry)

            self.stats.sets += 1
            logger.sync_debug("Cache set", namespace=namespace, key=str(key), ttl=ttl)
            return True

        except Exception as e:
            self.stats.errors += 1
            logger.sync_error(
                "Error setting cache entry",
                namespace=namespace,
                key=str(key),
                error=str(e)
            )
            return False

    async def delete(self, key: Any, namespace: str = "default") -> bool:
        """Delete a value from cache."""
        if not self.enabled:
            return False

        cache_key = self._generate_cache_key(key, namespace)

        try:
            # L1 Cache: Remove from memory
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]

            # L2 Cache: Remove from database
            if self.db_session:
                await self._delete_from_db(cache_key)

            self.stats.deletes += 1
            logger.sync_debug("Cache delete", namespace=namespace, key=str(key))
            return True

        except Exception as e:
            self.stats.errors += 1
            logger.sync_error(
                "Error deleting cache entry",
                namespace=namespace,
                key=str(key),
                error=str(e)
            )
            return False

    async def get_or_set(
        self,
        key: Any,
        fetch_func: Callable[[], Any],
        namespace: str = "default",
        ttl: int | None = None,
    ) -> Any:
        """
        Get value from cache or fetch and cache it.

        This implements the cache-aside pattern.
        """
        # Try to get from cache first
        cached_value = await self.get(key, namespace)
        if cached_value is not None:
            return cached_value

        # Fetch the value
        try:
            if asyncio.iscoroutinefunction(fetch_func):
                value = await fetch_func()
            else:
                value = fetch_func()

            # Cache the fetched value
            await self.set(key, value, namespace, ttl)
            return value

        except Exception as e:
            logger.sync_error(
                "Error in fetch function",
                namespace=namespace,
                key=str(key),
                error=str(e)
            )
            raise

    async def clear_namespace(self, namespace: str) -> int:
        """Clear all cache entries in a namespace."""
        if not self.enabled:
            return 0

        try:
            count = 0

            # L1 Cache: Clear memory entries
            keys_to_remove = [k for k, v in self.memory_cache.items() if v.namespace == namespace]
            for key in keys_to_remove:
                del self.memory_cache[key]
                count += 1

            # L2 Cache: Clear database entries
            if self.db_session:
                db_count = await self._clear_namespace_from_db(namespace)
                count += db_count

            logger.sync_info("Cleared entries from namespace", namespace=namespace, count=count)
            return count

        except Exception as e:
            self.stats.errors += 1
            logger.sync_error("Error clearing namespace", namespace=namespace, error=str(e))
            return 0

    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache."""
        if not self.enabled:
            return 0

        try:
            count = 0

            # L1 Cache: Clean expired memory entries
            datetime.now(timezone.utc)
            expired_keys = [k for k, v in self.memory_cache.items() if v.is_expired()]
            for key in expired_keys:
                del self.memory_cache[key]
                count += 1

            # L2 Cache: Clean expired database entries
            if self.db_session:
                db_count = await self._cleanup_expired_from_db()
                count += db_count

            if count > 0:
                logger.sync_info("Cleaned up expired cache entries", count=count)
            return count

        except Exception as e:
            self.stats.errors += 1
            logger.sync_error("Error cleaning up expired entries", error=str(e))
            return 0

    async def get_stats(self, namespace: str | None = None) -> dict[str, Any]:
        """Get cache statistics."""
        try:
            # Update current stats
            self.stats.memory_entries = len(self.memory_cache)

            if self.db_session:
                self.stats.db_entries = await self._get_db_entry_count(namespace)

            stats = self.stats.to_dict()

            # Add namespace-specific stats if requested
            if namespace and self.db_session:
                namespace_stats = await self._get_namespace_stats(namespace)
                stats["namespace"] = namespace_stats

            return stats

        except Exception as e:
            logger.sync_error("Error getting cache stats", error=str(e))
            return {"error": str(e)}

    # Database operations

    async def _get_from_db(self, cache_key: str) -> Any | None:
        """Get entry from database cache."""
        if not self.db_session:
            return None

        try:
            from sqlalchemy.ext.asyncio import AsyncSession

            query = text(
                """
                SELECT data, expires_at
                FROM cache_entries
                WHERE cache_key = :cache_key
                AND (expires_at IS NULL OR expires_at > NOW())
            """
            )

            if isinstance(self.db_session, AsyncSession):
                result = await self.db_session.execute(query, {"cache_key": cache_key})
            else:
                result = self.db_session.execute(query, {"cache_key": cache_key})

            row = result.fetchone()

            if row:
                # JSONB columns are automatically deserialized by PostgreSQL
                # Check if it's already a dict (JSONB) or a string (TEXT)
                if isinstance(row.data, dict):
                    return row.data
                else:
                    # Deserialize and handle corrupted entries
                    deserialized = self._deserialize_value(row.data)
                    if deserialized is None:
                        # Remove corrupted entry from database
                        logger.sync_warning("Removing corrupted cache entry", cache_key=cache_key)
                        await self._delete_from_db(cache_key)
                    return deserialized
            return None

        except Exception as e:
            logger.sync_error("Database cache get error", error=str(e))
            return None

    async def _set_in_db(self, cache_key: str, entry: CacheEntry) -> bool:
        """Set entry in database cache."""
        if not self.db_session:
            return False

        try:
            # For JSONB column, we can store the value directly as dict/list
            # No need to serialize to string
            data_value = entry.value
            data_size = len(json.dumps(data_value).encode("utf-8"))

            query = text(
                """
                INSERT INTO cache_entries
                (cache_key, namespace, data, expires_at, data_size, metadata)
                VALUES (:cache_key, :namespace, CAST(:data AS jsonb), :expires_at, :data_size, CAST(:metadata AS jsonb))
                ON CONFLICT (cache_key)
                DO UPDATE SET
                    data = EXCLUDED.data,
                    expires_at = EXCLUDED.expires_at,
                    last_accessed = NOW(),
                    access_count = cache_entries.access_count + 1,
                    data_size = EXCLUDED.data_size,
                    metadata = EXCLUDED.metadata
            """
            )

            from sqlalchemy.ext.asyncio import AsyncSession

            if isinstance(self.db_session, AsyncSession):
                await self.db_session.execute(
                    query,
                    {
                        "cache_key": cache_key,
                        "namespace": entry.namespace,
                        "data": json.dumps(data_value),  # Pass as JSON string for JSONB casting
                        "expires_at": entry.expires_at,
                        "data_size": data_size,
                        "metadata": json.dumps(entry.metadata),
                    },
                )
                await self.db_session.commit()
            else:
                self.db_session.execute(
                    query,
                    {
                        "cache_key": cache_key,
                        "namespace": entry.namespace,
                        "data": json.dumps(data_value),  # Pass as JSON string for JSONB casting
                        "expires_at": entry.expires_at,
                        "data_size": data_size,
                        "metadata": json.dumps(entry.metadata),
                    },
                )
                self.db_session.commit()
            return True

        except Exception as e:
            from sqlalchemy.ext.asyncio import AsyncSession

            if isinstance(self.db_session, AsyncSession):
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.sync_error("Database cache set error", error=str(e))
            return False

    async def _delete_from_db(self, cache_key: str) -> bool:
        """Delete entry from database cache."""
        if not self.db_session:
            return False

        try:
            from sqlalchemy.ext.asyncio import AsyncSession

            query = text("DELETE FROM cache_entries WHERE cache_key = :cache_key")
            if isinstance(self.db_session, AsyncSession):
                await self.db_session.execute(query, {"cache_key": cache_key})
                await self.db_session.commit()
            else:
                self.db_session.execute(query, {"cache_key": cache_key})
                self.db_session.commit()
            return True

        except Exception as e:
            from sqlalchemy.ext.asyncio import AsyncSession

            if isinstance(self.db_session, AsyncSession):
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.sync_error("Database cache delete error", error=str(e))
            return False

    async def _update_access_stats(self, cache_key: str) -> None:
        """Update access statistics for a cache entry."""
        if not self.db_session:
            return

        try:
            from sqlalchemy.ext.asyncio import AsyncSession

            query = text(
                """
                UPDATE cache_entries
                SET last_accessed = NOW(), access_count = access_count + 1
                WHERE cache_key = :cache_key
            """
            )

            if isinstance(self.db_session, AsyncSession):
                await self.db_session.execute(query, {"cache_key": cache_key})
                await self.db_session.commit()
            else:
                self.db_session.execute(query, {"cache_key": cache_key})
                self.db_session.commit()

        except Exception as e:
            from sqlalchemy.ext.asyncio import AsyncSession

            if isinstance(self.db_session, AsyncSession):
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.sync_error("Database access stats update error", error=str(e))

    async def _clear_namespace_from_db(self, namespace: str) -> int:
        """Clear all entries from a namespace in database."""
        if not self.db_session:
            return 0

        try:
            from sqlalchemy.ext.asyncio import AsyncSession

            query = text("DELETE FROM cache_entries WHERE namespace = :namespace")
            if isinstance(self.db_session, AsyncSession):
                result = await self.db_session.execute(query, {"namespace": namespace})
                await self.db_session.commit()
            else:
                result = self.db_session.execute(query, {"namespace": namespace})
                self.db_session.commit()
            return result.rowcount

        except Exception as e:
            from sqlalchemy.ext.asyncio import AsyncSession

            if isinstance(self.db_session, AsyncSession):
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.sync_error("Database namespace clear error", error=str(e))
            return 0

    async def _cleanup_expired_from_db(self) -> int:
        """Remove expired entries from database."""
        if not self.db_session:
            return 0

        try:
            from sqlalchemy.ext.asyncio import AsyncSession

            query = text(
                """
                DELETE FROM cache_entries
                WHERE expires_at IS NOT NULL AND expires_at <= NOW()
            """
            )

            if isinstance(self.db_session, AsyncSession):
                result = await self.db_session.execute(query)
                await self.db_session.commit()
            else:
                result = self.db_session.execute(query)
                self.db_session.commit()
            return result.rowcount

        except Exception as e:
            from sqlalchemy.ext.asyncio import AsyncSession

            if isinstance(self.db_session, AsyncSession):
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.sync_error("Database cleanup error", error=str(e))
            return 0

    async def _get_db_entry_count(self, namespace: str | None = None) -> int:
        """Get count of entries in database."""
        if not self.db_session:
            return 0

        try:
            from sqlalchemy.ext.asyncio import AsyncSession

            if namespace:
                query = text("SELECT COUNT(*) FROM cache_entries WHERE namespace = :namespace")
                if isinstance(self.db_session, AsyncSession):
                    result = await self.db_session.execute(query, {"namespace": namespace})
                else:
                    result = self.db_session.execute(query, {"namespace": namespace})
            else:
                query = text("SELECT COUNT(*) FROM cache_entries")
                if isinstance(self.db_session, AsyncSession):
                    result = await self.db_session.execute(query)
                else:
                    result = self.db_session.execute(query)

            return result.scalar() or 0

        except Exception as e:
            logger.sync_error("Database entry count error", error=str(e))
            return 0

    async def _get_namespace_stats(self, namespace: str) -> dict[str, Any]:
        """Get statistics for a specific namespace."""
        if not self.db_session:
            return {}

        try:
            from sqlalchemy.ext.asyncio import AsyncSession

            query = text("SELECT * FROM cache_stats WHERE namespace = :namespace")
            if isinstance(self.db_session, AsyncSession):
                result = await self.db_session.execute(query, {"namespace": namespace})
            else:
                result = self.db_session.execute(query, {"namespace": namespace})

            row = result.fetchone()

            if row:
                return dict(row._mapping)
            return {}

        except Exception as e:
            logger.sync_error("Database namespace stats error", error=str(e))
            return {}

    async def get_distinct_namespaces(self) -> list[str]:
        """Get all distinct cache namespaces from database."""
        if not self.db_session:
            logger.sync_debug("No database session available for namespaces query")
            return []

        try:
            from sqlalchemy.ext.asyncio import AsyncSession

            query = text("SELECT DISTINCT namespace FROM cache_entries ORDER BY namespace")
            if isinstance(self.db_session, AsyncSession):
                result = await self.db_session.execute(query)
            else:
                result = self.db_session.execute(query)

            namespaces = [row[0] for row in result.fetchall()]
            logger.sync_debug("Found distinct namespaces", count=len(namespaces), namespaces=namespaces)
            return namespaces

        except Exception as e:
            logger.sync_error("Error fetching distinct namespaces", error=str(e))
            return []


# Global cache service instance
cache_service: CacheService | None = None


def get_cache_service(db_session: Session | AsyncSession | None = None) -> CacheService:
    """Get or create the global cache service instance."""
    global cache_service

    if cache_service is None:
        cache_service = CacheService(db_session)

    # Update db_session if provided and different
    if db_session and cache_service.db_session != db_session:
        cache_service.db_session = db_session

    return cache_service


# Convenience functions


async def cached(
    key: str,
    fetch_func: Callable[[], T],
    namespace: str = "default",
    ttl: int | None = None,
    db_session: Session | AsyncSession | None = None,
) -> T:
    """
    Decorator-style function for caching.

    Usage:
        result = await cached("my_key", lambda: expensive_operation(), "my_namespace")
    """
    cache = get_cache_service(db_session)
    return await cache.get_or_set(key, fetch_func, namespace, ttl)


async def cache_get(
    key: str,
    namespace: str = "default",
    default: Any = None,
    db_session: Session | AsyncSession | None = None,
) -> Any:
    """Get a value from cache."""
    cache = get_cache_service(db_session)
    return await cache.get(key, namespace, default)


async def cache_set(
    key: str,
    value: Any,
    namespace: str = "default",
    ttl: int | None = None,
    db_session: Session | AsyncSession | None = None,
) -> bool:
    """Set a value in cache."""
    cache = get_cache_service(db_session)
    return await cache.set(key, value, namespace, ttl)


async def cache_delete(
    key: str, namespace: str = "default", db_session: Session | AsyncSession | None = None
) -> bool:
    """Delete a value from cache."""
    cache = get_cache_service(db_session)
    return await cache.delete(key, namespace)
