"""Tests for global exception handler registration."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestExceptionHandlers:
    """Verify domain exceptions produce correct HTTP responses."""

    def test_gene_not_found_returns_404(self):
        from app.core.exceptions import GeneNotFoundError
        from app.main import app

        @app.get("/test-gene-not-found")
        async def raise_gene_not_found():
            raise GeneNotFoundError("TEST123")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-gene-not-found")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "not_found"
        assert "TEST123" in data["error"]["message"]
        assert "error_id" in data["error"]

    def test_authentication_error_returns_401(self):
        from app.core.exceptions import AuthenticationError
        from app.main import app

        @app.get("/test-auth-error")
        async def raise_auth_error():
            raise AuthenticationError("Invalid credentials")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-auth-error")
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["type"] == "authentication_error"

    def test_permission_denied_returns_403(self):
        from app.core.exceptions import PermissionDeniedError
        from app.main import app

        @app.get("/test-perm-error")
        async def raise_perm_error():
            raise PermissionDeniedError("admin", "test_operation")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-perm-error")
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["type"] == "permission_denied"

    def test_domain_validation_error_returns_422(self):
        from app.core.exceptions import ValidationError as DomainValidationError
        from app.main import app

        @app.get("/test-validation-error")
        async def raise_validation_error():
            raise DomainValidationError(reason="Invalid input")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-validation-error")
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["type"] == "validation_error"

    def test_resource_conflict_returns_409(self):
        from app.core.exceptions import ResourceConflictError
        from app.main import app

        @app.get("/test-conflict-error")
        async def raise_conflict_error():
            raise ResourceConflictError("Gene", "Already exists")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-conflict-error")
        assert response.status_code == 409
        data = response.json()
        assert data["error"]["type"] == "resource_conflict"

    def test_rate_limit_exceeded_returns_429(self):
        from app.core.exceptions import RateLimitExceededError
        from app.main import app

        @app.get("/test-rate-limit-error")
        async def raise_rate_limit_error():
            raise RateLimitExceededError("test_service", retry_after=60)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-rate-limit-error")
        assert response.status_code == 429
        data = response.json()
        assert data["error"]["type"] == "rate_limit_exceeded"
        assert response.headers.get("Retry-After") == "60"

    def test_base_kidney_genetics_exception_returns_500(self):
        from app.core.exceptions import KidneyGeneticsException
        from app.main import app

        @app.get("/test-base-error")
        async def raise_base_error():
            raise KidneyGeneticsException("Something went wrong")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-base-error")
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["type"] == "internal_error"
