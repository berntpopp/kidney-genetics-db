"""Test API rate limiting."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestRateLimitModule:
    """Test rate limit key function and configuration."""

    def test_anonymous_key_returns_ip(self):
        """Anonymous requests should be keyed by IP address."""
        from app.core.rate_limit import _get_rate_limit_key

        request = MagicMock()
        request.headers = {}
        request.client.host = "1.2.3.4"
        request.scope = {"type": "http"}

        key = _get_rate_limit_key(request)
        assert "1.2.3.4" in key

    def test_limiter_is_configured(self):
        """Limiter should be configured with default limits."""
        from app.core.rate_limit import limiter

        assert limiter is not None
        assert limiter._default_limits is not None
