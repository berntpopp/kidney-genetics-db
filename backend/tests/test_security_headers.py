"""Tests for security headers middleware."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestSecurityHeaders:
    """Verify security headers are present in responses."""

    def test_x_content_type_options(self):
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/version")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self):
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/version")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self):
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/version")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self):
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/version")
        assert (
            response.headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"
        )
