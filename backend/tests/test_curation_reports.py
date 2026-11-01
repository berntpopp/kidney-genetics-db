"""Public curation reports, curator inbox and notification preferences."""

from datetime import datetime, timezone

import pytest
from fastapi import BackgroundTasks

from app.core.config import settings
from app.core.security import create_access_token
from app.models.curation_report import CurationReport
from app.models.gene import Gene
from app.models.gene_disease_association import GeneDiseaseAssociation
from app.services import notifications
from tests.fixtures.auth import get_or_create_user

URL = "/api/curation/reports"


def _auth(db_session, name: str, role: str) -> dict[str, str]:
    user = get_or_create_user(db_session, f"rep_{name}", f"rep_{name}@example.com", "Pw-1!", role)
    return {"Authorization": f"Bearer {create_access_token(subject=user.username)}"}


@pytest.fixture
def gene(db_session) -> Gene:
    gene = Gene(approved_symbol="REPFAKE", hgnc_id="HGNC:99926027")
    admin = get_or_create_user(db_session, "rep_rev", "rep_rev@example.com", "Pw-1!", "admin")
    author = get_or_create_user(db_session, "rep_aut", "rep_aut@example.com", "Pw-1!", "curator")
    db_session.add(gene)
    db_session.flush()
    db_session.add(
        GeneDiseaseAssociation(
            gene_id=gene.id,
            disease_id="MONDO:0005300",
            disease_name="chronic kidney disease",
            relationship_type="mendelian",
            evidence_strength="Definitive",
            source="kgdb",
            status="published",
            published_at=datetime.now(timezone.utc),
            curator_id=author.id,
            reviewer_id=admin.id,
            citations=["PMID:12345678"],
        )
    )
    db_session.commit()
    return gene


def _body(**kw) -> dict:
    return {
        "gene_symbol": "repfake",
        "kind": "problem",
        "message": "The inheritance is wrong.",
        "reporter_email": "expert@example.org",
        **kw,
    }


@pytest.mark.integration
async def test_public_report_is_stored_and_never_echoed(async_client, db_session, gene) -> None:
    resp = await async_client.post(f"{URL}/", json=_body())
    assert resp.status_code == 202 and resp.json() == {"status": "received"}
    assert db_session.query(CurationReport).filter_by(gene_id=gene.id).count() == 1


@pytest.mark.integration
async def test_honeypot_stores_nothing(async_client, db_session, gene) -> None:
    resp = await async_client.post(f"{URL}/", json=_body(website="http://spam"))
    assert resp.status_code == 202
    assert db_session.query(CurationReport).count() == 0


@pytest.mark.integration
async def test_unknown_gene_or_unpublished_is_404(async_client, db_session, gene) -> None:
    resp = await async_client.post(f"{URL}/", json=_body(gene_symbol="NOSUCHGENE"))
    assert resp.status_code == 404
    resp = await async_client.post(f"{URL}/", json=_body(association_id=10**9))
    assert resp.status_code == 404


@pytest.mark.integration
async def test_curator_lists_and_handles_viewer_forbidden(async_client, db_session, gene) -> None:
    await async_client.post(f"{URL}/", json=_body())
    curator, viewer = _auth(db_session, "cur", "curator"), _auth(db_session, "view", "viewer")

    assert (await async_client.get(f"{URL}/")).status_code == 401
    assert (await async_client.get(f"{URL}/", headers=viewer)).status_code == 403

    resp = await async_client.get(f"{URL}/", params={"status": "open"}, headers=curator)
    row = resp.json()["data"][0]
    assert row["gene_symbol"] == "REPFAKE" and row["reporter_email"] == "expert@example.org"
    assert resp.json()["meta"]["open_count"] >= 1

    resp = await async_client.patch(
        f"{URL}/{row['id']}", json={"status": "resolved"}, headers=viewer
    )
    assert resp.status_code == 403
    resp = await async_client.patch(
        f"{URL}/{row['id']}", json={"status": "resolved"}, headers=curator
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved" and resp.json()["handled_by"]
    resp = await async_client.patch(f"{URL}/{row['id']}", json={"status": "open"}, headers=curator)
    assert resp.json()["handled_by"] is None


@pytest.mark.integration
async def test_prefs_default_on_and_toggle(async_client, db_session) -> None:
    viewer = _auth(db_session, "prefs", "viewer")
    resp = await async_client.get("/api/users/me/notification-prefs", headers=viewer)
    assert {p["event"] for p in resp.json()} == set(notifications.EVENTS)
    assert all(p["enabled"] for p in resp.json())
    resp = await async_client.put(
        "/api/users/me/notification-prefs", json={"curation_report": False}, headers=viewer
    )
    assert {p["event"]: p["enabled"] for p in resp.json()}["curation_report"] is False
    resp = await async_client.put(
        "/api/users/me/notification-prefs", json={"nope": True}, headers=viewer
    )
    assert resp.status_code == 422


@pytest.mark.integration
def test_notify_skips_disabled_inactive_and_no_smtp(db_session, monkeypatch) -> None:
    on = get_or_create_user(db_session, "rep_on", "on@example.com", "Pw-1!", "curator")
    off = get_or_create_user(db_session, "rep_off", "off@example.com", "Pw-1!", "curator")
    gone = get_or_create_user(db_session, "rep_gone", "gone@example.com", "Pw-1!", "curator", False)
    notifications.set_pref(db_session, off, "curation_report", False)
    db_session.commit()

    tasks = BackgroundTasks()
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    notifications.notify(db_session, "curation_report", [on], "s", "b", tasks)
    assert tasks.tasks == []

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.org")
    notifications.notify(db_session, "curation_report", [on, off, gone], "s", "b", tasks)
    assert [t.args[0] for t in tasks.tasks] == [on.id]
