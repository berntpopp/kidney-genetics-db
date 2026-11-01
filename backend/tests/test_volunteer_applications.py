"""Public volunteer applications and the admin decision flow."""

from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.core.security import create_access_token
from app.models.gene import Gene
from app.models.user import User
from app.models.volunteer_application import VolunteerApplication
from tests.fixtures.auth import get_or_create_user

URL = "/api/volunteer-applications"


def _auth(db_session, name: str, role: str) -> dict[str, str]:
    user = get_or_create_user(db_session, f"vol_{name}", f"vol_{name}@example.com", "Pw-1!", role)
    return {"Authorization": f"Bearer {create_access_token(subject=user.username)}"}


@pytest.fixture
def gene(db_session) -> Gene:
    gene = Gene(approved_symbol="VOLFAKE", hgnc_id="HGNC:99926028")
    db_session.add(gene)
    db_session.commit()
    return gene


@pytest.fixture
def mail(monkeypatch) -> AsyncMock:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.org")
    sender = AsyncMock()
    monkeypatch.setattr("app.services.notifications.send_email", sender)
    return sender


def _body(**kw) -> dict:
    return {
        "gene_symbol": "volfake",
        "name": "Ada Expert",
        "email": "ada@example.org",
        "orcid": "0000-0002-1825-009X",
        "motivation": "I study this gene.",
        **kw,
    }


async def _apply(async_client, **kw) -> None:
    assert (await async_client.post(f"{URL}/", json=_body(**kw))).status_code == 202


@pytest.mark.integration
async def test_submit_stores_and_confirms(async_client, db_session, gene, mail) -> None:
    resp = await async_client.post(f"{URL}/", json=_body())
    assert resp.status_code == 202 and resp.json() == {"status": "received"}
    assert db_session.query(VolunteerApplication).filter_by(gene_id=gene.id).count() == 1
    assert "ada@example.org" in [c.args[0] for c in mail.await_args_list]


@pytest.mark.integration
async def test_honeypot_duplicate_unknown_gene_and_bad_orcid(
    async_client, db_session, gene, mail
) -> None:
    await _apply(async_client, website="http://spam")
    assert db_session.query(VolunteerApplication).count() == 0
    await _apply(async_client)
    await _apply(async_client, email="ADA@example.org")
    assert db_session.query(VolunteerApplication).count() == 1
    assert (await async_client.post(f"{URL}/", json=_body(gene_symbol="NOSUCH"))).status_code == 404
    assert (await async_client.post(f"{URL}/", json=_body(orcid="123"))).status_code == 400


@pytest.mark.integration
async def test_admin_list_and_forbidden(async_client, db_session, gene) -> None:
    await _apply(async_client)
    admin, curator = _auth(db_session, "adm1", "admin"), _auth(db_session, "cur1", "curator")
    assert (await async_client.get(f"{URL}/")).status_code == 401
    assert (await async_client.get(f"{URL}/", headers=curator)).status_code == 403
    resp = await async_client.get(f"{URL}/", params={"status": "pending"}, headers=admin)
    row = resp.json()["data"][0]
    assert row["gene_symbol"] == "VOLFAKE" and row["email"] == "ada@example.org"
    assert resp.json()["meta"]["pending_count"] >= 1
    forbidden = await async_client.post(
        f"{URL}/{row['id']}/decision", json={"decision": "approved"}, headers=curator
    )
    assert forbidden.status_code == 403


@pytest.mark.integration
async def test_approve_creates_curator_with_invite_and_cannot_decide_twice(
    async_client, db_session, gene, mail
) -> None:
    await _apply(async_client)
    admin = _auth(db_session, "adm2", "admin")
    app_id = db_session.query(VolunteerApplication).one().id
    mail.reset_mock()

    resp = await async_client.post(
        f"{URL}/{app_id}/decision", json={"decision": "approved", "note": "Welcome"}, headers=admin
    )
    assert resp.status_code == 200 and resp.json()["status"] == "approved"
    user = db_session.query(User).filter_by(email="ada@example.org").one()
    assert user.role == "curator" and user.is_active and user.password_reset_token
    assert resp.json()["user_id"] == user.id
    to, _subject, text = mail.await_args.args
    assert to == "ada@example.org"
    assert f"{settings.SITE_URL}/reset-password?token=" in text and "Welcome" in text

    again = await async_client.post(
        f"{URL}/{app_id}/decision", json={"decision": "rejected"}, headers=admin
    )
    assert again.status_code == 409


@pytest.mark.integration
async def test_approve_links_existing_viewer_and_raises_role(
    async_client, db_session, gene, mail
) -> None:
    viewer = get_or_create_user(db_session, "vol_exist", "ada@example.org", "Pw-1!", "viewer")
    await _apply(async_client)
    admin = _auth(db_session, "adm3", "admin")
    app_id = db_session.query(VolunteerApplication).one().id
    resp = await async_client.post(
        f"{URL}/{app_id}/decision", json={"decision": "approved"}, headers=admin
    )
    assert resp.json()["user_id"] == viewer.id
    db_session.refresh(viewer)
    assert viewer.role == "curator"
    assert "reset-password" not in mail.await_args.args[2]


@pytest.mark.integration
async def test_reject_emails_note_and_creates_no_user(async_client, db_session, gene, mail) -> None:
    await _apply(async_client)
    admin = _auth(db_session, "adm4", "admin")
    app_id = db_session.query(VolunteerApplication).one().id
    resp = await async_client.post(
        f"{URL}/{app_id}/decision",
        json={"decision": "rejected", "note": "Not a fit right now"},
        headers=admin,
    )
    assert resp.json()["status"] == "rejected" and resp.json()["user_id"] is None
    assert db_session.query(User).filter_by(email="ada@example.org").count() == 0
    assert "Not a fit right now" in mail.await_args.args[2]


@pytest.mark.integration
async def test_invite_url_returned_only_when_email_disabled(
    async_client, db_session, gene, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    await _apply(async_client)
    admin = _auth(db_session, "adm5", "admin")
    app_id = db_session.query(VolunteerApplication).one().id
    resp = await async_client.post(
        f"{URL}/{app_id}/decision", json={"decision": "approved"}, headers=admin
    )
    assert "/reset-password?token=" in resp.json()["invite_url"]
    listing = await async_client.get(URL + "/", headers=admin)
    assert all("invite_url" not in row for row in listing.json()["data"])
