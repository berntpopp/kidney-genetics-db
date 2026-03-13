"""Tests for auth security improvements."""

import inspect

import pytest


@pytest.mark.unit
class TestPasswordResetSecurity:
    """Verify password reset does not leak tokens."""

    def test_no_token_in_log(self):
        """Reset token must not appear in log messages."""
        from app.api.endpoints import auth

        source = inspect.getsource(auth.forgot_password)
        # token= should not appear in any logger call
        assert "token=reset_token" not in source
        assert "token=reset_token[:8]" not in source

    def test_forgot_password_has_rate_limit(self):
        """forgot_password must have rate limiting."""
        from app.api.endpoints import auth

        module_source = inspect.getsource(auth)
        idx = module_source.index("async def forgot_password")
        preceding = module_source[max(0, idx - 200) : idx]
        assert "limiter.limit" in preceding
