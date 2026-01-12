"""
Performance monitoring decorators for the unified logging system.

Provides decorators for tracking operation performance, database queries,
and API endpoint response times with automatic logging integration.
"""

import asyncio
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

# Lazy import to avoid circular dependency
_logger: Any = None

F = TypeVar("F", bound=Callable[..., Any])


def _get_logger() -> Any:
    """Get logger instance lazily to avoid circular import."""
    global _logger
    if _logger is None:
        from app.core.logging import get_logger

        _logger = get_logger(__name__)
    return _logger


def timed_operation(
    operation_name: str | None = None,
    warning_threshold_ms: float = 1000,
    error_threshold_ms: float = 5000,
    include_args: bool = False,
) -> Callable[[F], F]:
    """
    Decorator to time operations and log performance metrics.

    Args:
        operation_name: Name of the operation (defaults to function name)
        warning_threshold_ms: Log warning if operation takes longer than this (ms)
        error_threshold_ms: Log error if operation takes longer than this (ms)
        include_args: Whether to include function arguments in logs
    """

    def decorator(func: F) -> F:
        name = operation_name or func.__name__

        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()

                # Build context for logging
                context: dict[str, Any] = {"operation": name}
                if include_args:
                    context["args"] = str(args)[:200]  # Limit arg length
                    context["kwargs"] = str(kwargs)[:200]

                try:
                    # Log start of operation (debug level)
                    await _get_logger().debug("Operation started", **context)

                    # Execute the operation
                    result = await func(*args, **kwargs)

                    # Calculate duration
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)

                    # Log based on duration
                    if duration_ms > error_threshold_ms:
                        await _get_logger().error("Operation exceeded error threshold", **context)
                    elif duration_ms > warning_threshold_ms:
                        await _get_logger().warning(
                            "Operation exceeded warning threshold", **context
                        )
                    else:
                        await _get_logger().info("Operation completed", **context)

                    return result

                except Exception as e:
                    # Log the error with timing
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    await _get_logger().error("Operation failed", **context)
                    raise

            return async_wrapper  # type: ignore[return-value]
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()

                # Build context for logging
                context: dict[str, Any] = {"operation": name}
                if include_args:
                    context["args"] = str(args)[:200]
                    context["kwargs"] = str(kwargs)[:200]

                try:
                    # Log start of operation (debug level)
                    _get_logger().sync_debug("Operation started", **context)

                    # Execute the operation
                    result = func(*args, **kwargs)

                    # Calculate duration
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)

                    # Log based on duration
                    if duration_ms > error_threshold_ms:
                        _get_logger().sync_error("Operation exceeded error threshold", **context)
                    elif duration_ms > warning_threshold_ms:
                        _get_logger().sync_warning(
                            "Operation exceeded warning threshold", **context
                        )
                    else:
                        _get_logger().sync_info("Operation completed", **context)

                    return result

                except Exception as e:
                    # Log the error with timing
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    _get_logger().sync_error("Operation failed", **context)
                    raise

            return sync_wrapper  # type: ignore[return-value]

    return decorator


def database_query(query_type: str = "SELECT") -> Callable[[F], F]:
    """
    Decorator specifically for database operations.

    Args:
        query_type: Type of query (SELECT, INSERT, UPDATE, DELETE)
    """
    return timed_operation(
        operation_name=f"database_{query_type.lower()}",
        warning_threshold_ms=100,  # Warn on queries > 100ms
        error_threshold_ms=1000,  # Error on queries > 1s
        include_args=False,  # Don't log query parameters by default
    )


def api_endpoint(endpoint_name: str | None = None) -> Callable[[F], F]:
    """
    Decorator for API endpoint performance tracking.

    Args:
        endpoint_name: Name of the endpoint (defaults to function name)
    """
    return timed_operation(
        operation_name=endpoint_name,
        warning_threshold_ms=500,  # Warn on endpoints > 500ms
        error_threshold_ms=2000,  # Error on endpoints > 2s
        include_args=False,
    )


def batch_operation(
    batch_name: str, batch_size_getter: Callable[..., int] | None = None
) -> Callable[[F], F]:
    """
    Decorator for batch processing operations with per-item metrics.

    Args:
        batch_name: Name of the batch operation
        batch_size_getter: Function to extract batch size from arguments
    """

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()

                # Get batch size if getter provided
                batch_size: int | None = None
                if batch_size_getter:
                    try:
                        batch_size = batch_size_getter(*args, **kwargs)
                    except Exception:
                        pass

                context: dict[str, Any] = {"operation": batch_name, "batch_size": batch_size}

                try:
                    await _get_logger().info("Batch operation started", **context)
                    result = await func(*args, **kwargs)

                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)

                    if batch_size:
                        context["ms_per_item"] = round(duration_ms / batch_size, 2)
                        context["items_per_second"] = round(batch_size / (duration_ms / 1000), 2)

                    await _get_logger().info("Batch operation completed", **context)
                    return result

                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    await _get_logger().error("Batch operation failed", **context)
                    raise

            return async_wrapper  # type: ignore[return-value]
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()

                # Get batch size if getter provided
                batch_size: int | None = None
                if batch_size_getter:
                    try:
                        batch_size = batch_size_getter(*args, **kwargs)
                    except Exception:
                        pass

                context: dict[str, Any] = {"operation": batch_name, "batch_size": batch_size}

                try:
                    _get_logger().sync_info("Batch operation started", **context)
                    result = func(*args, **kwargs)

                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)

                    if batch_size:
                        context["ms_per_item"] = round(duration_ms / batch_size, 2)
                        context["items_per_second"] = round(batch_size / (duration_ms / 1000), 2)

                    _get_logger().sync_info("Batch operation completed", **context)
                    return result

                except Exception as e:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    context["duration_ms"] = round(duration_ms, 2)
                    context["error"] = str(e)
                    _get_logger().sync_error("Batch operation failed", **context)
                    raise

            return sync_wrapper  # type: ignore[return-value]

    return decorator


class PerformanceMonitor:
    """Context manager for performance monitoring blocks of code."""

    def __init__(self, operation_name: str, **extra_context: Any) -> None:
        self.operation_name = operation_name
        self.extra_context = extra_context
        self.start_time: float | None = None

    def __enter__(self) -> "PerformanceMonitor":
        self.start_time = time.perf_counter()
        _get_logger().sync_debug(
            "Performance block started", operation=self.operation_name, **self.extra_context
        )
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        start = self.start_time if self.start_time is not None else time.perf_counter()
        duration_ms = (time.perf_counter() - start) * 1000

        context: dict[str, Any] = {
            "operation": self.operation_name,
            "duration_ms": round(duration_ms, 2),
            **self.extra_context,
        }

        if exc_type:
            context["error"] = str(exc_val)
            _get_logger().sync_error("Performance block failed", **context)
        else:
            _get_logger().sync_info("Performance block completed", **context)

        # Don't suppress exceptions (returning None is equivalent to returning False)

    async def __aenter__(self) -> "PerformanceMonitor":
        self.start_time = time.perf_counter()
        await _get_logger().debug(
            "Performance block started", operation=self.operation_name, **self.extra_context
        )
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        start = self.start_time if self.start_time is not None else time.perf_counter()
        duration_ms = (time.perf_counter() - start) * 1000

        context: dict[str, Any] = {
            "operation": self.operation_name,
            "duration_ms": round(duration_ms, 2),
            **self.extra_context,
        }

        if exc_type:
            context["error"] = str(exc_val)
            await _get_logger().error("Performance block failed", **context)
        else:
            await _get_logger().info("Performance block completed", **context)

        # Don't suppress exceptions (returning None is equivalent to returning False)


def monitor_blocking(threshold_ms: float = 5.0) -> Callable[[F], F]:
    """
    Decorator to monitor and log event loop blocking in async functions.

    Detects when async operations take longer than expected, which may
    indicate blocking I/O or CPU-bound operations that should be offloaded
    to a thread pool.

    Args:
        threshold_ms: Threshold in milliseconds above which to log a warning (default: 5ms)

    Usage:
        @monitor_blocking(threshold_ms=10.0)
        async def potentially_blocking_function():
            # Function code here
            pass

    Example:
        @monitor_blocking(threshold_ms=5.0)
        async def fetch_data():
            # If this takes >5ms, a warning will be logged
            result = await some_operation()
            return result
    """

    def decorator(func: F) -> F:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"monitor_blocking can only be applied to async functions, got {func}")

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            loop = asyncio.get_event_loop()
            start = loop.time()

            result = await func(*args, **kwargs)

            duration_ms = (loop.time() - start) * 1000
            if duration_ms > threshold_ms:
                await _get_logger().warning(
                    f"Potential event loop blocking in {func.__name__}",
                    duration_ms=round(duration_ms, 2),
                    threshold_ms=threshold_ms,
                    function=f"{func.__module__}.{func.__name__}",
                    recommendation="Consider offloading to thread pool if this operation involves I/O or is CPU-bound",
                )

            return result

        return wrapper  # type: ignore[return-value]

    return decorator
