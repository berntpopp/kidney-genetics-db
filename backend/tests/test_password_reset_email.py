"""Forgot-password emails a hashed, single-use, one-hour link; off without SMTP."""

from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from app.api.endpoints import auth
from app.core import email
from app.core.config import settings
from app.core.security import hash_reset_token
from tests.fixtures.auth import get_or_create_user

PASSWORD = "Synthetic-Old-Pw-3Lk!"
NEW_PASSWORD = "Synthetic-New-Pw-8Rt!"


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, str]]:
    outbox: list[tuple[str, str, str]] = []

    async def fake_send(to: str, subject: str, body: str) -> None:
        outbox.append((to, subject, body))

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.org")
    monkeypatch.setattr(auth, "send_email", fake_send)
    return outbox


@pytest.mark.integration
async def test_forgot_password_is_off_without_smtp(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    resp = await async_client.post("/api/auth/forgot-password", json={"email": "a@example.org"})
    assert resp.status_code == 503
    assert "administrator" in resp.json()["error"]["detail"]


@pytest.mark.integration
async def test_reset_link_works_once_and_only_its_hash_is_stored(
    async_client: AsyncClient, db_session, sent
) -> None:
    user = get_or_create_user(
        db_session, "reset_mail_user", "reset@example.org", PASSWORD, "viewer"
    )

    resp = await async_client.post("/api/auth/forgot-password", json={"email": "reset@example.org"})
    assert resp.status_code == 200, resp.text
    [(to, _subject, body)] = sent
    assert to == "reset@example.org"
    link = next(line for line in body.splitlines() if "/reset-password?token=" in line)
    assert link.startswith(f"{settings.SITE_URL}/reset-password?token=")
    token = parse_qs(urlparse(link).query)["token"][0]

    db_session.refresh(user)
    assert user.password_reset_token == hash_reset_token(token)  # never the usable token

    body_json = {"token": token, "new_password": NEW_PASSWORD}
    assert (await async_client.post("/api/auth/reset-password", json=body_json)).status_code == 200
    assert (await async_client.post("/api/auth/reset-password", json=body_json)).status_code == 400
    login = await async_client.post(
        "/api/auth/login", data={"username": user.username, "password": NEW_PASSWORD}
    )
    assert login.status_code == 200


@pytest.mark.integration
async def test_unknown_email_gets_the_same_answer_and_no_mail(
    async_client: AsyncClient, sent
) -> None:
    resp = await async_client.post("/api/auth/forgot-password", json={"email": "no@example.org"})
    assert resp.status_code == 200
    assert "If an account with that email exists" in resp.json()["message"]
    assert sent == []


@pytest.mark.unit
async def test_send_email_uses_starttls_and_login(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: float) -> None:
            calls.append(f"connect {host}:{port}")

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *exc: object) -> None:
            calls.append("quit")

        def starttls(self, context: object) -> None:
            calls.append("starttls")

        def login(self, user: str, password: str) -> None:
            calls.append(f"login {user}")

        def send_message(self, message: object) -> None:
            calls.append(f"send {message['To']}")  # type: ignore[index]

    monkeypatch.setattr(email.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.org")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_SECURITY", "starttls")
    monkeypatch.setattr(settings, "SMTP_USER", "mailer")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", SecretStr("synthetic-smtp-pw"))

    await email.send_email("to@example.org", "Subject", "Body")

    assert calls == [
        "connect smtp.example.org:587",
        "starttls",
        "login mailer",
        "send to@example.org",
        "quit",
    ]
