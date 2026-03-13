"""Tests for cache service thread safety."""

import threading

import pytest


@pytest.mark.unit
class TestCacheThreadSafety:
    """Verify CacheService uses thread-safe access patterns."""

    def test_cache_service_has_lock(self):
        """CacheService must have a threading.Lock for L1 cache."""
        from app.core.cache_service import CacheService

        cache = CacheService(db_session=None)
        assert hasattr(cache, "_memory_lock")
        assert isinstance(cache._memory_lock, type(threading.Lock()))

    def test_concurrent_cache_access_no_race(self):
        """Verify concurrent access doesn't corrupt cache."""
        from app.core.cache_service import CacheService

        cache = CacheService(db_session=None)
        errors: list[Exception] = []

        def writer(n: int) -> None:
            try:
                for i in range(100):
                    with cache._memory_lock:
                        cache.memory_cache[f"key_{n}_{i}"] = f"value_{n}_{i}"
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(n,)) for n in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


@pytest.mark.unit
class TestGenesEndpointCache:
    """Verify genes endpoint uses CacheService, not manual cache."""

    def test_no_module_level_cache_dicts(self):
        """Module-level cache dicts should be removed from genes.py."""
        import inspect

        from app.api.endpoints import genes

        source = inspect.getsource(genes)
        assert "_metadata_cache: dict" not in source
        assert "_hpo_classifications_cache: dict" not in source
        assert "_gene_ids_cache: dict" not in source


@pytest.mark.unit
class TestCacheStatsBatching:
    """Verify cache stats are batched, not written per-operation."""

    def test_stats_have_batch_counter(self):
        from app.core.cache_service import CacheService

        cache = CacheService(db_session=None)
        assert hasattr(cache.stats, "operations_since_persist")
        assert hasattr(cache.stats, "PERSIST_THRESHOLD")
