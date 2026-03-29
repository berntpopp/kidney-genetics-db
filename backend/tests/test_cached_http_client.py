"""Tests for CachedHttpClient redirect and resilience behavior."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.cached_http_client import CachedHttpClient


@pytest.mark.unit
class TestCachedHttpClientRedirects:
    """Verify CachedHttpClient follows redirects."""

    def test_http_client_has_follow_redirects_enabled(self):
        """The underlying httpx client must follow redirects."""
        with patch("app.core.cached_http_client.get_cache_service") as mock_cache:
            mock_cache.return_value = MagicMock()

            client = CachedHttpClient.__new__(CachedHttpClient)
            CachedHttpClient.__init__(client)

            # Verify the httpx client has follow_redirects enabled
            assert isinstance(client.http_client, httpx.AsyncClient)
            assert client.http_client.follow_redirects is True, (
                "CachedHttpClient must create httpx.AsyncClient with follow_redirects=True"
            )
