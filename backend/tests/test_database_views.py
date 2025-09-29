"""
Comprehensive tests for database views migration.
Tests all components: validators, views, shadow testing, and monitoring.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.core.cache_invalidation import CacheInvalidationManager, ViewDependency
from app.core.database import get_thread_pool_executor
from app.core.feature_flags import FeatureFlags, RolloutStrategy
from app.core.shadow_testing import (
    ComparisonResult,
    ShadowTester,
    BatchShadowTester,
)
from app.core.validators import SQLSafeValidator, QueryParameterValidator
from app.core.view_monitoring import ViewMetricsManager
from app.db.materialized_views import (
    MaterializedViewManager,
    RefreshStrategy,
    MaterializedViewConfig,
)


class TestSQLValidator:
    """Test SQL injection prevention validators."""

    def test_validate_column_safe(self):
        """Test validation of safe column names."""
        # Valid column
        result = SQLSafeValidator.validate_column("approved_symbol", "genes")
        assert result == "approved_symbol"

        # Valid column with table prefix
        result = SQLSafeValidator.validate_column("g.approved_symbol", "genes")
        assert result == "g.approved_symbol"

    def test_validate_column_unsafe(self):
        """Test rejection of unsafe column names."""
        # Invalid column
        with pytest.raises(HTTPException) as exc_info:
            SQLSafeValidator.validate_column("DROP TABLE users", "genes")
        assert exc_info.value.status_code == 400
        assert "Invalid column" in exc_info.value.detail

        # Column not in whitelist
        with pytest.raises(HTTPException) as exc_info:
            SQLSafeValidator.validate_column("password_hash", "users")
        assert exc_info.value.status_code == 400

    def test_validate_sort_order(self):
        """Test sort order validation."""
        # Valid orders
        assert SQLSafeValidator.validate_sort_order("ASC") == "ASC"
        assert SQLSafeValidator.validate_sort_order("desc") == "DESC"

        # Invalid order
        with pytest.raises(HTTPException) as exc_info:
            SQLSafeValidator.validate_sort_order("RANDOM")
        assert exc_info.value.status_code == 400

    def test_validate_limit_offset(self):
        """Test limit and offset validation."""
        # Valid limit
        assert SQLSafeValidator.validate_limit(50) == 50
        assert SQLSafeValidator.validate_limit(2000, max_limit=1000) == 1000  # Capped

        # Invalid limit
        with pytest.raises(HTTPException):
            SQLSafeValidator.validate_limit(-1)

        # Valid offset
        assert SQLSafeValidator.validate_offset(100) == 100

        # Invalid offset
        with pytest.raises(HTTPException):
            SQLSafeValidator.validate_offset(-10)

    def test_sanitize_search_term(self):
        """Test search term sanitization."""
        # SQL special characters
        assert SQLSafeValidator.sanitize_search_term("test%") == "test\\%"
        assert SQLSafeValidator.sanitize_search_term("test_user") == "test\\_user"
        assert SQLSafeValidator.sanitize_search_term("test[0]") == "test\\[0]"

    def test_build_safe_where_clause(self):
        """Test safe WHERE clause building."""
        conditions = {
            "approved_symbol": "BRCA1",
            "is_active": True,
        }

        where_clause, params = SQLSafeValidator.build_safe_where_clause(
            conditions, "genes"
        )

        assert "approved_symbol = :param_approved_symbol" in where_clause
        assert "is_active = :param_is_active" in where_clause
        assert params["param_approved_symbol"] == "BRCA1"
        assert params["param_is_active"] is True


class TestFeatureFlags:
    """Test feature flag system."""

    def test_feature_flag_disabled(self):
        """Test disabled feature flag."""
        flags = FeatureFlags()
        flags.FLAGS["test_feature"] = {"enabled": False}

        assert not flags.is_enabled("test_feature")

    def test_feature_flag_enabled(self):
        """Test enabled feature flag."""
        flags = FeatureFlags()
        flags.FLAGS["test_feature"] = {"enabled": True}

        assert flags.is_enabled("test_feature")

    def test_gradual_rollout(self):
        """Test gradual rollout strategy."""
        flags = FeatureFlags()
        flags.FLAGS["test_feature"] = {
            "enabled": False,
            "strategy": RolloutStrategy.GRADUAL,
            "rollout_steps": {1: 0, 2: 50, 3: 100},
            "current_step": 2,
        }

        # User in rollout percentage
        assert flags.is_enabled("test_feature", user_id=123)  # Hash mod < 50

        # Update step
        flags.update_rollout_step("test_feature", 3)
        assert flags.is_enabled("test_feature", user_id=999)  # 100% rollout

    def test_canary_rollout(self):
        """Test canary deployment strategy."""
        flags = FeatureFlags()
        flags.FLAGS["test_feature"] = {
            "enabled": False,
            "strategy": RolloutStrategy.CANARY,
            "canary_percentage": 10,
        }

        # Some users get feature, some don't (probabilistic)
        enabled_count = sum(
            1 for i in range(1000)
            if flags.is_enabled("test_feature", user_id=i)
        )

        # Should be roughly 10% (with some variance)
        assert 50 < enabled_count < 150  # Allow for variance


class TestShadowTesting:
    """Test shadow testing framework."""

    @pytest.mark.asyncio
    async def test_matching_results(self):
        """Test shadow test with matching results."""
        flags = FeatureFlags()
        tester = ShadowTester(flags)

        def old_impl():
            return {"result": 42, "data": [1, 2, 3]}

        def new_impl():
            return {"result": 42, "data": [1, 2, 3]}

        result = await tester.run_shadow_test(
            endpoint="test",
            old_implementation=old_impl,
            new_implementation=new_impl,
        )

        assert result.results_match
        assert result.comparison_result == ComparisonResult.MATCH

    @pytest.mark.asyncio
    async def test_mismatched_results(self):
        """Test shadow test with mismatched results."""
        flags = FeatureFlags()
        tester = ShadowTester(flags)

        def old_impl():
            return {"result": 42}

        def new_impl():
            return {"result": 43}  # Different value

        result = await tester.run_shadow_test(
            endpoint="test",
            old_implementation=old_impl,
            new_implementation=new_impl,
        )

        assert not result.results_match
        assert result.comparison_result == ComparisonResult.DATA_MISMATCH
        assert result.differences is not None

    @pytest.mark.asyncio
    async def test_performance_regression(self):
        """Test detection of performance regression."""
        flags = FeatureFlags()
        tester = ShadowTester(flags, performance_threshold=1.5)

        def old_impl():
            return {"result": 42}

        def new_impl():
            time.sleep(0.1)  # Simulate slow operation
            return {"result": 42}

        result = await tester.run_shadow_test(
            endpoint="test",
            old_implementation=old_impl,
            new_implementation=new_impl,
        )

        assert not result.results_match  # Marked as mismatch due to regression
        assert result.comparison_result == ComparisonResult.PERFORMANCE_REGRESSION
        assert result.performance_ratio > 1.5

    @pytest.mark.asyncio
    async def test_batch_shadow_testing(self):
        """Test batch shadow testing."""
        flags = FeatureFlags()
        tester = ShadowTester(flags)
        batch_tester = BatchShadowTester(tester)

        test_cases = [
            {
                "endpoint": "test1",
                "old_implementation": lambda: {"result": 1},
                "new_implementation": lambda: {"result": 1},
            },
            {
                "endpoint": "test2",
                "old_implementation": lambda: {"result": 2},
                "new_implementation": lambda: {"result": 3},  # Mismatch
            },
        ]

        results = await batch_tester.run_batch_tests(test_cases)
        report = batch_tester.generate_report(results)

        assert len(results) == 2
        assert report["summary"]["total_tests"] == 2
        assert report["summary"]["matches"] == 1
        assert report["summary"]["mismatches"] == 1
        assert report["summary"]["match_rate"] == 50.0


class TestCacheInvalidation:
    """Test cache invalidation system."""

    @pytest.mark.asyncio
    async def test_table_dependency_tracking(self):
        """Test tracking of table dependencies."""
        cache_service = MagicMock()
        manager = CacheInvalidationManager(cache_service)

        # Check dependencies
        views = manager.get_dependencies_for_table("genes")
        assert "gene_list_detailed" in views
        assert "gene_distribution_analysis" in views

        dep = manager.get_dependencies_for_view("gene_list_detailed")
        assert dep is not None
        assert "genes" in dep.depends_on_tables

    @pytest.mark.asyncio
    async def test_cache_invalidation_for_table(self):
        """Test cache invalidation when table changes."""
        cache_service = MagicMock()
        cache_service.clear_namespace = asyncio.coroutine(lambda x: None)

        manager = CacheInvalidationManager(cache_service)

        # Invalidate caches for genes table
        invalidated = await manager.invalidate_for_table("genes")

        # Should invalidate related namespaces
        assert len(invalidated) > 0
        cache_service.clear_namespace.assert_called()

    @pytest.mark.asyncio
    async def test_register_dynamic_dependency(self):
        """Test registering new view dependencies."""
        cache_service = MagicMock()
        manager = CacheInvalidationManager(cache_service)

        # Register new view
        manager.register_view_dependency(
            view_name="custom_view",
            tables={"genes", "gene_evidence"},
            namespaces={"custom:cache"},
        )

        # Check it was registered
        dep = manager.get_dependencies_for_view("custom_view")
        assert dep is not None
        assert "genes" in dep.depends_on_tables
        assert "custom:cache" in dep.cache_namespaces


class TestMaterializedViews:
    """Test materialized view management."""

    def test_lock_id_generation(self):
        """Test advisory lock ID generation."""
        db = MagicMock()
        manager = MaterializedViewManager(db)

        # Same view should get same lock ID
        lock1 = manager._get_lock_id("test_view")
        lock2 = manager._get_lock_id("test_view")
        assert lock1 == lock2

        # Different views get different IDs
        lock3 = manager._get_lock_id("other_view")
        assert lock1 != lock3

    def test_advisory_lock_acquisition(self):
        """Test advisory lock acquisition."""
        db = MagicMock()
        db.execute.return_value.scalar.return_value = True

        manager = MaterializedViewManager(db)
        acquired = manager._acquire_advisory_lock(12345)

        assert acquired
        db.execute.assert_called()

    def test_materialized_view_refresh(self):
        """Test materialized view refresh."""
        db = MagicMock()
        db.execute.return_value.scalar.return_value = True  # Lock acquired

        manager = MaterializedViewManager(db)

        # Add test view
        manager.MATERIALIZED_VIEWS["test_view"] = MaterializedViewConfig(
            name="test_view",
            definition="SELECT 1",
            indexes=[],
            dependencies=set(),
            refresh_strategy=RefreshStrategy.CONCURRENT,
            refresh_interval_hours=24,
        )

        # Refresh view
        success = manager.refresh_materialized_view("test_view")

        assert success
        # Check that refresh was called
        calls = [str(call) for call in db.execute.call_args_list]
        assert any("REFRESH MATERIALIZED VIEW" in str(call) for call in calls)


class TestThreadPoolSingleton:
    """Test singleton thread pool pattern."""

    def test_singleton_instance(self):
        """Test that thread pool is singleton."""
        pool1 = get_thread_pool_executor()
        pool2 = get_thread_pool_executor()

        assert pool1 is pool2  # Same instance

    def test_thread_pool_execution(self):
        """Test thread pool execution."""
        pool = get_thread_pool_executor()

        def blocking_operation():
            time.sleep(0.01)
            return 42

        # Should not block event loop
        loop = asyncio.new_event_loop()
        future = loop.run_in_executor(pool, blocking_operation)
        result = loop.run_until_complete(future)

        assert result == 42


class TestViewMonitoring:
    """Test view monitoring and metrics."""

    def test_metrics_generation(self):
        """Test Prometheus metrics generation."""
        manager = ViewMetricsManager()

        # Get metrics (should return bytes)
        metrics = manager.get_metrics()
        assert isinstance(metrics, bytes)
        assert len(metrics) > 0

    @pytest.mark.asyncio
    async def test_health_thresholds(self):
        """Test health threshold checking."""
        manager = ViewMetricsManager()

        health = await manager.check_health_thresholds()

        assert "healthy" in health
        assert "checks" in health
        assert "error_rate" in health["checks"]
        assert "p99_latency" in health["checks"]


class TestDatabaseViewQueries:
    """Test actual database view queries."""

    @pytest.fixture
    def db_session(self):
        """Create test database session."""
        # This would be replaced with test database in real tests
        from app.core.database import SessionLocal
        db = SessionLocal()
        yield db
        db.close()

    def test_gene_list_view_structure(self, db_session):
        """Test gene_list_detailed view has expected columns."""
        # Check view exists and has expected structure
        result = db_session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'gene_list_detailed'
            ORDER BY ordinal_position
        """))

        columns = {row[0]: row[1] for row in result}

        # Check key columns exist
        expected_columns = [
            "gene_id",
            "hgnc_id",
            "gene_symbol",
            "total_score",
            "percentage_score",
            "classification",
        ]

        for col in expected_columns:
            assert col in columns, f"Missing column: {col}"


# Integration test combining all components
class TestIntegration:
    """Integration tests for complete flow."""

    @pytest.mark.asyncio
    async def test_complete_migration_flow(self):
        """Test complete migration flow from SQL to views."""
        # 1. Initialize feature flags
        flags = FeatureFlags()
        flags.FLAGS["use_database_views"]["enabled"] = False

        # 2. Create shadow tester
        tester = ShadowTester(flags)

        # 3. Run shadow test
        def old_sql():
            return {"genes": [{"id": 1, "symbol": "BRCA1"}]}

        def new_view():
            return {"genes": [{"id": 1, "symbol": "BRCA1"}]}

        result = await tester.run_shadow_test(
            endpoint="genes",
            old_implementation=old_sql,
            new_implementation=new_view,
        )

        assert result.results_match

        # 4. Enable feature flag
        flags.FLAGS["use_database_views"]["enabled"] = True

        # 5. Verify new implementation is used
        assert flags.is_enabled("use_database_views")

    @pytest.mark.asyncio
    async def test_rollback_on_failure(self):
        """Test rollback when issues detected."""
        flags = FeatureFlags()
        flags.FLAGS["use_database_views"]["enabled"] = True

        # Simulate issue detection
        tester = ShadowTester(flags, performance_threshold=1.0)

        def old_fast():
            return {"result": "fast"}

        def new_slow():
            time.sleep(0.05)  # Slower than threshold
            return {"result": "slow"}

        result = await tester.run_shadow_test(
            endpoint="test",
            old_implementation=old_fast,
            new_implementation=new_slow,
        )

        assert result.comparison_result == ComparisonResult.PERFORMANCE_REGRESSION

        # Should trigger rollback
        flags.FLAGS["use_database_views"]["enabled"] = False
        assert not flags.is_enabled("use_database_views")