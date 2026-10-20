"""Regression tests for #290: password change/reset revokes the stored refresh token."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from tests.fixtures.auth import get_or_create_user

PASSWORD = "Synthetic-Old-Pw-3Lk!"
NEW_PASSWORD = "Synthetic-New-Pw-8Rt!"
XHR = {"X-Requested-With": "XMLHttpRequest"}


async def _login(client: AsyncClient, username: str) -> tuple[str, str]:
    resp = await client.post("/api/auth/login", data={"username": username, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    refresh = resp.cookies["refresh_token"]
    client.cookies.clear()
    return resp.json()["access_token"], refresh


async def _refresh_status(client: AsyncClient, refresh: str) -> int:
    resp = await client.post("/api/auth/refresh", headers=XHR, json={"refresh_token": refresh})
    return resp.status_code


@pytest.fixture
def user(db_session):
    return get_or_create_user(
        db_session, "audit_revoke_user", "audit_revoke_user@example.com", PASSWORD, "viewer"
    )


@pytest.mark.integration
async def test_change_password_revokes_refresh_token(async_client: AsyncClient, user) -> None:
    access, refresh = await _login(async_client, user.username)
    assert await _refresh_status(async_client, refresh) == 200

    resp = await async_client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {access}"},
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    assert await _refresh_status(async_client, refresh) == 401


@pytest.mark.integration
async def test_reset_password_revokes_refresh_token(
    async_client: AsyncClient, db_session, user
) -> None:
    _, refresh = await _login(async_client, user.username)
    assert await _refresh_status(async_client, refresh) == 200

    user.password_reset_token = "synthetic-reset-token-290"
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db_session.commit()
    resp = await async_client.post(
        "/api/auth/reset-password",
        json={"token": "synthetic-reset-token-290", "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    assert await _refresh_status(async_client, refresh) == 401
