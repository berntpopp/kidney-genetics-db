"""
Advanced retry utilities with exponential backoff and jitter.
"""

import asyncio
import random
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        jitter_range: tuple[float, float] = (0.8, 1.2),
        retry_on_exceptions: tuple[type[Exception], ...] = (
            httpx.HTTPStatusError,
            httpx.RequestError,
            httpx.TimeoutException,
            asyncio.TimeoutError,
        ),
        retry_on_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504),
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_range = jitter_range
        self.retry_on_exceptions = retry_on_exceptions
        self.retry_on_status_codes = retry_on_status_codes

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.

        Uses exponential backoff with optional jitter.
        """
        # Exponential backoff
        delay = min(self.initial_delay * (self.exponential_base**attempt), self.max_delay)

        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_min, jitter_max = self.jitter_range
            jitter_factor = random.uniform(jitter_min, jitter_max)
            delay *= jitter_factor

        return delay


def _is_retryable_status(error: httpx.HTTPStatusError, config: RetryConfig) -> bool:
    """Honour retry_on_status_codes; gnomAD signals rate limiting as 400 "rate limit" (#364)."""
    response = error.response
    if response.status_code in config.retry_on_status_codes:
        return True
    return response.status_code == 400 and "rate limit" in response.text.lower()


def _retry_delay(error: Exception, config: RetryConfig, attempt: int) -> float:
    """Backoff with jitter, or a 429 Retry-After capped at max_delay."""
    if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 429:
        try:
            return min(float(error.response.headers.get("retry-after")), config.max_delay)
        except (TypeError, ValueError):
            pass
    return config.calculate_delay(attempt)


class CircuitBreaker:
    """
    Circuit breaker to prevent repeated calls to failing services.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise Exception(f"Circuit breaker is open (failures: {self.failure_count})")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    async def async_call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute async function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise Exception(f"Circuit breaker is open (failures: {self.failure_count})")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time is not None
            and time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self) -> None:
        """Reset circuit breaker on successful call."""
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self) -> None:
        """Record failure and potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.sync_warning("Circuit breaker opened", failure_count=self.failure_count)


def retry_with_backoff(
    config: RetryConfig | None = None, circuit_breaker: CircuitBreaker | None = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for retrying functions with exponential backoff.

    Supports both sync and async functions.
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    # Use circuit breaker if provided
                    if circuit_breaker:
                        return await circuit_breaker.async_call(func, *args, **kwargs)
                    else:
                        return await func(*args, **kwargs)

                except config.retry_on_exceptions as e:
                    last_exception = e
                    if isinstance(e, httpx.HTTPStatusError) and not _is_retryable_status(e, config):
                        logger.sync_debug(f"Status code {e.response.status_code} is not retryable")
                        raise
                    delay = _retry_delay(e, config, attempt)

                    # Don't retry if this was the last attempt
                    if attempt < config.max_retries:
                        logger.sync_warning(
                            "Attempt failed, retrying",
                            attempt=attempt + 1,
                            max_attempts=config.max_retries + 1,
                            error=str(e),
                            retry_delay=delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.sync_error(
                            "All attempts failed", max_attempts=config.max_retries + 1
                        )

            # If we get here, all retries failed
            if last_exception:
                raise last_exception

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    # Use circuit breaker if provided
                    if circuit_breaker:
                        return circuit_breaker.call(func, *args, **kwargs)
                    else:
                        return func(*args, **kwargs)

                except config.retry_on_exceptions as e:
                    last_exception = e
                    if isinstance(e, httpx.HTTPStatusError) and not _is_retryable_status(e, config):
                        raise
                    delay = _retry_delay(e, config, attempt)

                    # Don't retry if this was the last attempt
                    if attempt < config.max_retries:
                        logger.sync_warning(
                            "Attempt failed, retrying",
                            attempt=attempt + 1,
                            max_attempts=config.max_retries + 1,
                            error=str(e),
                            retry_delay=delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.sync_error(
                            "All attempts failed", max_attempts=config.max_retries + 1
                        )

            # If we get here, all retries failed
            if last_exception:
                raise last_exception

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class RetryStrategy:
    """
    Unified retry strategy for executing functions with exponential backoff.
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """Initialize retry strategy with configuration."""
        self.config = RetryConfig(
            max_retries=max_retries,
            initial_delay=initial_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
        )

    async def execute_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute an async function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except self.config.retry_on_exceptions as e:
                last_exception = e
                if isinstance(e, httpx.HTTPStatusError) and not _is_retryable_status(
                    e, self.config
                ):
                    raise

                if attempt < self.config.max_retries:
                    delay = _retry_delay(e, self.config, attempt)
                    await logger.warning(
                        f"Attempt {attempt + 1}/{self.config.max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    await logger.error(f"All {self.config.max_retries + 1} attempts failed")

        if last_exception:
            raise last_exception

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute a sync function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.config.retry_on_exceptions as e:
                last_exception = e
                if isinstance(e, httpx.HTTPStatusError) and not _is_retryable_status(
                    e, self.config
                ):
                    raise

                if attempt < self.config.max_retries:
                    delay = _retry_delay(e, self.config, attempt)
                    logger.sync_warning(
                        f"Attempt {attempt + 1}/{self.config.max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.sync_error(f"All {self.config.max_retries + 1} attempts failed")

        if last_exception:
            raise last_exception


class RetryableHTTPClient:
    """
    HTTP client with built-in retry logic and circuit breaker.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        retry_config: RetryConfig | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ):
        self.client = client
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = circuit_breaker

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """GET request, retried per ``retry_config``; callers add no retry layer of their own."""
        return await self._send(self.client.get, url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """POST request, retried per ``retry_config``; callers add no retry layer of their own."""
        return await self._send(self.client.post, url, **kwargs)

    async def _send(self, send: Callable[..., Any], url: str, **kwargs: Any) -> httpx.Response:
        async def attempt() -> httpx.Response:
            response: httpx.Response = await send(url, **kwargs)
            response.raise_for_status()
            return response

        result: httpx.Response = await retry_with_backoff(self.retry_config, self.circuit_breaker)(
            attempt
        )()
        return result

    async def close(self) -> None:
        """Close the underlying client."""
        await self.client.aclose()


class SimpleRateLimiter:
    """
    Simple rate limiter - no bursts, just consistent rate.

    Ensures requests are spaced at least 1/requests_per_second apart.
    Perfect for APIs with strict rate limits like PubTator3 (3 req/s).
    """

    def __init__(self, requests_per_second: float = 3.0):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second (e.g., 3.0 for PubTator)
        """
        self.min_interval = 1.0 / requests_per_second
        self.last_request: float = 0.0

    async def wait(self) -> None:
        """Wait if needed to maintain rate limit."""
        now = time.monotonic()
        elapsed = now - self.last_request
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        self.last_request = time.monotonic()


async def handle_rate_limit_response(response: httpx.Response) -> None:
    """
    If response is 429, pause the domain for Retry-After duration.

    Call this after receiving an HTTP response to automatically pause
    all requests to the same domain when rate-limited.
    """
    if response.status_code == 429:
        from app.core.domain_rate_limiter import get_domain_rate_limiter_registry

        retry_after = float(response.headers.get("Retry-After", "60"))
        domain = response.request.url.host
        registry = get_domain_rate_limiter_registry()
        registry.pause_domain(domain, retry_after)
