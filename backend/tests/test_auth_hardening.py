"""Login lock, client IP, session revocation and token reuse (#374)."""

import importlib
import inspect
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from starlette.requests import Request

from app.api.endpoints import auth
from app.core.rate_limit import _get_real_ip, limiter
from app.core.security import create_access_token, hash_reset_token
from tests.fixtures.auth import get_or_create_user

PASSWORD = "Synthetic-Pw-374-Ok!"
XHR = {"X-Requested-With": "XMLHttpRequest"}


@pytest.fixture
def user(db_session):
    return get_or_create_user(db_session, "hard374", "hard374@example.com", PASSWORD, "curator")


@pytest.fixture
def admin(db_session):
    return get_or_create_user(db_session, "hard374a", "hard374a@example.com", PASSWORD, "admin")


def _bearer(user) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject=user.username)}"}


async def _login(client: AsyncClient, password: str = PASSWORD, name: str = "hard374"):
    return await client.post("/api/auth/login", data={"username": name, "password": password})


@pytest.mark.integration
async def test_locked_account_answers_like_a_wrong_password(
    async_client: AsyncClient, db_session, user
) -> None:
    session = _bearer(user)
    for _ in range(5):
        assert (await _login(async_client, "wrong")).status_code == 401
    db_session.refresh(user)
    locked_until = user.locked_until
    assert locked_until is not None

    # The right password no longer tells (it was 423), and guesses do not extend the lock
    assert (await _login(async_client)).status_code == 401
    assert (await _login(async_client, "wrong")).status_code == 401
    db_session.refresh(user)
    assert user.locked_until == locked_until
    # An open session keeps working (was 423)
    assert (await async_client.get("/api/auth/me", headers=session)).status_code == 200


@pytest.mark.integration
async def test_unknown_names_cost_one_bcrypt_check(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    real = auth.verify_password
    monkeypatch.setattr(auth, "verify_password", lambda p, h: calls.append(h) or real(p, h))
    assert (await _login(async_client, name="nobody-374")).status_code == 401
    assert calls == [auth._dummy_hash()]


def _request(headers: dict[str, str]) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": ("172.18.0.5", 1234)})


@pytest.mark.unit
def test_client_ip_ignores_client_written_forwarded_for() -> None:
    assert _get_real_ip(_request({"X-Forwarded-For": "203.0.113.7"})) == "172.18.0.5"
    assert _get_real_ip(_request({"X-Real-IP": "198.51.100.2"})) == "198.51.100.2"


@pytest.mark.unit
def test_rate_limited_endpoints_take_request_and_response() -> None:
    """slowapi answers 500 at runtime without them; tests run with the limiter off."""
    import app.main  # noqa: F401 - registers every router's limits

    for qualified in limiter._route_limits:
        module, name = qualified.rsplit(".", 1)
        params = inspect.signature(getattr(importlib.import_module(module), name)).parameters
        assert {"request", "response"} <= set(params), qualified
    assert "app.api.endpoints.auth.forgot_password" in limiter._route_limits


@pytest.mark.integration
async def test_admin_cannot_deactivate_themselves(async_client: AsyncClient, admin) -> None:
    resp = await async_client.put(
        f"/api/auth/users/{admin.id}", json={"is_active": False}, headers=_bearer(admin)
    )
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.parametrize("change", [{"role": "viewer"}, {"is_active": False}])
async def test_role_change_or_deactivation_ends_refresh(
    async_client: AsyncClient, db_session, user, admin, change
) -> None:
    refresh = (await _login(async_client)).cookies["refresh_token"]
    async_client.cookies.clear()
    resp = await async_client.put(f"/api/auth/users/{user.id}", json=change, headers=_bearer(admin))
    assert resp.status_code == 200, resp.text
    if "is_active" in change:  # re-activation must not bring the old session back
        await async_client.put(
            f"/api/auth/users/{user.id}", json={"is_active": True}, headers=_bearer(admin)
        )
    resp = await async_client.post(
        "/api/auth/refresh", headers=XHR, json={"refresh_token": refresh}
    )
    assert resp.status_code == 401


@pytest.mark.integration
async def test_password_change_voids_an_older_reset_link(
    async_client: AsyncClient, db_session, user
) -> None:
    user.password_reset_token = hash_reset_token("older-link-374")
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db_session.commit()
    resp = await async_client.post(
        "/api/auth/change-password",
        headers=_bearer(user),
        json={"current_password": PASSWORD, "new_password": "Synthetic-New-374-Ok!"},
    )
    assert resp.status_code == 200
    resp = await async_client.post(
        "/api/auth/reset-password",
        json={"token": "older-link-374", "new_password": "Synthetic-Evil-374-Ok!"},
    )
    assert resp.status_code == 400


@pytest.mark.integration
async def test_logout_clears_the_refresh_cookie(async_client: AsyncClient, user) -> None:
    resp = await async_client.post("/api/auth/logout", headers=_bearer(user))
    assert resp.status_code == 200
    cookie = resp.headers["set-cookie"]
    assert cookie.startswith("refresh_token=") and "Max-Age=0" in cookie and "/api/auth" in cookie


@pytest.mark.integration
async def test_token_from_before_the_account_existed_is_refused(
    async_client: AsyncClient, db_session, user
) -> None:
    """A deleted user's token must not authenticate a later account with the same name."""
    headers = _bearer(user)
    user.created_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    db_session.commit()
    assert (await async_client.get("/api/auth/me", headers=headers)).status_code == 401


@pytest.mark.integration
async def test_staging_texts_need_a_curator(async_client: AsyncClient, user) -> None:
    for url in ("/api/staging/staging/pending", "/api/staging/normalization/logs"):
        assert (await async_client.get(url)).status_code == 401, url
        assert (await async_client.get(url, headers=_bearer(user))).status_code == 200, url
