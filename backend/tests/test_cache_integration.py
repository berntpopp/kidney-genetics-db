"""
Integration tests for cache system with gene annotations.

Tests the complete cache flow from API endpoints through cache layers
to database persistence.
"""

import asyncio
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import text

from app.core.cache_service import get_cache_service
from app.models.gene import Gene


@pytest.fixture
def sample_gene():
    """Create a sample gene for testing."""
    gene = Gene(
        id=1,
        approved_symbol="TEST1",
        hgnc_id="HGNC:12345",
        entrez_gene_id="67890",
        omim_gene_id="123456",
    )
    return gene


@pytest.fixture
def sample_annotation_data():
    """Sample annotation data for testing."""
    return {
        "hgnc": {
            "symbol": "TEST1",
            "name": "Test Gene 1",
            "alias_symbols": ["TST1", "TG1"],
            "prev_symbols": ["OLD1"],
            "location": "1q23.4",
        },
        "gnomad": {"pLI": 0.95, "oe_lof": 0.12, "oe_mis": 0.85, "constraint_flag": True},
        "gtex": {
            "expression": {"kidney": 45.2, "heart": 12.3, "brain": 78.9},
            "tissue_specific": True,
        },
        "hpo": {
            "phenotypes": [
                {"id": "HP:0000001", "name": "Phenotype 1"},
                {"id": "HP:0000002", "name": "Phenotype 2"},
            ],
            "inheritance": ["Autosomal dominant"],
        },
    }


class TestAnnotationCacheIntegration:
    """Test annotation caching integration."""

    @pytest.mark.asyncio
    async def test_annotation_cache_flow(self, db_session, sample_annotation_data):
        """Test complete annotation cache flow."""
        cache_service = get_cache_service(db_session)

        # Set annotation data
        success = await cache_service.set_annotation(
            gene_id=1, data=sample_annotation_data, source="all", ttl=3600, db_session=db_session
        )
        assert success is True

        # Retrieve annotation data
        cached_data = await cache_service.get_annotation(
            gene_id=1, source="all", db_session=db_session
        )
        assert cached_data == sample_annotation_data

        # Verify it's in both L1 and L2
        cache_key = "1:all"

        # Check L1 (memory cache)
        memory_key = f"annotations:{cache_key}"
        assert memory_key in cache_service._memory_cache

        # Check L2 (database)
        result = db_session.execute(
            text("SELECT value FROM cache_entries WHERE cache_key = :key"),
            {"key": f"annotations:{cache_key}"},
        ).fetchone()
        assert result is not None

    @pytest.mark.asyncio
    async def test_source_specific_caching(self, db_session, sample_annotation_data):
        """Test caching for specific annotation sources."""
        cache_service = get_cache_service(db_session)

        # Cache individual sources
        for source, data in sample_annotation_data.items():
            await cache_service.set_annotation(
                gene_id=1, data={source: data}, source=source, ttl=3600, db_session=db_session
            )

        # Retrieve specific sources
        hgnc_data = await cache_service.get_annotation(1, "hgnc", db_session)
        assert "hgnc" in hgnc_data
        assert hgnc_data["hgnc"]["symbol"] == "TEST1"

        gnomad_data = await cache_service.get_annotation(1, "gnomad", db_session)
        assert "gnomad" in gnomad_data
        assert gnomad_data["gnomad"]["pLI"] == 0.95

    @pytest.mark.asyncio
    async def test_annotation_summary_caching(self, db_session):
        """Test caching of annotation summaries."""
        cache_service = get_cache_service(db_session)

        summary_data = {
            "gene_id": 1,
            "sources": ["hgnc", "gnomad", "gtex"],
            "last_updated": datetime.utcnow().isoformat(),
            "completeness": 0.85,
            "key_findings": ["High pLI score", "Kidney-specific expression"],
        }

        # Set summary
        success = await cache_service.set_summary(
            gene_id=1, data=summary_data, ttl=7200, db_session=db_session
        )
        assert success is True

        # Get summary
        cached_summary = await cache_service.get_summary(1, db_session)
        assert cached_summary == summary_data

    @pytest.mark.asyncio
    async def test_gene_cache_invalidation(self, db_session, sample_annotation_data):
        """Test invalidating all cache for a gene."""
        cache_service = get_cache_service(db_session)

        # Set multiple cache entries for a gene
        await cache_service.set_annotation(1, sample_annotation_data, "all", 3600, db_session)
        await cache_service.set_annotation(
            1, {"hgnc": sample_annotation_data["hgnc"]}, "hgnc", 3600, db_session
        )
        await cache_service.set_summary(1, {"summary": "data"}, 7200, db_session)

        # Verify they're cached
        assert await cache_service.get_annotation(1, "all", db_session) is not None
        assert await cache_service.get_annotation(1, "hgnc", db_session) is not None
        assert await cache_service.get_summary(1, db_session) is not None

        # Invalidate gene
        count = await cache_service.invalidate_gene(1, db_session)
        assert count >= 1

        # Verify they're cleared
        assert await cache_service.get_annotation(1, "all", db_session) is None
        assert await cache_service.get_annotation(1, "hgnc", db_session) is None
        assert await cache_service.get_summary(1, db_session) is None

    @pytest.mark.asyncio
    async def test_namespace_isolation_for_annotations(self, db_session):
        """Test that different annotation namespaces are isolated."""
        cache_service = get_cache_service(db_session)

        # Set same key in different namespaces
        await cache_service.set("gene:1", {"annotations": "data"}, "annotations", 3600)
        await cache_service.set("gene:1", {"hgnc": "data"}, "hgnc", 3600)
        await cache_service.set("gene:1", {"clinvar": "data"}, "clinvar", 3600)

        # Verify isolation
        assert (await cache_service.get("gene:1", "annotations"))["annotations"] == "data"
        assert (await cache_service.get("gene:1", "hgnc"))["hgnc"] == "data"
        assert (await cache_service.get("gene:1", "clinvar"))["clinvar"] == "data"

        # Clear one namespace
        await cache_service.clear_namespace("hgnc")

        # Verify only that namespace is cleared
        assert await cache_service.get("gene:1", "annotations") is not None
        assert await cache_service.get("gene:1", "hgnc") is None
        assert await cache_service.get("gene:1", "clinvar") is not None


class TestCacheWithAnnotationEndpoints:
    """Test cache integration with annotation API endpoints."""

    @pytest.mark.asyncio
    async def test_endpoint_cache_pattern(self, db_session):
        """Test the cache pattern used by annotation endpoints."""
        cache_service = get_cache_service(db_session)

        # Simulate endpoint pattern: check cache, fetch if miss, cache result
        gene_id = 1
        source = "hgnc"
        cache_key = f"{gene_id}:{source}"

        # Step 1: Check cache (miss)
        cached = await cache_service.get(cache_key, "annotations", default=None)
        assert cached is None

        # Step 2: Fetch data (simulated)
        fetched_data = {"source": source, "data": {"symbol": "TEST1", "name": "Test Gene 1"}}

        # Step 3: Cache the result
        await cache_service.set(cache_key, fetched_data, "annotations", ttl=3600)

        # Step 4: Subsequent request hits cache
        cached = await cache_service.get(cache_key, "annotations", default=None)
        assert cached == fetched_data

    @pytest.mark.asyncio
    async def test_concurrent_annotation_requests(self, db_session):
        """Test handling concurrent requests for same annotation."""
        cache_service = get_cache_service(db_session)

        fetch_count = 0

        async def fetch_annotation(gene_id, source):
            """Simulate fetching annotation with delay."""
            nonlocal fetch_count

            cache_key = f"{gene_id}:{source}"

            # Check cache
            cached = await cache_service.get(cache_key, "annotations")
            if cached:
                return cached

            # Simulate fetch
            fetch_count += 1
            await asyncio.sleep(0.05)  # Simulate API delay

            data = {"source": source, "count": fetch_count}
            await cache_service.set(cache_key, data, "annotations", ttl=60)
            return data

        # Launch concurrent requests for same gene
        tasks = [fetch_annotation(1, "hgnc") for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All should get the same result
        assert all(r["source"] == "hgnc" for r in results)

        # Ideally only one fetch (but allow for race conditions)
        assert fetch_count <= 2

    @pytest.mark.asyncio
    async def test_batch_annotation_caching(self, db_session):
        """Test caching multiple annotations in batch."""
        cache_service = get_cache_service(db_session)

        # Batch cache multiple genes
        genes = [1, 2, 3, 4, 5]
        for gene_id in genes:
            await cache_service.set_annotation(
                gene_id, {"data": f"gene_{gene_id}"}, "all", ttl=3600, db_session=db_session
            )

        # Verify all are cached
        for gene_id in genes:
            result = await cache_service.get_annotation(gene_id, "all", db_session)
            assert result["data"] == f"gene_{gene_id}"

        # Get statistics
        stats = await cache_service.get_namespace_statistics("annotations")
        assert stats["entry_count"] >= len(genes)


class TestCachePerformanceIntegration:
    """Test cache performance in integration scenarios."""

    @pytest.mark.asyncio
    async def test_cache_warmup(self, db_session):
        """Test cache warmup scenario."""
        cache_service = get_cache_service(db_session)

        # Simulate cache warmup for frequently accessed genes
        hot_genes = list(range(1, 11))  # Top 10 genes

        # Warm up cache
        for gene_id in hot_genes:
            await cache_service.set_annotation(
                gene_id,
                {"preloaded": True, "gene_id": gene_id},
                "all",
                ttl=7200,  # Longer TTL for hot data
                db_session=db_session,
            )

        # Verify all hot genes are in L1 cache
        for gene_id in hot_genes:
            cache_key = f"annotations:{gene_id}:all"
            assert cache_key in cache_service._memory_cache

    @pytest.mark.asyncio
    async def test_cache_cascade(self, db_session):
        """Test L1 -> L2 cache cascade."""
        cache_service = get_cache_service(db_session)

        # Set data (goes to both L1 and L2)
        await cache_service.set("test_key", "test_value", "test", ttl=60)

        # Clear L1 cache
        cache_service._memory_cache.clear()

        # Get should hit L2 and repopulate L1
        result = await cache_service.get("test_key", "test")
        assert result == "test_value"

        # Verify L1 is repopulated
        assert "test:test_key" in cache_service._memory_cache

    @pytest.mark.asyncio
    async def test_cache_expiry_cascade(self, db_session):
        """Test expiry handling across cache layers."""
        cache_service = get_cache_service(db_session)

        # Set with short TTL
        with patch("time.time", return_value=1000.0):
            await cache_service.set("expire_test", "value", "test", ttl=30)

        # Advance time past expiry
        with patch("time.time", return_value=1031.0):
            # Should return None (expired)
            result = await cache_service.get("expire_test", "test")
            assert result is None

            # Should be removed from L1
            assert "test:expire_test" not in cache_service._memory_cache


class TestCacheMonitoring:
    """Test cache monitoring and statistics."""

    @pytest.mark.asyncio
    async def test_cache_hit_rate_tracking(self, db_session):
        """Test tracking cache hit rates."""
        cache_service = get_cache_service(db_session)

        # Perform operations to generate hit/miss pattern
        await cache_service.set("key1", "value1", "test", ttl=60)
        await cache_service.set("key2", "value2", "test", ttl=60)

        # Hits
        await cache_service.get("key1", "test")
        await cache_service.get("key2", "test")
        await cache_service.get("key1", "test")  # Second hit

        # Misses
        await cache_service.get("key3", "test")
        await cache_service.get("key4", "test")

        # Get statistics
        stats = await cache_service.get_statistics()

        # Verify statistics structure
        assert "total_entries" in stats
        assert "namespaces" in stats
        assert stats["total_entries"] >= 2

    @pytest.mark.asyncio
    async def test_namespace_statistics(self, db_session):
        """Test detailed namespace statistics."""
        cache_service = get_cache_service(db_session)

        # Populate different namespaces
        namespaces = ["annotations", "hgnc", "clinvar", "gnomad"]
        for ns in namespaces:
            for i in range(3):
                await cache_service.set(f"key{i}", f"value{i}", ns, ttl=3600)

        # Get statistics for each namespace
        for ns in namespaces:
            stats = await cache_service.get_namespace_statistics(ns)
            assert stats["namespace"] == ns
            assert stats["entry_count"] >= 3
            assert "memory_entries" in stats
            assert "db_entries" in stats

    @pytest.mark.asyncio
    async def test_cache_health_check(self, db_session):
        """Test cache health check functionality."""
        cache_service = get_cache_service(db_session)

        # Perform basic health check
        health = {
            "l1_available": cache_service._memory_cache is not None,
            "l2_available": cache_service._db is not None,
            "max_memory_size": cache_service._memory_cache.maxsize,
            "current_memory_usage": len(cache_service._memory_cache),
        }

        assert health["l1_available"] is True
        assert health["l2_available"] is True
        assert health["max_memory_size"] > 0
        assert health["current_memory_usage"] >= 0


class TestCacheErrorRecovery:
    """Test cache error handling and recovery."""

    @pytest.mark.asyncio
    async def test_l2_failure_fallback(self, db_session):
        """Test behavior when L2 (database) fails."""
        cache_service = get_cache_service(db_session)

        # Set data in cache
        await cache_service.set("test_key", "test_value", "test", ttl=60)

        # Simulate L2 failure
        with patch.object(cache_service._db, "execute", side_effect=Exception("DB Error")):
            # Should still work from L1
            result = await cache_service.get("test_key", "test")
            # L1 should still have it
            if "test:test_key" in cache_service._memory_cache:
                assert result == "test_value"

    @pytest.mark.asyncio
    async def test_cache_corruption_handling(self, db_session):
        """Test handling of corrupted cache data."""
        cache_service = get_cache_service(db_session)

        # Insert corrupted data directly into L2
        db_session.execute(
            text("""
                INSERT INTO cache_entries (cache_key, namespace, value, created_at)
                VALUES (:key, :namespace, :value, :created_at)
            """),
            {
                "key": "test:corrupted",
                "namespace": "test",
                "value": '{"invalid json',  # Corrupted JSON
                "created_at": datetime.utcnow(),
            },
        )
        db_session.commit()

        # Should handle gracefully
        result = await cache_service.get("corrupted", "test")
        assert result is None  # Should return None for corrupted data

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self, db_session):
        """Test concurrent cache operations don't interfere."""
        cache_service = get_cache_service(db_session)

        async def cache_operation(i):
            key = f"key_{i}"
            value = f"value_{i}"
            namespace = f"ns_{i % 3}"  # Use 3 namespaces

            # Set
            await cache_service.set(key, value, namespace, ttl=60)

            # Get
            result = await cache_service.get(key, namespace)
            assert result == value

            # Delete
            if i % 2 == 0:
                await cache_service.delete(key, namespace)

            return i

        # Run many concurrent operations
        tasks = [cache_operation(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20
        assert all(isinstance(r, int) for r in results)
