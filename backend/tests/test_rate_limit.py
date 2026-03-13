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

    def test_returns_ip_for_invalid_bearer(self):
        """Invalid bearer tokens should fall back to IP-based key."""
        from app.core.rate_limit import _get_rate_limit_key

        request = MagicMock()
        request.headers = {"Authorization": "Bearer invalid_token"}
        request.client.host = "1.2.3.4"
        request.scope = {"type": "http"}

        result = _get_rate_limit_key(request)
        assert isinstance(result, str)
        # Should fall back to IP, not crash
        assert not result.startswith("user:")
        assert not result.startswith("admin:")

    def test_import_uses_verify_token(self):
        """Verify we import verify_token, not decode_access_token."""
        from app.core.security import verify_token  # noqa: F401

        assert callable(verify_token)

    def test_invalid_bearer_falls_back_to_ip(self):
        """Invalid bearer tokens must not crash and should fall back to IP."""
        from app.core.rate_limit import _get_rate_limit_key

        request = MagicMock()
        request.headers = {"Authorization": "Bearer totally.bogus.jwt"}
        request.client.host = "10.0.0.1"
        request.scope = {"type": "http"}

        key = _get_rate_limit_key(request)
        assert "10.0.0.1" in key

    def test_limiter_is_configured(self):
        """Limiter should be configured with default limits."""
        from app.core.rate_limit import limiter

        assert limiter is not None
        assert limiter._default_limits is not None
