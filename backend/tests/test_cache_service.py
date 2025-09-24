"""
Comprehensive tests for the cache service.

Tests L1/L2 cache behavior, TTL expiration, namespace isolation,
and cache statistics.
"""

import asyncio
import time
from unittest.mock import patch

import pytest
from sqlalchemy import text

from app.core.cache_service import CacheService, get_cache_service


@pytest.fixture
def cache_service(db_session):
    """Create a cache service instance for testing."""
    return CacheService(db_session)


@pytest.fixture
def mock_time():
    """Mock time for testing TTL expiration."""
    with patch("time.time") as mock:
        mock.return_value = 1000.0
        yield mock


class TestCacheServiceBasics:
    """Test basic cache operations."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_service):
        """Test basic set and get operations."""
        # Set a value
        success = await cache_service.set("test_key", {"data": "test"}, "test_namespace")
        assert success is True

        # Get the value
        result = await cache_service.get("test_key", "test_namespace")
        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_service):
        """Test getting a non-existent key returns None."""
        result = await cache_service.get("nonexistent", "test_namespace")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_with_default(self, cache_service):
        """Test get with default value."""
        result = await cache_service.get("nonexistent", "test_namespace", default="default_value")
        assert result == "default_value"

    @pytest.mark.asyncio
    async def test_delete_key(self, cache_service):
        """Test deleting a cached key."""
        # Set a value
        await cache_service.set("test_key", "test_value", "test_namespace")

        # Delete it
        success = await cache_service.delete("test_key", "test_namespace")
        assert success is True

        # Verify it's gone
        result = await cache_service.get("test_key", "test_namespace")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, cache_service):
        """Test deleting non-existent key returns False."""
        success = await cache_service.delete("nonexistent", "test_namespace")
        assert success is False


class TestNamespaceIsolation:
    """Test namespace isolation functionality."""

    @pytest.mark.asyncio
    async def test_namespace_isolation(self, cache_service):
        """Test that namespaces are properly isolated."""
        # Set same key in different namespaces
        await cache_service.set("key", "value1", "namespace1")
        await cache_service.set("key", "value2", "namespace2")

        # Verify isolation
        assert await cache_service.get("key", "namespace1") == "value1"
        assert await cache_service.get("key", "namespace2") == "value2"

    @pytest.mark.asyncio
    async def test_clear_namespace(self, cache_service):
        """Test clearing a specific namespace."""
        # Set values in multiple namespaces
        await cache_service.set("key1", "value1", "namespace1")
        await cache_service.set("key2", "value2", "namespace1")
        await cache_service.set("key1", "value3", "namespace2")

        # Clear namespace1
        count = await cache_service.clear_namespace("namespace1")
        assert count >= 2

        # Verify namespace1 is cleared but namespace2 is intact
        assert await cache_service.get("key1", "namespace1") is None
        assert await cache_service.get("key2", "namespace1") is None
        assert await cache_service.get("key1", "namespace2") == "value3"


class TestTTLExpiration:
    """Test TTL and expiration functionality."""

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache_service, mock_time):
        """Test that entries expire after TTL."""
        # Set with 60 second TTL
        await cache_service.set("test_key", "test_value", "test_namespace", ttl=60)

        # Value should exist immediately
        assert await cache_service.get("test_key", "test_namespace") == "test_value"

        # Advance time by 61 seconds
        mock_time.return_value = 1061.0

        # Value should be expired
        result = await cache_service.get("test_key", "test_namespace")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_ttl_persists(self, cache_service, mock_time):
        """Test that entries without TTL persist."""
        # Set without TTL
        await cache_service.set("test_key", "test_value", "test_namespace", ttl=None)

        # Advance time significantly
        mock_time.return_value = 10000.0

        # Value should still exist
        assert await cache_service.get("test_key", "test_namespace") == "test_value"

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, cache_service, mock_time):
        """Test cleanup of expired entries."""
        # Set entries with different TTLs
        await cache_service.set("key1", "value1", "test_namespace", ttl=30)
        await cache_service.set("key2", "value2", "test_namespace", ttl=60)
        await cache_service.set("key3", "value3", "test_namespace", ttl=None)

        # Advance time by 45 seconds
        mock_time.return_value = 1045.0

        # Cleanup expired entries
        count = await cache_service.cleanup_expired()
        assert count >= 1  # key1 should be cleaned up

        # Verify key1 is gone, others remain
        assert await cache_service.get("key1", "test_namespace") is None
        assert await cache_service.get("key2", "test_namespace") == "value2"
        assert await cache_service.get("key3", "test_namespace") == "value3"


class TestL1L2CacheLayers:
    """Test L1 (memory) and L2 (database) cache interaction."""

    @pytest.mark.asyncio
    async def test_l1_cache_hit(self, cache_service):
        """Test that L1 cache is used when available."""
        # Set a value
        await cache_service.set("test_key", "test_value", "test_namespace")

        # First get should hit L2 and populate L1
        result1 = await cache_service.get("test_key", "test_namespace")
        assert result1 == "test_value"

        # Second get should hit L1 (memory cache)
        # We can verify by checking the memory cache directly
        cache_key = "test_namespace:test_key"
        assert cache_key in cache_service._memory_cache

    @pytest.mark.asyncio
    async def test_l1_cache_eviction(self, cache_service):
        """Test L1 cache LRU eviction."""
        # Set max size to a small value for testing
        cache_service._memory_cache.maxsize = 3

        # Add entries to fill cache
        for i in range(4):
            await cache_service.set(f"key{i}", f"value{i}", "test_namespace")

        # The first key should be evicted from L1 but still in L2
        assert "test_namespace:key0" not in cache_service._memory_cache

        # But it should still be retrievable from L2
        result = await cache_service.get("key0", "test_namespace")
        assert result == "value0"

    @pytest.mark.asyncio
    async def test_l2_persistence(self, cache_service, db_session):
        """Test that L2 cache persists in database."""
        # Set a value
        await cache_service.set("test_key", {"complex": "data"}, "test_namespace")

        # Verify it's in the database
        result = db_session.execute(
            text("SELECT value FROM cache_entries WHERE cache_key = :key"),
            {"key": "test_namespace:test_key"}
        ).fetchone()

        assert result is not None
        # The value should be JSON serialized in the database


class TestCacheStatistics:
    """Test cache statistics functionality."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, cache_service):
        """Test getting cache statistics."""
        # Set some values
        await cache_service.set("key1", "value1", "namespace1")
        await cache_service.set("key2", "value2", "namespace1")
        await cache_service.set("key3", "value3", "namespace2")

        # Get overall statistics
        stats = await cache_service.get_statistics()
        assert "total_entries" in stats
        assert "namespaces" in stats
        assert stats["total_entries"] >= 3

    @pytest.mark.asyncio
    async def test_namespace_statistics(self, cache_service):
        """Test getting namespace-specific statistics."""
        # Set values with different TTLs
        await cache_service.set("key1", "value1", "test_namespace", ttl=60)
        await cache_service.set("key2", "value2", "test_namespace", ttl=None)

        # Get namespace statistics
        stats = await cache_service.get_namespace_statistics("test_namespace")
        assert stats["namespace"] == "test_namespace"
        assert stats["entry_count"] >= 2
        assert "memory_entries" in stats
        assert "db_entries" in stats


class TestAnnotationCompatibility:
    """Test annotation-specific compatibility methods."""

    @pytest.mark.asyncio
    async def test_get_annotation(self, cache_service):
        """Test get_annotation compatibility method."""
        # Set an annotation
        await cache_service.set("1:hgnc", {"gene": "data"}, "annotations")

        # Get using compatibility method
        result = await cache_service.get_annotation(1, "hgnc")
        assert result == {"gene": "data"}

    @pytest.mark.asyncio
    async def test_set_annotation(self, cache_service):
        """Test set_annotation compatibility method."""
        # Set using compatibility method
        success = await cache_service.set_annotation(
            1, {"gene": "data"}, "hgnc", ttl=3600
        )
        assert success is True

        # Verify it's cached
        result = await cache_service.get("1:hgnc", "annotations")
        assert result == {"gene": "data"}

    @pytest.mark.asyncio
    async def test_invalidate_gene(self, cache_service):
        """Test invalidating all cache for a gene."""
        # Set data for a gene in multiple namespaces
        await cache_service.set("1:all", {"all": "data"}, "annotations")
        await cache_service.set("1:hgnc", {"hgnc": "data"}, "hgnc")
        await cache_service.set("summary:1", {"summary": "data"}, "annotations")

        # Invalidate gene
        count = await cache_service.invalidate_gene(1)
        assert count >= 1

        # Verify data is cleared
        assert await cache_service.get("1:all", "annotations") is None
        assert await cache_service.get("1:hgnc", "hgnc") is None

    @pytest.mark.asyncio
    async def test_get_set_summary(self, cache_service):
        """Test summary cache methods."""
        # Set summary
        success = await cache_service.set_summary(1, {"summary": "data"}, ttl=7200)
        assert success is True

        # Get summary
        result = await cache_service.get_summary(1)
        assert result == {"summary": "data"}


class TestConcurrency:
    """Test concurrent cache operations."""

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, cache_service):
        """Test concurrent write operations."""
        async def write_task(i):
            await cache_service.set(f"key{i}", f"value{i}", "test_namespace")
            return i

        # Run concurrent writes
        tasks = [write_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10

        # Verify all values are cached
        for i in range(10):
            result = await cache_service.get(f"key{i}", "test_namespace")
            assert result == f"value{i}"

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, cache_service):
        """Test concurrent read operations."""
        # Set initial values
        for i in range(5):
            await cache_service.set(f"key{i}", f"value{i}", "test_namespace")

        async def read_task(i):
            return await cache_service.get(f"key{i}", "test_namespace")

        # Run concurrent reads
        tasks = [read_task(i % 5) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # Verify all reads succeeded
        for i, result in enumerate(results):
            expected = f"value{i % 5}"
            assert result == expected


class TestErrorHandling:
    """Test error handling in cache operations."""

    @pytest.mark.asyncio
    async def test_invalid_json_handling(self, cache_service):
        """Test handling of non-JSON-serializable data."""
        # Try to cache a non-serializable object
        class NonSerializable:
            pass

        obj = NonSerializable()

        # This should handle the error gracefully
        with pytest.raises(TypeError):
            await cache_service.set("key", obj, "namespace")

    @pytest.mark.asyncio
    async def test_database_error_handling(self, cache_service):
        """Test handling of database errors."""
        # Mock database error
        with patch.object(cache_service._db, 'execute', side_effect=Exception("DB Error")):
            # Should handle error gracefully and return None
            result = await cache_service.get("key", "namespace")
            assert result is None


class TestCacheServiceFactory:
    """Test the cache service factory function."""

    def test_get_cache_service_with_session(self, db_session):
        """Test getting cache service with session."""
        service = get_cache_service(db_session)
        assert isinstance(service, CacheService)
        assert service._db == db_session

    def test_get_cache_service_without_session(self):
        """Test getting cache service without session."""
        service = get_cache_service(None)
        assert isinstance(service, CacheService)
        # Should create its own session or use a default one
        assert service is not None

    def test_cache_service_singleton(self, db_session):
        """Test that same session returns same service instance."""
        service1 = get_cache_service(db_session)
        service2 = get_cache_service(db_session)
        # Should be the same instance for the same session
        assert service1 is service2


@pytest.mark.asyncio
class TestPerformance:
    """Test cache performance characteristics."""

    async def test_bulk_operations_performance(self, cache_service):
        """Test performance of bulk operations."""
        start_time = time.time()

        # Bulk write
        for i in range(100):
            await cache_service.set(f"key{i}", f"value{i}", "perf_test")

        write_time = time.time() - start_time

        # Bulk read
        start_time = time.time()
        for i in range(100):
            await cache_service.get(f"key{i}", "perf_test")

        read_time = time.time() - start_time

        # Performance assertions
        assert write_time < 5.0  # Should complete within 5 seconds
        assert read_time < 1.0   # Reads should be faster

    async def test_memory_cache_performance(self, cache_service):
        """Test L1 cache performance advantage."""
        # Warm up L1 cache
        await cache_service.set("test_key", "test_value", "test_namespace")
        await cache_service.get("test_key", "test_namespace")

        # Time L1 hit (should be very fast)
        start_time = time.time()
        for _ in range(1000):
            await cache_service.get("test_key", "test_namespace")
        l1_time = time.time() - start_time

        # Clear L1 cache
        cache_service._memory_cache.clear()

        # Time L2 hit (slower due to DB access)
        start_time = time.time()
        for _ in range(10):  # Fewer iterations for L2
            await cache_service.get("test_key", "test_namespace")
            cache_service._memory_cache.clear()  # Force L2 hit
        l2_time = (time.time() - start_time) / 100  # Normalize

        # L1 should be significantly faster
        assert l1_time < l2_time
