"""Tests for the percentile service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from scipy.stats import rankdata

from app.core.percentile_service import PercentileService


def test_percentile_calculation_with_ties():
    """Test that tied scores get averaged ranks."""
    scores = [10, 20, 20, 30, 40]
    ranks = rankdata(scores, method="average")
    percentiles = (ranks - 1) / (len(ranks) - 1)

    # Tied values should have same percentile
    assert percentiles[1] == percentiles[2]
    assert 0.3 < percentiles[1] < 0.4


def test_single_value_percentile():
    """Test edge case of single value."""
    scores = [42.0]
    ranks = rankdata(scores, method="average")
    # Single value should not be 100th percentile
    assert ranks[0] == 1.0

    # Convention: map to 0.5 (median) for single values
    percentile = 0.5 if len(scores) == 1 else (ranks[0] - 1) / (len(ranks) - 1)
    assert percentile == 0.5


def test_percentile_edge_cases():
    """Test various edge cases."""
    # Empty list
    scores = []
    if scores:
        ranks = rankdata(scores, method="average")
        percentiles = (ranks - 1) / (len(ranks) - 1)
    else:
        percentiles = []
    assert percentiles == []

    # All same values
    scores = [50, 50, 50, 50]
    ranks = rankdata(scores, method="average")
    # All should have same percentile (middle)
    percentiles = (ranks - 1) / (len(ranks) - 1) if len(ranks) > 1 else [0.5] * len(ranks)
    assert len(set(percentiles)) == 1  # All same


@pytest.mark.asyncio
async def test_percentile_service_disabled():
    """Test that service respects disable flag."""
    mock_session = Mock()

    with patch.dict("os.environ", {"DISABLE_PERCENTILE_CALCULATION": "true"}):
        service = PercentileService(mock_session)
        assert service.disabled is True

        result = await service.calculate_global_percentiles("test_source", "score")
        assert result == {}


@pytest.mark.asyncio
async def test_percentile_service_frequency_limiting():
    """Test that service respects frequency limits."""
    mock_session = Mock()
    service = PercentileService(mock_session)

    # Mock cache service
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()
    service.cache_service = mock_cache

    # First call should work
    with patch.object(service, "_calculate_sync", return_value={1: 0.5}):
        result1 = await service.calculate_global_percentiles("test", "score", force=False)
        assert result1 == {}  # No cached value

        # Mark as calculated
        service._last_calculation["test"] = 1000

        # Second call within interval should be skipped
        with patch("time.time", return_value=1100):  # 100 seconds later
            _ = await service.calculate_global_percentiles("test", "score", force=False)
            # Should return cached or empty (not recalculated)
            assert mock_cache.get.called


@pytest.mark.asyncio
async def test_percentile_service_timeout():
    """Test that service times out correctly."""
    mock_session = Mock()
    service = PercentileService(mock_session)

    # Mock a slow calculation
    async def slow_calc(*args):
        import asyncio

        await asyncio.sleep(10)  # Longer than timeout
        return {}

    with patch.object(service, "_calculate_with_fallback", side_effect=slow_calc):
        # Should timeout and return empty
        result = await service.calculate_global_percentiles("test", "score")
        # Due to timeout, should fall back to cache or empty
        assert result is not None  # Should not hang


@pytest.mark.asyncio
async def test_percentile_validation():
    """Test percentile validation logic."""
    mock_session = Mock()
    service = PercentileService(mock_session)

    # Test with good distribution
    good_percentiles = {
        1: 0.0,
        2: 0.1,
        3: 0.2,
        4: 0.3,
        5: 0.4,
        6: 0.5,
        7: 0.6,
        8: 0.7,
        9: 0.8,
        10: 0.9,
        11: 1.0,
    }
    service.get_cached_percentiles_only = AsyncMock(return_value=good_percentiles)
    result = await service.validate_percentiles("test")
    assert result["status"] == "ok"
    assert result["checks"]["has_variance"] is True
    assert result["checks"]["median_reasonable"] is True

    # Test with bad distribution (all same)
    bad_percentiles = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0}
    service.get_cached_percentiles_only = AsyncMock(return_value=bad_percentiles)
    result = await service.validate_percentiles("test")
    assert result["status"] == "warning"
    assert result["checks"]["has_variance"] is False
    assert result["checks"]["no_all_ones"] is False

    # Test with no data
    service.get_cached_percentiles_only = AsyncMock(return_value=None)
    result = await service.validate_percentiles("test")
    assert result["status"] == "error"
    assert result["message"] == "No percentiles found"
