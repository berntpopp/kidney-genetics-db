"""Tests for CachedHttpClient redirect and resilience behavior."""

import pytest
from unittest.mock import MagicMock, patch

from app.core.cached_http_client import CachedHttpClient


@pytest.mark.unit
class TestCachedHttpClientRedirects:
    """Verify CachedHttpClient follows redirects."""

    def test_http_client_has_follow_redirects_enabled(self):
        """The underlying hishel client must follow redirects."""
        with patch("app.core.cached_http_client.hishel") as mock_hishel:
            mock_hishel.Controller.return_value = MagicMock()
            mock_hishel.AsyncFileStorage.return_value = MagicMock()
            mock_hishel.AsyncCacheClient.return_value = MagicMock()

            # Call the real __init__
            CachedHttpClient.__init__(
                CachedHttpClient.__new__(CachedHttpClient)
            )

            # Verify follow_redirects=True was passed
            call_kwargs = mock_hishel.AsyncCacheClient.call_args
            assert call_kwargs is not None
            _, kwargs = call_kwargs
            assert kwargs.get("follow_redirects") is True, (
                "CachedHttpClient must pass follow_redirects=True to AsyncCacheClient"
            )
