"""
HTTPX AsyncClient fixtures for true async testing.
Following FastAPI best practices for integration testing.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import create_access_token
from app.main import app


@pytest.fixture
async def async_client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """
    Async client with dependency overrides for testing.
    Uses HTTPX with ASGI transport for true async testing.
    """
    # Override database dependency to use test session
    app.dependency_overrides[get_db] = lambda: db_session

    # Create async client with ASGI transport
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=30.0,  # Longer timeout for complex operations
    ) as client:
        yield client

    # Clean up overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(async_client: AsyncClient, test_user) -> AsyncClient:
    """
    Client with authentication headers for testing protected endpoints.
    Requires a test_user fixture to be defined.
    """
    # Create access token for test user
    token = create_access_token({"sub": test_user.username, "role": test_user.role})

    # Add authorization header
    async_client.headers["Authorization"] = f"Bearer {token}"

    return async_client


@pytest.fixture
async def admin_client(async_client: AsyncClient, admin_user) -> AsyncClient:
    """
    Client authenticated as admin for testing admin endpoints.
    """
    token = create_access_token({"sub": admin_user.username, "role": "admin"})
    async_client.headers["Authorization"] = f"Bearer {token}"

    return async_client


@pytest.fixture
async def curator_client(async_client: AsyncClient, curator_user) -> AsyncClient:
    """
    Client authenticated as curator for testing curator-level access.
    """
    token = create_access_token({"sub": curator_user.username, "role": "curator"})
    async_client.headers["Authorization"] = f"Bearer {token}"

    return async_client
