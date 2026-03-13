"""Tests for secure token storage via HttpOnly cookies."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestTokenCookies:
    """Verify refresh tokens are sent as HttpOnly cookies."""

    def test_login_sets_httponly_cookie(self):
        """Login response should set refresh_token as HttpOnly cookie."""
        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "test_password"},
        )
        # If login succeeds, check cookie
        if response.status_code == 200:
            cookies = response.headers.get("set-cookie", "")
            assert "refresh_token" in cookies
            assert "httponly" in cookies.lower()
            assert "samesite=strict" in cookies.lower()

    def test_refresh_requires_csrf_header(self):
        """Refresh endpoint should reject requests without X-Requested-With header."""
        from app.main import app

        client = TestClient(app)
        # POST to refresh without CSRF header should fail with 403
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "dummy"},
        )
        assert response.status_code == 403
        body = response.json()
        detail = body.get("detail", "") or body.get("error", {}).get("detail", "")
        assert "CSRF" in detail

    def test_refresh_accepts_csrf_header(self):
        """Refresh endpoint should accept requests with X-Requested-With header."""
        from app.main import app

        client = TestClient(app)
        # POST with CSRF header but invalid token should get 401, not 403
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "dummy"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        # Should pass CSRF check and fail on token validation instead
        assert response.status_code == 401
