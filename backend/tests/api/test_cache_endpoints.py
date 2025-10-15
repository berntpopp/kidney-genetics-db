"""
Integration tests for cache endpoints.

Tests cover:
1. Namespace stats with empty namespaces (Fix #2)
2. Namespace stats with populated data
3. Cache warming functionality
4. Cache health checks
5. Regression tests for existing functionality
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.orm import Session


@pytest.mark.integration
class TestCacheNamespaceStats:
    """Test cache namespace statistics endpoints."""

    @pytest.mark.asyncio
    async def test_namespace_stats_empty_namespace(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """
        Test that empty namespaces return zeros instead of 500 error.

        This is the primary regression test for Fix #2:
        Before fix: 500 Internal Server Error with ValidationError
        After fix: 200 OK with all zeros
        """
        # Call endpoint for a namespace that has no cache entries
        response = await admin_client.get("/api/admin/cache/stats/hgnc")

        # Should return 200, not 500
        assert response.status_code == 200

        stats = response.json()

        # All stats should be zero for empty namespace
        assert stats["namespace"] == "hgnc"
        assert stats["total_entries"] == 0
        assert stats["active_entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["total_accesses"] == 0
        assert stats["avg_accesses"] == 0.0
        assert stats["total_size_bytes"] == 0
        assert stats["last_access_time"] is None
        assert stats["oldest_entry"] is None
        assert stats["newest_entry"] is None

    @pytest.mark.asyncio
    async def test_namespace_stats_with_data(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """Test namespace stats with actual cache data."""
        # Insert test cache entries
        now = datetime.now(timezone.utc)
        db_session.execute(
            text("""
                INSERT INTO cache_entries
                (cache_key, namespace, value, data, created_at, updated_at, access_count, last_accessed_at, size_bytes)
                VALUES
                ('test:1', 'clinvar', '{"data": "value1"}'::jsonb, '{"info": "data1"}'::jsonb, :now, :now, 5, :now, 100),
                ('test:2', 'clinvar', '{"data": "value2"}'::jsonb, '{"info": "data2"}'::jsonb, :now, :now, 10, :now, 200),
                ('test:3', 'clinvar', '{"data": "value3"}'::jsonb, '{"info": "data3"}'::jsonb, :now, :now, 15, :now, 300)
            """),
            {"now": now}
        )
        db_session.commit()

        # Get stats for namespace with data
        response = await admin_client.get("/api/admin/cache/stats/clinvar")

        assert response.status_code == 200
        stats = response.json()

        # Verify stats are populated
        assert stats["namespace"] == "clinvar"
        assert stats["total_entries"] == 3
        assert stats["active_entries"] == 3
        assert stats["expired_entries"] == 0
        assert stats["total_accesses"] == 30  # 5 + 10 + 15
        assert stats["avg_accesses"] == 10.0  # 30 / 3
        assert stats["total_size_bytes"] == 600  # 100 + 200 + 300

    @pytest.mark.asyncio
    async def test_namespace_stats_with_expired_entries(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """Test namespace stats correctly separates active and expired entries."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Insert mixed active and expired entries
        db_session.execute(
            text("""
                INSERT INTO cache_entries
                (cache_key, namespace, value, data, expires_at, created_at, updated_at, access_count, last_accessed_at, size_bytes)
                VALUES
                ('active:1', 'hpo', '{"data": "active1"}'::jsonb, '{"info": "active1"}'::jsonb, :tomorrow, :now, :now, 5, :now, 100),
                ('expired:1', 'hpo', '{"data": "expired1"}'::jsonb, '{"info": "expired1"}'::jsonb, :yesterday, :now, :now, 10, :now, 200),
                ('expired:2', 'hpo', '{"data": "expired2"}'::jsonb, '{"info": "expired2"}'::jsonb, :yesterday, :now, :now, 15, :now, 300)
            """),
            {"now": now, "yesterday": yesterday, "tomorrow": tomorrow}
        )
        db_session.commit()

        response = await admin_client.get("/api/admin/cache/stats/hpo")

        assert response.status_code == 200
        stats = response.json()

        assert stats["namespace"] == "hpo"
        assert stats["total_entries"] == 3
        assert stats["active_entries"] == 1
        assert stats["expired_entries"] == 2


@pytest.mark.integration
class TestCacheHealthCheck:
    """Test cache health check endpoints."""

    @pytest.mark.asyncio
    async def test_cache_health_check(self, admin_client: AsyncClient, db_session: Session):
        """Test that cache health check works correctly."""
        response = await admin_client.get("/api/admin/cache/health")

        assert response.status_code == 200
        health = response.json()

        # Health check should return status and stats
        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]

        # Should include L1 and L2 cache info
        if "l1_cache" in health:
            assert "enabled" in health["l1_cache"]

        if "l2_cache" in health:
            assert "enabled" in health["l2_cache"]

    @pytest.mark.asyncio
    async def test_cache_health_all_namespaces(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """Test that health check returns data for all namespaces."""
        # Insert data in multiple namespaces
        now = datetime.now(timezone.utc)
        db_session.execute(
            text("""
                INSERT INTO cache_entries
                (cache_key, namespace, value, created_at, updated_at, access_count, last_accessed_at, size_bytes)
                VALUES
                ('test:1', 'clinvar', '{"data": "v1"}'::jsonb, :now, :now, 1, :now, 100),
                ('test:2', 'hgnc', '{"data": "v2"}'::jsonb, :now, :now, 1, :now, 100),
                ('test:3', 'pubtator', '{"data": "v3"}'::jsonb, :now, :now, 1, :now, 100)
            """),
            {"now": now}
        )
        db_session.commit()

        response = await admin_client.get("/api/admin/cache/health")

        assert response.status_code == 200
        health = response.json()

        # Should report on multiple namespaces
        if "namespace_stats" in health:
            assert len(health["namespace_stats"]) >= 3


@pytest.mark.integration
class TestCacheWarm:
    """Test cache warming functionality."""

    @pytest.mark.asyncio
    async def test_cache_warm_empty_sources(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """Test cache warming with empty source list returns proper response."""
        response = await admin_client.post(
            "/api/admin/cache/warm",
            json={"sources": []}
        )

        # Should accept empty list but return appropriate message
        # Either 200 with no work done, or 400 for validation
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            result = response.json()
            # If accepted, should indicate no sources were warmed
            if "sources_warmed" in result:
                assert result["sources_warmed"] == 0

    @pytest.mark.asyncio
    async def test_cache_warm_invalid_source(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """Test that invalid source names are handled gracefully."""
        response = await admin_client.post(
            "/api/admin/cache/warm",
            json={"sources": ["invalid_source_name_12345"]}
        )

        # Should either skip invalid sources or return validation error
        # Both are acceptable responses
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            result = response.json()
            # Should indicate which sources were invalid
            if "skipped_sources" in result:
                assert "invalid_source_name_12345" in result["skipped_sources"]

    @pytest.mark.asyncio
    async def test_cache_warm_valid_source(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """Test cache warming with valid source name."""
        response = await admin_client.post(
            "/api/admin/cache/warm",
            json={"sources": ["hgnc"]}
        )

        # Should accept valid source
        # May return 200 or 202 (accepted for async processing)
        assert response.status_code in [200, 202]


@pytest.mark.integration
class TestCacheClear:
    """Test cache clearing functionality."""

    @pytest.mark.asyncio
    async def test_clear_namespace(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """Test clearing specific namespace."""
        # Insert test data
        now = datetime.now(timezone.utc)
        db_session.execute(
            text("""
                INSERT INTO cache_entries
                (cache_key, namespace, value, created_at, updated_at)
                VALUES
                ('test:1', 'gencc', '{"data": "v1"}'::jsonb, :now, :now),
                ('test:2', 'gencc', '{"data": "v2"}'::jsonb, :now, :now),
                ('test:3', 'panelapp', '{"data": "v3"}'::jsonb, :now, :now)
            """),
            {"now": now}
        )
        db_session.commit()

        # Clear one namespace
        response = await admin_client.post("/api/admin/cache/clear/gencc")

        assert response.status_code == 200

        # Verify namespace was cleared
        result = db_session.execute(
            text("SELECT COUNT(*) FROM cache_entries WHERE namespace = 'gencc'")
        )
        count = result.scalar()
        assert count == 0

        # Verify other namespace still has data
        result = db_session.execute(
            text("SELECT COUNT(*) FROM cache_entries WHERE namespace = 'panelapp'")
        )
        count = result.scalar()
        assert count == 1

    @pytest.mark.asyncio
    async def test_clear_all_cache(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """Test clearing all cache."""
        # Insert test data
        now = datetime.now(timezone.utc)
        db_session.execute(
            text("""
                INSERT INTO cache_entries
                (cache_key, namespace, value, created_at, updated_at)
                VALUES
                ('test:1', 'clingen', '{"data": "v1"}'::jsonb, :now, :now),
                ('test:2', 'http', '{"data": "v2"}'::jsonb, :now, :now)
            """),
            {"now": now}
        )
        db_session.commit()

        # Clear all cache
        response = await admin_client.post("/api/admin/cache/clear")

        assert response.status_code == 200

        # Verify all cache entries were cleared
        result = db_session.execute(text("SELECT COUNT(*) FROM cache_entries"))
        count = result.scalar()
        assert count == 0


@pytest.mark.integration
class TestCacheRegressions:
    """Regression tests to ensure existing functionality still works."""

    @pytest.mark.asyncio
    async def test_existing_cache_operations_still_work(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """
        Comprehensive regression test ensuring all cache operations work.
        This protects against breaking changes from the namespace stats fix.
        """
        # 1. Health check should work
        response = await admin_client.get("/api/admin/cache/health")
        assert response.status_code == 200

        # 2. Empty namespace stats should return zeros (not error)
        response = await admin_client.get("/api/admin/cache/stats/files")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_entries"] == 0

        # 3. Can still insert and retrieve cache entries
        now = datetime.now(timezone.utc)
        db_session.execute(
            text("""
                INSERT INTO cache_entries
                (cache_key, namespace, value, created_at, updated_at, access_count, size_bytes)
                VALUES ('regression:test', 'files', '{"test": "data"}'::jsonb, :now, :now, 1, 50)
            """),
            {"now": now}
        )
        db_session.commit()

        # 4. Stats should reflect the new entry
        response = await admin_client.get("/api/admin/cache/stats/files")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_entries"] == 1
        assert stats["active_entries"] == 1

        # 5. Clear should work
        response = await admin_client.post("/api/admin/cache/clear/files")
        assert response.status_code == 200

        # 6. Stats should be back to zero
        response = await admin_client.get("/api/admin/cache/stats/files")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_all_known_namespaces_return_valid_stats(
        self, admin_client: AsyncClient, db_session: Session
    ):
        """
        Test that all known cache namespaces return valid stats (not 500 errors).
        This was the primary symptom of the bug - 8 namespaces returned 500.
        """
        known_namespaces = [
            "hgnc", "pubtator", "gencc", "panelapp",
            "hpo", "clingen", "http", "files", "clinvar"
        ]

        for namespace in known_namespaces:
            response = await admin_client.get(f"/api/admin/cache/stats/{namespace}")

            # All should return 200, not 500
            assert response.status_code == 200, \
                f"Namespace {namespace} returned {response.status_code}"

            stats = response.json()

            # Should have valid structure
            assert "namespace" in stats
            assert stats["namespace"] == namespace
            assert "total_entries" in stats
            assert isinstance(stats["total_entries"], int)
            assert stats["total_entries"] >= 0
