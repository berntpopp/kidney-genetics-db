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

    def test_decode_access_token_does_not_exist(self):
        """Confirm decode_access_token does not exist."""
        with pytest.raises(ImportError):
            from app.core.security import decode_access_token  # noqa: F401

    def test_limiter_is_configured(self):
        """Limiter should be configured with default limits."""
        from app.core.rate_limit import limiter

        assert limiter is not None
        assert limiter._default_limits is not None
