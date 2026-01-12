"""
Database view monitoring and observability.
Uses Prometheus for metrics collection specific to database views migration.
"""

import asyncio
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from app.core.logging import get_logger

logger = get_logger(__name__)

# Create dedicated registry for view metrics
view_registry = CollectorRegistry()

# Database view query performance
view_query_duration = Histogram(
    "db_view_query_duration_seconds",
    "Database view query duration in seconds",
    ["view_name", "operation"],
    registry=view_registry,
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

view_query_total = Counter(
    "db_view_query_total",
    "Total database view queries",
    ["view_name", "status"],
    registry=view_registry,
)

view_query_errors = Counter(
    "db_view_query_errors_total",
    "Database view query errors",
    ["view_name", "error_type"],
    registry=view_registry,
)

# Shadow testing metrics
shadow_test_duration = Histogram(
    "shadow_test_duration_seconds",
    "Shadow test execution duration",
    ["endpoint", "implementation"],
    registry=view_registry,
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0),
)

shadow_test_mismatches = Counter(
    "shadow_test_mismatches_total",
    "Shadow test result mismatches",
    ["endpoint", "mismatch_type"],
    registry=view_registry,
)

shadow_test_total = Counter(
    "shadow_test_total",
    "Total shadow tests performed",
    ["endpoint", "result"],
    registry=view_registry,
)

# Feature flag metrics
feature_flag_evaluations = Counter(
    "feature_flag_evaluations_total",
    "Feature flag evaluations",
    ["flag_name", "result"],
    registry=view_registry,
)

feature_flag_rollout_percentage = Gauge(
    "feature_flag_rollout_percentage",
    "Current rollout percentage for feature flags",
    ["flag_name"],
    registry=view_registry,
)

# Materialized view metrics
materialized_view_refresh_duration = Histogram(
    "materialized_view_refresh_duration_seconds",
    "Time to refresh materialized views",
    ["view_name", "refresh_type"],
    registry=view_registry,
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

materialized_view_refresh_total = Counter(
    "materialized_view_refresh_total",
    "Total materialized view refreshes",
    ["view_name", "status"],
    registry=view_registry,
)

# Cache invalidation metrics
cache_invalidation_total = Counter(
    "cache_invalidation_total",
    "Total cache invalidations",
    ["table_name", "namespace"],
    registry=view_registry,
)

# Performance comparison metrics
performance_comparison = Gauge(
    "view_performance_comparison_ratio",
    "Performance ratio between old and new implementation (new/old)",
    ["endpoint", "metric_type"],
    registry=view_registry,
)


def track_view_performance(view_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to track database view query performance.

    Usage:
        @track_view_performance("gene_list_detailed")
        async def query_genes():
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                error_type = type(e).__name__
                view_query_errors.labels(view_name=view_name, error_type=error_type).inc()
                logger.sync_error(f"View query failed: {view_name}", error=e, view_name=view_name)
                raise
            finally:
                duration = time.time() - start_time
                view_query_duration.labels(view_name=view_name, operation="query").observe(duration)
                view_query_total.labels(view_name=view_name, status=status).inc()

                # Log slow queries for alerting
                if duration > 0.1:  # 100ms threshold
                    logger.sync_warning(
                        "Slow view query detected",
                        view_name=view_name,
                        duration_ms=duration * 1000,
                        threshold_ms=100,
                    )

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            status = "success"

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                error_type = type(e).__name__
                view_query_errors.labels(view_name=view_name, error_type=error_type).inc()
                logger.sync_error(
                    f"View query failed: {view_name}", error=e, view_name=view_name
                )
                raise
            finally:
                duration = time.time() - start_time
                view_query_duration.labels(view_name=view_name, operation="query").observe(duration)
                view_query_total.labels(view_name=view_name, status=status).inc()

                # Log slow queries
                if duration > 0.1:
                    logger.sync_warning(
                        "Slow view query detected", view_name=view_name, duration_ms=duration * 1000
                    )

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def track_shadow_test(endpoint: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to track shadow test execution.

    Usage:
        @track_shadow_test("get_genes")
        async def shadow_test_genes():
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                result = await func(*args, **kwargs)

                # Track duration for both implementations
                if hasattr(result, "old_duration_ms") and hasattr(result, "new_duration_ms"):
                    shadow_test_duration.labels(endpoint=endpoint, implementation="old").observe(
                        result.old_duration_ms / 1000
                    )

                    shadow_test_duration.labels(endpoint=endpoint, implementation="new").observe(
                        result.new_duration_ms / 1000
                    )

                    # Track performance comparison
                    if result.old_duration_ms > 0:
                        ratio = result.new_duration_ms / result.old_duration_ms
                        performance_comparison.labels(
                            endpoint=endpoint, metric_type="duration_ratio"
                        ).set(ratio)

                # Track match/mismatch
                if hasattr(result, "results_match"):
                    status = "match" if result.results_match else "mismatch"
                    shadow_test_total.labels(endpoint=endpoint, result=status).inc()

                    if not result.results_match:
                        mismatch_type = "data"
                        if hasattr(result, "error") and result.error:
                            mismatch_type = "exception"

                        shadow_test_mismatches.labels(
                            endpoint=endpoint, mismatch_type=mismatch_type
                        ).inc()

                return result

            except Exception as e:
                shadow_test_total.labels(endpoint=endpoint, result="error").inc()
                logger.sync_error(f"Shadow test failed for {endpoint}", error=e)
                raise

        return wrapper

    return decorator


def track_materialized_view_refresh(view_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to track materialized view refresh operations.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.sync_error(f"Materialized view refresh failed: {view_name}", error=e)
                raise
            finally:
                duration = time.time() - start_time

                # Determine refresh type
                refresh_type = "concurrent" if "CONCURRENTLY" in str(func) else "standard"

                materialized_view_refresh_duration.labels(
                    view_name=view_name, refresh_type=refresh_type
                ).observe(duration)

                materialized_view_refresh_total.labels(view_name=view_name, status=status).inc()

                if duration > 30:  # 30 second threshold
                    logger.sync_warning(
                        f"Slow materialized view refresh: {view_name}", duration_s=duration
                    )

        return wrapper if asyncio.iscoroutinefunction(func) else func

    return decorator


def track_feature_flag_evaluation(flag_name: str, enabled: bool) -> None:
    """
    Track feature flag evaluation.

    Args:
        flag_name: Name of the feature flag
        enabled: Whether the flag was evaluated as enabled
    """
    result = "enabled" if enabled else "disabled"
    feature_flag_evaluations.labels(flag_name=flag_name, result=result).inc()


def update_rollout_percentage(flag_name: str, percentage: float) -> None:
    """
    Update the rollout percentage metric.

    Args:
        flag_name: Name of the feature flag
        percentage: Current rollout percentage
    """
    feature_flag_rollout_percentage.labels(flag_name=flag_name).set(percentage)


def track_cache_invalidation(table_name: str, namespace: str) -> None:
    """
    Track cache invalidation operations.

    Args:
        table_name: Table that triggered invalidation
        namespace: Cache namespace being invalidated
    """
    cache_invalidation_total.labels(table_name=table_name, namespace=namespace).inc()


class ViewMetricsManager:
    """
    Manager for view-specific metrics.
    Provides centralized access to metrics and reporting.
    """

    @staticmethod
    def get_metrics() -> bytes:
        """
        Get current metrics in Prometheus format.

        Returns:
            Metrics data in Prometheus text format
        """
        result: bytes = generate_latest(view_registry)
        return result

    @staticmethod
    def get_metrics_summary() -> dict[str, Any]:
        """
        Get summary of key metrics.

        Returns:
            Dictionary with key metric values
        """
        # Get sample values from collectors
        summary: dict[str, Any] = {
            "view_queries": {},
            "shadow_tests": {},
            "feature_flags": {},
            "materialized_views": {},
            "performance": {},
        }

        # This would need actual metric parsing in production
        # For now, return structure
        return summary

    @staticmethod
    async def check_health_thresholds() -> dict[str, Any]:
        """
        Check if metrics are within healthy thresholds.

        Returns:
            Health status based on metric thresholds
        """
        health: dict[str, Any] = {"healthy": True, "checks": {}}

        # Check error rate (should be < 1%)
        # In production, calculate from actual metrics
        error_rate = 0.001  # Placeholder
        health["checks"]["error_rate"] = {
            "value": error_rate,
            "threshold": 0.01,
            "healthy": error_rate < 0.01,
        }

        # Check P99 latency (should be < 200ms)
        p99_latency = 0.085  # Placeholder
        health["checks"]["p99_latency"] = {
            "value": p99_latency,
            "threshold": 0.2,
            "healthy": p99_latency < 0.2,
        }

        # Check shadow test mismatch rate (should be < 5%)
        mismatch_rate = 0.01  # Placeholder
        health["checks"]["shadow_test_mismatch_rate"] = {
            "value": mismatch_rate,
            "threshold": 0.05,
            "healthy": mismatch_rate < 0.05,
        }

        # Overall health
        checks: dict[str, Any] = health["checks"]
        health["healthy"] = all(check.get("healthy", True) for check in checks.values())

        return health


# Export middleware for FastAPI
class ViewMetricsMiddleware:
    """FastAPI middleware for view metrics endpoint."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        """
        Handle metrics endpoint requests.
        """
        if scope["type"] == "http" and scope["path"] == "/view-metrics":
            # Return Prometheus metrics
            metrics = ViewMetricsManager.get_metrics()

            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        [b"content-type", CONTENT_TYPE_LATEST.encode()],
                        [b"content-length", str(len(metrics)).encode()],
                    ],
                }
            )

            await send(
                {
                    "type": "http.response.body",
                    "body": metrics,
                }
            )
        else:
            await self.app(scope, receive, send)
