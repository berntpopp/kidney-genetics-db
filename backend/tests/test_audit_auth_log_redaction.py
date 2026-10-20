"""Regression test for #285: auth secrets must never reach any logger field."""

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote_plus

import pytest
from httpx import AsyncClient

from app.api.endpoints.admin_settings import get_settings_service
from app.core.logging.context import get_context
from app.core.logging.unified_logger import UnifiedLogger
from app.core.security import create_access_token
from app.main import app
from tests.fixtures.auth import get_or_create_user

PASSWORD = "Synthetic-Login-Pw-9f3K!"
NEW_PASSWORD = "Synthetic-Changed-Pw-7Qx!"
RESET_PASSWORD = "Synthetic-Reset-Pw-4Zm!"
RESET_TOKEN = "synthetic-reset-token-b81d"
JWT_SECRET = "synthetic-jwt-secret-value-0123456789abcdef"


@pytest.fixture
def captured_logs(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every UnifiedLogger call (message, kwargs and bound context) as text."""
    records: list[str] = []

    async def fake_log(self: UnifiedLogger, level: str, message: str, **kwargs: Any) -> None:
        records.append(repr((level, message, kwargs, get_context(), self._bound_context)))

    def fake_sync_log(self: UnifiedLogger, level: str, message: str, **kwargs: Any) -> None:
        records.append(repr((level, message, kwargs, get_context(), self._bound_context)))

    monkeypatch.setattr(UnifiedLogger, "log", fake_log)
    monkeypatch.setattr(UnifiedLogger, "sync_log", fake_sync_log)
    return records


@pytest.mark.integration
async def test_auth_secrets_never_reach_logs(
    async_client: AsyncClient, db_session, captured_logs: list[str]
) -> None:
    user = get_or_create_user(
        db_session, "audit_log_user", "audit_log_user@example.com", PASSWORD, "viewer"
    )

    # Login: password in form body, refresh token in Set-Cookie
    resp = await async_client.post(
        "/api/auth/login", data={"username": user.username, "password": PASSWORD}
    )
    assert resp.status_code == 200, resp.text
    refresh = resp.cookies["refresh_token"]
    access = resp.json()["access_token"]

    # Refresh via cookie and via legacy JSON body
    xhr = {"X-Requested-With": "XMLHttpRequest"}
    resp = await async_client.post("/api/auth/refresh", headers=xhr)
    assert resp.status_code == 200, resp.text
    async_client.cookies.clear()
    resp = await async_client.post(
        "/api/auth/refresh", headers=xhr, json={"refresh_token": refresh}
    )
    assert resp.status_code == 200, resp.text

    # Password change
    resp = await async_client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {access}"},
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 200, resp.text

    # Password reset with a valid token
    user.password_reset_token = RESET_TOKEN
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db_session.commit()
    resp = await async_client.post(
        "/api/auth/reset-password", json={"token": RESET_TOKEN, "new_password": RESET_PASSWORD}
    )
    assert resp.status_code == 200, resp.text

    assert captured_logs, "logger capture did not record anything"
    logged = "\n".join(captured_logs)
    for secret in (PASSWORD, NEW_PASSWORD, RESET_PASSWORD, RESET_TOKEN, refresh, access):
        assert secret not in logged
        assert quote_plus(secret) not in logged


class _StubSettingsService:
    async def update_setting(self, **kwargs: Any) -> dict[str, Any]:
        return {"requires_restart": True}


@pytest.mark.integration
async def test_admin_setting_secret_never_reaches_logs(
    async_client: AsyncClient, db_session, captured_logs: list[str]
) -> None:
    admin = get_or_create_user(
        db_session, "audit_log_admin", "audit_log_admin@example.com", PASSWORD, "admin"
    )
    app.dependency_overrides[get_settings_service] = _StubSettingsService
    resp = await async_client.put(
        "/api/admin/settings/1",
        headers={"Authorization": f"Bearer {create_access_token(subject=admin.username)}"},
        json={"value": JWT_SECRET, "change_reason": "rotate"},
    )
    assert resp.status_code == 200, resp.text

    assert captured_logs, "logger capture did not record anything"
    assert JWT_SECRET not in "\n".join(captured_logs)
