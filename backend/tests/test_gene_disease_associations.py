"""Reviewed gene-disease association workflow (#26)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ResourceConflictError
from app.core.security import create_access_token
from app.models.gene import Gene
from app.models.user import User
from app.schemas.gene_disease_association import AssociationCreate, AssociationUpdate
from app.services import gene_disease_association_service as service
from tests.fixtures.auth import get_or_create_user

URL = "/api/curation/associations"
RECORD = {
    "gene_symbol": "GDA26FAKE",
    "disease_id": "MONDO:0005300",
    "disease_name": "chronic kidney disease",
    "evidence_strength": "Definitive",
    "citations": ["12345678", "PMID:23456789", "12345678"],
    "evidence_summary": "Segregation in three families.",
}


def _auth(db_session, name: str, role: str = "curator") -> dict[str, str]:
    user = get_or_create_user(
        db_session, f"gda26_{name}", f"gda26_{name}@example.com", "Pw-1!", role
    )
    return {"Authorization": f"Bearer {create_access_token(subject=user.username)}"}


@pytest.fixture
def gene(db_session) -> Gene:
    gene = Gene(approved_symbol="GDA26FAKE", hgnc_id="HGNC:99926026")
    db_session.add(gene)
    db_session.commit()
    return gene


async def _create(client: AsyncClient, headers: dict, **overrides) -> dict:
    resp = await client.post(f"{URL}/", json={**RECORD, **overrides}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _public(client: AsyncClient) -> list[dict]:
    resp = await client.get(f"{URL}/", params={"gene_symbol": "gda26fake"})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.integration
async def test_full_workflow_and_public_visibility(async_client, db_session, gene) -> None:
    author, reviewer = _auth(db_session, "author"), _auth(db_session, "reviewer", "admin")
    rec = await _create(async_client, author)
    assert rec["status"] == "draft"
    assert rec["citations"] == ["PMID:12345678", "PMID:23456789"]
    assert rec["gene_symbol"] == "GDA26FAKE" and rec["created_at"] and rec["submitted_at"] is None
    assert await _public(async_client) == []

    resp = await async_client.patch(
        f"{URL}/{rec['id']}", json={"evidence_strength": "Strong"}, headers=author
    )
    assert resp.status_code == 200 and resp.json()["evidence_strength"] == "Strong"

    resp = await async_client.post(f"{URL}/{rec['id']}/submit", headers=author)
    assert resp.status_code == 200 and resp.json()["status"] == "in_review"
    assert resp.json()["submitted_at"]
    assert await _public(async_client) == []

    # in_review is visible to curators, not the public
    resp = await async_client.get(f"{URL}/workflow", params={"status": "in_review"}, headers=author)
    assert [r["id"] for r in resp.json()["data"] if r["gene_symbol"] == "GDA26FAKE"] == [rec["id"]]

    resp = await async_client.post(f"{URL}/{rec['id']}/publish", headers=reviewer)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "published" and body["reviewer_id"] != body["curator_id"]
    assert body["reviewed_at"] and body["published_at"]
    assert [r["id"] for r in await _public(async_client)] == [rec["id"]]

    # Published records are immutable until a reviewer returns them to draft
    resp = await async_client.patch(
        f"{URL}/{rec['id']}", json={"disease_name": "x"}, headers=author
    )
    assert resp.status_code == 409
    resp = await async_client.post(f"{URL}/{rec['id']}/return-to-draft", headers=reviewer)
    assert resp.status_code == 200 and resp.json()["status"] == "draft"
    assert resp.json()["published_at"] is None
    assert await _public(async_client) == []


@pytest.mark.integration
async def test_self_publication_and_self_return_forbidden(async_client, db_session, gene) -> None:
    author = _auth(db_session, "selfadmin", "admin")
    rec = await _create(async_client, author)
    await async_client.post(f"{URL}/{rec['id']}/submit", headers=author)
    for action in ("publish", "return-to-draft"):
        resp = await async_client.post(f"{URL}/{rec['id']}/{action}", headers=author)
        assert resp.status_code == 403, (action, resp.text)
    assert await _public(async_client) == []


@pytest.mark.integration
async def test_only_author_edits_or_submits_and_order_is_enforced(
    async_client, db_session, gene
) -> None:
    author, other = _auth(db_session, "author"), _auth(db_session, "other")
    rec = await _create(async_client, author)
    rid = rec["id"]
    assert (await async_client.patch(f"{URL}/{rid}", json={}, headers=other)).status_code == 403
    assert (await async_client.post(f"{URL}/{rid}/submit", headers=other)).status_code == 403
    # Drafts cannot be published or returned
    assert (await async_client.post(f"{URL}/{rid}/publish", headers=other)).status_code == 409
    assert (
        await async_client.post(f"{URL}/{rid}/return-to-draft", headers=other)
    ).status_code == 409
    assert (await async_client.post(f"{URL}/999999999/submit", headers=author)).status_code == 404


@pytest.mark.integration
async def test_anonymous_and_viewer_cannot_write_or_see_workflow(
    async_client, db_session, gene
) -> None:
    viewer = _auth(db_session, "viewer", "viewer")
    rid = (await _create(async_client, _auth(db_session, "author")))["id"]
    calls = [
        ("get", f"{URL}/workflow", None),
        ("post", f"{URL}/", RECORD),
        ("patch", f"{URL}/{rid}", {"disease_name": "x"}),
        ("post", f"{URL}/{rid}/submit", None),
        ("post", f"{URL}/{rid}/publish", None),
        ("post", f"{URL}/{rid}/return-to-draft", None),
    ]
    for method, url, body in calls:
        kwargs = {"json": body} if body is not None else {}
        assert (await getattr(async_client, method)(url, **kwargs)).status_code == 401, url
        resp = await getattr(async_client, method)(url, headers=viewer, **kwargs)
        assert resp.status_code == 403, url


@pytest.mark.integration
async def test_multiple_diseases_per_gene_but_no_duplicates(async_client, db_session, gene) -> None:
    author = _auth(db_session, "author")
    await _create(async_client, author)
    await _create(async_client, author, disease_id="OMIM:137920", disease_name="RCAD")
    resp = await async_client.get(
        f"{URL}/workflow", params={"gene_symbol": "GDA26FAKE"}, headers=author
    )
    assert {r["disease_id"] for r in resp.json()["data"]} == {"MONDO:0005300", "OMIM:137920"}
    resp = await async_client.post(f"{URL}/", json=RECORD, headers=author)
    assert resp.status_code == 409


@pytest.mark.integration
@pytest.mark.parametrize(
    "overrides",
    [
        {"disease_id": "HP:0000083"},  # phenotype, not a disease
        {"disease_id": "MONDO:123"},
        {"disease_id": "ORPHA:93"},
        {"disease_id": "OMIM:1379200"},
        {"citations": []},
        {"citations": ["PMID:abc"]},
        {"citations": ["doi:10.1/x"]},
        {"evidence_strength": "Very strong"},
        {"disease_name": "   "},
    ],
)
async def test_invalid_evidence_rejected(async_client, db_session, gene, overrides) -> None:
    # The app-wide request-validation handler answers 400 VALIDATION_ERROR
    resp = await async_client.post(
        f"{URL}/", json={**RECORD, **overrides}, headers=_auth(db_session, "author")
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.integration
async def test_unknown_gene_rejected(async_client, db_session, gene) -> None:
    resp = await async_client.post(
        f"{URL}/", json={**RECORD, "gene_symbol": "NOTAGENE26"}, headers=_auth(db_session, "author")
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.integration
async def test_hpo_error_explains_phenotype_vs_disease(async_client, db_session, gene) -> None:
    resp = await async_client.post(
        f"{URL}/", json={**RECORD, "disease_id": "HP:0000083"}, headers=_auth(db_session, "author")
    )
    assert "phenotype" in resp.text


@pytest.mark.integration
async def test_patch_cannot_null_required_fields(async_client, db_session, gene) -> None:
    author = _auth(db_session, "author")
    rid = (await _create(async_client, author))["id"]
    for field in ("disease_name", "citations", "disease_id", "evidence_strength"):
        resp = await async_client.patch(f"{URL}/{rid}", json={field: None}, headers=author)
        assert resp.status_code == 400, field
    resp = await async_client.patch(f"{URL}/{rid}", json={"citations": ["x"]}, headers=author)
    assert resp.status_code == 400
    resp = await async_client.patch(f"{URL}/{rid}", json={"evidence_summary": None}, headers=author)
    assert resp.status_code == 200 and resp.json()["evidence_summary"] is None


def test_no_pipeline_code_writes_expert_records() -> None:
    """Automated updates cannot overwrite expert decisions: only the curation
    model, schema, service and router reference the table."""
    app_dir = Path(__file__).resolve().parents[1] / "app"
    allowed = {
        "models/__init__.py",
        "models/gene_disease_association.py",
        "services/gene_disease_association_service.py",
        "api/endpoints/gene_disease_associations.py",
        "schemas/gene_disease_association.py",
        "main.py",
        "api/endpoints/auth.py",  # refuses to delete users who authored/reviewed records
    }
    hits = {
        str(p.relative_to(app_dir))
        for p in app_dir.rglob("*.py")
        if any(t in p.read_text() for t in ("gene_disease_association", "GeneDiseaseAssociation"))
    }
    assert hits <= allowed, hits - allowed


@pytest.mark.integration
async def test_deleting_an_author_is_refused_with_409(async_client, db_session, gene) -> None:
    """Provenance: the FK stays; deactivate the user instead of deleting them."""
    author = _auth(db_session, "deleted_author")
    await _create(async_client, author)
    author_id = db_session.query(User).filter(User.username == "gda26_deleted_author").one().id
    admin = _auth(db_session, "deleter", "admin")
    resp = await async_client.delete(f"/api/auth/users/{author_id}", headers=admin)
    assert resp.status_code == 409, resp.text
    assert "deactivate" in resp.text
    assert db_session.get(User, author_id) is not None


def test_unique_violation_on_commit_maps_to_409() -> None:
    """A concurrent duplicate that slips past the pre-check still answers 409."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.commit.side_effect = IntegrityError("INSERT", {}, Exception("uq_gda_gene_disease"))
    with patch.object(service.gene_crud, "get_by_symbol", return_value=MagicMock(id=1)):
        with pytest.raises(ResourceConflictError):
            service.create(db, AssociationCreate(**RECORD), MagicMock(id=1))
    db.rollback.assert_called_once()

    db.reset_mock()
    db.commit.side_effect = IntegrityError("UPDATE", {}, Exception("uq_gda_gene_disease"))
    record = MagicMock(curator_id=1, status="draft", gene_id=1, id=5)
    locked = db.query.return_value.filter.return_value.with_for_update.return_value
    locked.first.return_value = record
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
    with pytest.raises(ResourceConflictError):
        service.update(db, 5, AssociationUpdate(disease_id="OMIM:137920"), MagicMock(id=1))
    db.rollback.assert_called_once()
