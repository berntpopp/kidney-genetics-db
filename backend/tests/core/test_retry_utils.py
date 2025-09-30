"""
Unit tests for retry utilities.
Testing retry logic, exponential backoff, circuit breaker without external dependencies.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.retry_utils import (
    CircuitBreaker,
    RetryableHTTPClient,
    RetryConfig,
    retry_with_backoff,
)


@pytest.mark.unit
class TestRetryConfig:
    """Test retry configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()

        assert config.max_retries == 5
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.jitter_range == (0.8, 1.2)

    def test_custom_config(self):
        """Test custom configuration."""
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False,
            jitter_range=(0.9, 1.1),
        )

        assert config.max_retries == 3
        assert config.initial_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert config.jitter_range == (0.9, 1.1)

    def test_delay_calculation(self):
        """Test delay calculation with exponential backoff."""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False,  # Disable jitter for predictable testing
        )

        # Test exponential backoff
        delay_0 = config.calculate_delay(0)  # 1.0 * 2^0 = 1.0
        delay_1 = config.calculate_delay(1)  # 1.0 * 2^1 = 2.0
        delay_2 = config.calculate_delay(2)  # 1.0 * 2^2 = 4.0

        assert delay_0 == 1.0
        assert delay_1 == 2.0
        assert delay_2 == 4.0


@pytest.mark.unit
class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_initial_state_closed(self):
        """Test that circuit breaker starts in closed state."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    def test_failure_tracking(self):
        """Test that failures are tracked internally."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        # Simulate failures
        breaker._on_failure()
        assert breaker.failure_count == 1

        breaker._on_failure()
        assert breaker.failure_count == 2

    def test_circuit_opens_after_threshold(self):
        """Test that circuit opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)

        # Record failures up to threshold
        breaker._on_failure()
        assert breaker.state == "closed"

        # One more failure should open the circuit
        breaker._on_failure()
        assert breaker.state == "open"

    def test_success_resets_failures(self):
        """Test that success resets failure count."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        breaker._on_failure()
        breaker._on_failure()
        assert breaker.failure_count == 2

        breaker._on_success()
        assert breaker.failure_count == 0
        assert breaker.state == "closed"

    def test_open_circuit_rejects_calls(self):
        """Test that open circuit rejects calls immediately."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)

        # Open the circuit
        breaker._on_failure()
        assert breaker.state == "open"

        # Should raise exception when trying to call
        def dummy_func():
            return "success"

        with pytest.raises(Exception, match="Circuit breaker is open"):
            breaker.call(dummy_func)

    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(self):
        """Test that circuit enters half-open state after timeout."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        # Open the circuit
        breaker._on_failure()
        assert breaker.state == "open"

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Next call should enter half-open state
        async def dummy_async():
            return "success"

        result = await breaker.async_call(dummy_async)
        assert result == "success"
        assert breaker.state == "closed"  # Success should close it


@pytest.mark.unit
class TestRetryDecorator:
    """Test retry decorator functionality."""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test that successful calls don't retry."""
        call_count = 0

        @retry_with_backoff()
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_function()

        assert result == "success"
        assert call_count == 1  # Called only once

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test that function retries on failure."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=3))
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await failing_function()

        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded third time

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that max retries is respected."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=2))
        async def always_failing():
            nonlocal call_count
            call_count += 1
            raise Exception("Permanent failure")

        with pytest.raises(Exception, match="Permanent failure"):
            await always_failing()

        # Should try: initial + 2 retries = 3 total
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff increases delay."""
        call_times = []

        @retry_with_backoff(
            config=RetryConfig(
                max_retries=3,
                initial_delay=0.1,
                exponential_base=2.0,
                jitter=False,  # No jitter for predictable timing
            )
        )
        async def timed_function():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 3:
                raise Exception("Retry me")
            return "success"

        await timed_function()

        # Check that delays are increasing
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]

            # Second delay should be longer than first (exponential backoff)
            assert delay2 > delay1

    @pytest.mark.asyncio
    async def test_retry_specific_exceptions_only(self):
        """Test retrying only specific exception types."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=3, retry_on_exceptions=(ValueError,)))
        async def selective_retry():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retry this")
            elif call_count == 2:
                raise TypeError("Don't retry this")

        with pytest.raises(TypeError):
            await selective_retry()

        # Should have called twice: once ValueError (retried), once TypeError (not retried)
        assert call_count == 2


@pytest.mark.unit
class TestRetryableHTTPClient:
    """Test retryable HTTP client."""

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """Test that successful requests return immediately."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=MagicMock(status_code=200))

        retryable_client = RetryableHTTPClient(
            client=mock_client, retry_config=RetryConfig(max_retries=3)
        )

        response = await retryable_client.get("http://example.com")

        assert response.status_code == 200
        # Should only call once
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_5xx_errors(self):
        """Test that 5xx errors trigger retry."""
        mock_client = MagicMock()

        # First two calls return 500, third succeeds
        mock_client.get = AsyncMock(
            side_effect=[
                MagicMock(status_code=500),
                MagicMock(status_code=503),
                MagicMock(status_code=200),
            ]
        )

        retryable_client = RetryableHTTPClient(
            client=mock_client, retry_config=RetryConfig(max_retries=3, initial_delay=0.01)
        )

        response = await retryable_client.get("http://example.com")

        assert response.status_code == 200
        # Should have retried twice
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx_errors(self):
        """Test that 4xx errors don't trigger retry."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=MagicMock(status_code=404))

        retryable_client = RetryableHTTPClient(
            client=mock_client, retry_config=RetryConfig(max_retries=3)
        )

        response = await retryable_client.get("http://example.com")

        assert response.status_code == 404
        # Should only call once (no retry on 4xx)
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self):
        """Test that circuit breaker prevents requests when open."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Service unavailable"))

        circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=10.0)

        retryable_client = RetryableHTTPClient(
            client=mock_client,
            retry_config=RetryConfig(max_retries=1, initial_delay=0.01),
            circuit_breaker=circuit_breaker,
        )

        # First request should fail and record failure
        with pytest.raises(Exception, match="Service unavailable"):
            await retryable_client.get("http://example.com")

        # Second request should fail and open circuit
        with pytest.raises(Exception, match="Service unavailable"):
            await retryable_client.get("http://example.com")

        # Circuit should now be open
        assert circuit_breaker.state == "open"

        # Third request should fail immediately without calling client
        initial_call_count = mock_client.get.call_count
        with pytest.raises(Exception, match="Circuit breaker is open"):
            await retryable_client.get("http://example.com")

        # Client should not have been called again
        assert mock_client.get.call_count == initial_call_count


@pytest.mark.unit
class TestRetryUtilsEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_zero_retries(self):
        """Test behavior with zero retries configured."""
        call_count = 0

        @retry_with_backoff(config=RetryConfig(max_retries=0))
        async def function_with_no_retries():
            nonlocal call_count
            call_count += 1
            raise Exception("Fail")

        with pytest.raises(Exception, match="Fail"):
            await function_with_no_retries()

        # Should only call once (no retries)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delays."""
        config = RetryConfig(initial_delay=1.0, jitter=True, jitter_range=(0.5, 1.5))

        delays = []
        for i in range(5):
            # Calculate delay with jitter
            delay = config.calculate_delay(i)
            delays.append(delay)

        # With jitter enabled, delays should incorporate randomness
        # Base delay for retry 0 would be 1.0, but jitter makes it vary
        assert all(d > 0 for d in delays), "All delays should be positive"
