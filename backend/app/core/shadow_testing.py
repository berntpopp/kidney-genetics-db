"""
Shadow testing framework for comparing old and new implementations.
Enables safe migration with real-world validation.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from deepdiff import DeepDiff

from app.core.feature_flags import FeatureFlags
from app.core.logging import get_logger
from app.core.view_monitoring import (
    shadow_test_duration,
    shadow_test_mismatches,
    shadow_test_total,
    track_shadow_test,
)

logger = get_logger(__name__)


class ComparisonResult(Enum):
    """Result of shadow test comparison."""

    MATCH = "match"
    DATA_MISMATCH = "data_mismatch"
    PERFORMANCE_REGRESSION = "performance_regression"
    ERROR_OLD = "error_old"
    ERROR_NEW = "error_new"
    ERROR_BOTH = "error_both"


@dataclass
class ShadowTestResult:
    """Result of a shadow test execution."""

    endpoint: str
    results_match: bool
    comparison_result: ComparisonResult
    old_result: Any
    new_result: Any
    old_duration_ms: float
    new_duration_ms: float
    performance_ratio: float  # new/old duration
    differences: dict | None = None
    error: str | None = None
    metadata: dict = None


class ShadowTester:
    """
    Framework for shadow testing during migration.

    Runs both old and new implementations, compares results,
    and tracks metrics for decision making.
    """

    def __init__(self, feature_flags: FeatureFlags, performance_threshold: float = 1.5):
        """
        Initialize shadow tester.

        Args:
            feature_flags: Feature flag system for controlling rollout
            performance_threshold: Max acceptable performance ratio (new/old)
        """
        self.feature_flags = feature_flags
        self.performance_threshold = performance_threshold

    async def run_shadow_test(
        self,
        endpoint: str,
        old_implementation: Callable,
        new_implementation: Callable,
        args: tuple = (),
        kwargs: dict = None,
        comparison_fields: list[str] | None = None,
        metadata: dict | None = None,
    ) -> ShadowTestResult:
        """
        Run both implementations and compare results.

        Args:
            endpoint: Name of the endpoint being tested
            old_implementation: Original implementation
            new_implementation: New implementation using views
            args: Positional arguments for both implementations
            kwargs: Keyword arguments for both implementations
            comparison_fields: Specific fields to compare (None = all)
            metadata: Additional metadata for logging

        Returns:
            ShadowTestResult with comparison details
        """
        kwargs = kwargs or {}
        metadata = metadata or {}

        # Initialize result
        result = ShadowTestResult(
            endpoint=endpoint,
            results_match=False,
            comparison_result=ComparisonResult.MATCH,
            old_result=None,
            new_result=None,
            old_duration_ms=0,
            new_duration_ms=0,
            performance_ratio=0,
            metadata=metadata,
        )

        # Run old implementation
        old_start = time.time()
        old_error = None
        try:
            if asyncio.iscoroutinefunction(old_implementation):
                result.old_result = await old_implementation(*args, **kwargs)
            else:
                result.old_result = old_implementation(*args, **kwargs)
        except Exception as e:
            old_error = str(e)
            logger.error(f"Old implementation error in {endpoint}: {e}")
        result.old_duration_ms = (time.time() - old_start) * 1000

        # Run new implementation
        new_start = time.time()
        new_error = None
        try:
            if asyncio.iscoroutinefunction(new_implementation):
                result.new_result = await new_implementation(*args, **kwargs)
            else:
                result.new_result = new_implementation(*args, **kwargs)
        except Exception as e:
            new_error = str(e)
            logger.error(f"New implementation error in {endpoint}: {e}")
        result.new_duration_ms = (time.time() - new_start) * 1000

        # Calculate performance ratio
        if result.old_duration_ms > 0:
            result.performance_ratio = result.new_duration_ms / result.old_duration_ms
        else:
            result.performance_ratio = 1.0

        # Determine comparison result
        if old_error and new_error:
            result.comparison_result = ComparisonResult.ERROR_BOTH
            result.error = f"Both failed: old={old_error}, new={new_error}"
        elif old_error:
            result.comparison_result = ComparisonResult.ERROR_OLD
            result.error = f"Old failed: {old_error}"
        elif new_error:
            result.comparison_result = ComparisonResult.ERROR_NEW
            result.error = f"New failed: {new_error}"
        else:
            # Compare results
            result.results_match, result.differences = self._compare_results(
                result.old_result, result.new_result, comparison_fields
            )

            if result.results_match:
                # Check performance
                if result.performance_ratio > self.performance_threshold:
                    result.comparison_result = ComparisonResult.PERFORMANCE_REGRESSION
                    result.results_match = False  # Consider regression as mismatch
                else:
                    result.comparison_result = ComparisonResult.MATCH
            else:
                result.comparison_result = ComparisonResult.DATA_MISMATCH

        # Track metrics
        self._track_metrics(result)

        # Log result
        await self._log_result(result)

        return result

    def _compare_results(
        self, old_result: Any, new_result: Any, comparison_fields: list[str] | None = None
    ) -> tuple[bool, dict | None]:
        """
        Compare two results for equality.

        Args:
            old_result: Result from old implementation
            new_result: Result from new implementation
            comparison_fields: Specific fields to compare

        Returns:
            Tuple of (matches, differences)
        """
        try:
            # Handle None cases
            if old_result is None and new_result is None:
                return True, None
            if old_result is None or new_result is None:
                return False, {"one_is_none": True}

            # Filter to specific fields if requested
            if comparison_fields:
                old_filtered = self._filter_fields(old_result, comparison_fields)
                new_filtered = self._filter_fields(new_result, comparison_fields)
            else:
                old_filtered = old_result
                new_filtered = new_result

            # Use DeepDiff for detailed comparison
            diff = DeepDiff(
                old_filtered,
                new_filtered,
                ignore_order=True,  # Lists can be in different order
                exclude_regex_paths=[
                    r".*\.created_at$",  # Ignore timestamps
                    r".*\.updated_at$",
                    r".*\.last_.*$",
                ],
                significant_digits=6,  # Float precision
                verbose_level=2,
            )

            if not diff:
                return True, None

            return False, diff.to_dict()

        except Exception as e:
            logger.error(f"Error comparing results: {e}")
            return False, {"error": str(e)}

    def _filter_fields(self, data: Any, fields: list[str]) -> Any:
        """
        Filter data to only include specified fields.

        Args:
            data: Data to filter
            fields: Fields to include

        Returns:
            Filtered data
        """
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k in fields}
        elif isinstance(data, list):
            return [self._filter_fields(item, fields) for item in data]
        elif hasattr(data, "__dict__"):
            return {k: v for k, v in data.__dict__.items() if k in fields}
        else:
            return data

    def _track_metrics(self, result: ShadowTestResult):
        """
        Track shadow test metrics.

        Args:
            result: Test result to track
        """
        # Track duration for both implementations
        shadow_test_duration.labels(endpoint=result.endpoint, implementation="old").observe(
            result.old_duration_ms / 1000
        )

        shadow_test_duration.labels(endpoint=result.endpoint, implementation="new").observe(
            result.new_duration_ms / 1000
        )

        # Track result
        status = "match" if result.results_match else "mismatch"
        shadow_test_total.labels(endpoint=result.endpoint, result=status).inc()

        # Track mismatches
        if not result.results_match:
            mismatch_type = result.comparison_result.value
            shadow_test_mismatches.labels(
                endpoint=result.endpoint, mismatch_type=mismatch_type
            ).inc()

    async def _log_result(self, result: ShadowTestResult):
        """
        Log shadow test result.

        Args:
            result: Test result to log
        """
        if result.results_match:
            await logger.info(
                f"Shadow test passed for {result.endpoint}",
                endpoint=result.endpoint,
                old_duration_ms=round(result.old_duration_ms, 2),
                new_duration_ms=round(result.new_duration_ms, 2),
                performance_ratio=round(result.performance_ratio, 2),
                metadata=result.metadata,
            )
        else:
            await logger.warning(
                f"Shadow test mismatch for {result.endpoint}",
                endpoint=result.endpoint,
                comparison_result=result.comparison_result.value,
                old_duration_ms=round(result.old_duration_ms, 2),
                new_duration_ms=round(result.new_duration_ms, 2),
                performance_ratio=round(result.performance_ratio, 2),
                differences=result.differences,
                error=result.error,
                metadata=result.metadata,
            )


class ShadowTestDecorator:
    """Decorator for automatic shadow testing of methods."""

    def __init__(
        self, endpoint: str, shadow_tester: ShadowTester, comparison_fields: list[str] | None = None
    ):
        """
        Initialize decorator.

        Args:
            endpoint: Endpoint name for tracking
            shadow_tester: ShadowTester instance
            comparison_fields: Fields to compare
        """
        self.endpoint = endpoint
        self.shadow_tester = shadow_tester
        self.comparison_fields = comparison_fields

    def __call__(self, new_implementation: Callable) -> Callable:
        """
        Decorate a function for shadow testing.

        Args:
            new_implementation: New implementation to test

        Returns:
            Wrapped function that performs shadow testing
        """

        @track_shadow_test(self.endpoint)
        async def async_wrapper(old_implementation: Callable, *args, **kwargs):
            """Async wrapper for shadow testing."""
            # Check if shadow testing is enabled
            if not self.shadow_tester.feature_flags.is_enabled("shadow_testing"):
                # Just run the appropriate implementation
                if self.shadow_tester.feature_flags.is_enabled("use_database_views"):
                    return await new_implementation(*args, **kwargs)
                else:
                    return await old_implementation(*args, **kwargs)

            # Run shadow test
            result = await self.shadow_tester.run_shadow_test(
                endpoint=self.endpoint,
                old_implementation=old_implementation,
                new_implementation=new_implementation,
                args=args,
                kwargs=kwargs,
                comparison_fields=self.comparison_fields,
            )

            # Return appropriate result based on feature flag
            if self.shadow_tester.feature_flags.is_enabled("use_database_views"):
                return result.new_result
            else:
                return result.old_result

        def sync_wrapper(old_implementation: Callable, *args, **kwargs):
            """Sync wrapper for shadow testing."""
            # For sync functions, run async in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_wrapper(old_implementation, *args, **kwargs))
            finally:
                loop.close()

        if asyncio.iscoroutinefunction(new_implementation):
            return async_wrapper
        else:
            return sync_wrapper


# Batch shadow testing for multiple endpoints
class BatchShadowTester:
    """Run shadow tests for multiple endpoints in parallel."""

    def __init__(self, shadow_tester: ShadowTester):
        """
        Initialize batch tester.

        Args:
            shadow_tester: ShadowTester instance
        """
        self.shadow_tester = shadow_tester

    async def run_batch_tests(self, test_cases: list[dict[str, Any]]) -> list[ShadowTestResult]:
        """
        Run multiple shadow tests in parallel.

        Args:
            test_cases: List of test case configurations

        Returns:
            List of test results
        """
        tasks = []

        for test_case in test_cases:
            task = self.shadow_tester.run_shadow_test(
                endpoint=test_case["endpoint"],
                old_implementation=test_case["old_implementation"],
                new_implementation=test_case["new_implementation"],
                args=test_case.get("args", ()),
                kwargs=test_case.get("kwargs", {}),
                comparison_fields=test_case.get("comparison_fields"),
                metadata=test_case.get("metadata"),
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch test failed for {test_cases[i]['endpoint']}: {result}")
                # Create error result
                error_result = ShadowTestResult(
                    endpoint=test_cases[i]["endpoint"],
                    results_match=False,
                    comparison_result=ComparisonResult.ERROR_BOTH,
                    old_result=None,
                    new_result=None,
                    old_duration_ms=0,
                    new_duration_ms=0,
                    performance_ratio=0,
                    error=str(result),
                )
                final_results.append(error_result)
            else:
                final_results.append(result)

        return final_results

    def generate_report(self, results: list[ShadowTestResult]) -> dict:
        """
        Generate summary report from batch test results.

        Args:
            results: List of test results

        Returns:
            Summary report dictionary
        """
        total = len(results)
        matches = sum(1 for r in results if r.results_match)
        mismatches = total - matches

        performance_regressions = sum(
            1 for r in results if r.comparison_result == ComparisonResult.PERFORMANCE_REGRESSION
        )

        avg_old_duration = sum(r.old_duration_ms for r in results) / total if total > 0 else 0
        avg_new_duration = sum(r.new_duration_ms for r in results) / total if total > 0 else 0
        avg_performance_ratio = (
            sum(r.performance_ratio for r in results) / total if total > 0 else 0
        )

        return {
            "summary": {
                "total_tests": total,
                "matches": matches,
                "mismatches": mismatches,
                "match_rate": matches / total * 100 if total > 0 else 0,
                "performance_regressions": performance_regressions,
            },
            "performance": {
                "avg_old_duration_ms": round(avg_old_duration, 2),
                "avg_new_duration_ms": round(avg_new_duration, 2),
                "avg_performance_ratio": round(avg_performance_ratio, 2),
                "improvement_percentage": round((1 - avg_performance_ratio) * 100, 2),
            },
            "mismatches_by_type": {
                result.comparison_result.value: sum(
                    1 for r in results if r.comparison_result == result.comparison_result
                )
                for result in results
                if not result.results_match
            },
            "endpoints": {
                r.endpoint: {
                    "match": r.results_match,
                    "comparison_result": r.comparison_result.value,
                    "performance_ratio": round(r.performance_ratio, 2),
                }
                for r in results
            },
        }


# Convenience factory function
def get_shadow_tester(
    feature_flags: FeatureFlags | None = None, performance_threshold: float = 1.5
) -> ShadowTester:
    """
    Get a shadow tester instance.

    Args:
        feature_flags: Feature flags instance (creates new if None)
        performance_threshold: Performance regression threshold

    Returns:
        ShadowTester instance
    """
    if feature_flags is None:
        feature_flags = FeatureFlags()

    return ShadowTester(feature_flags=feature_flags, performance_threshold=performance_threshold)
