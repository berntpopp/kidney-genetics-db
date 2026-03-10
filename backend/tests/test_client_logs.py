"""Test client-side log reporting endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestClientLogsEndpoint:
    """Test POST /api/client-logs."""

    @pytest.mark.asyncio
    async def test_accepts_valid_error_log(self, async_client: AsyncClient):
        """Valid error log should be accepted."""
        response = await async_client.post(
            "/api/client-logs",
            json={
                "level": "ERROR",
                "message": "Unhandled Vue error",
                "error_type": "TypeError",
                "error_message": "Cannot read properties of null",
                "url": "https://example.com/genes/HNF1B",
                "user_agent": "Mozilla/5.0",
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_rejects_invalid_level(self, async_client: AsyncClient):
        """Invalid log level should be rejected."""
        response = await async_client.post(
            "/api/client-logs",
            json={
                "level": "INVALID",
                "message": "test",
            },
        )
        # Project returns 400 for validation errors (custom error handler)
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_requires_message(self, async_client: AsyncClient):
        """Message field is required."""
        response = await async_client.post(
            "/api/client-logs",
            json={
                "level": "ERROR",
            },
        )
        # Project returns 400 for validation errors (custom error handler)
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_no_auth_required(self, async_client: AsyncClient):
        """Endpoint should be public (no auth required)."""
        response = await async_client.post(
            "/api/client-logs",
            json={
                "level": "ERROR",
                "message": "test error",
            },
        )
        assert response.status_code in (201, 200)
