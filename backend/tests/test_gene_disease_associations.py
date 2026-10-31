"""Reviewed gene-disease association workflow (#26)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ResourceConflictError
from app.core.security import create_access_token
from app.models.gene import Gene
from app.models.gene_disease_association import GeneDiseaseAssociationEvent
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


def _seen(record: dict) -> dict:
    """The review body: the version the reviewer looked at."""
    return {"expected_updated_at": record["updated_at"]}


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
    rec = resp.json()
    assert await _public(async_client) == []

    # in_review is visible to curators, not the public
    resp = await async_client.get(f"{URL}/workflow", params={"status": "in_review"}, headers=author)
    assert [r["id"] for r in resp.json()["data"] if r["gene_symbol"] == "GDA26FAKE"] == [rec["id"]]

    resp = await async_client.post(f"{URL}/{rec['id']}/publish", json=_seen(rec), headers=reviewer)
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
    resp = await async_client.post(
        f"{URL}/{rec['id']}/return-to-draft", json=_seen(body), headers=reviewer
    )
    assert resp.status_code == 200 and resp.json()["status"] == "draft"
    assert resp.json()["published_at"] is None
    assert await _public(async_client) == []


@pytest.mark.integration
async def test_self_publication_and_self_return_forbidden(async_client, db_session, gene) -> None:
    author = _auth(db_session, "selfadmin", "admin")
    rec = await _create(async_client, author)
    await async_client.post(f"{URL}/{rec['id']}/submit", headers=author)
    for action in ("publish", "return-to-draft"):
        resp = await async_client.post(
            f"{URL}/{rec['id']}/{action}", json=_seen(rec), headers=author
        )
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
    for action in ("publish", "return-to-draft"):
        resp = await async_client.post(f"{URL}/{rid}/{action}", json=_seen(rec), headers=other)
        assert resp.status_code == 409, action
    assert (await async_client.post(f"{URL}/999999999/submit", headers=author)).status_code == 404


@pytest.mark.integration
async def test_anonymous_and_viewer_cannot_write_or_see_workflow(
    async_client, db_session, gene
) -> None:
    viewer = _auth(db_session, "viewer", "viewer")
    rec = await _create(async_client, _auth(db_session, "author"))
    rid = rec["id"]
    calls = [
        ("get", f"{URL}/workflow", None),
        ("post", f"{URL}/", RECORD),
        ("patch", f"{URL}/{rid}", {"disease_name": "x"}),
        ("post", f"{URL}/{rid}/submit", None),
        ("post", f"{URL}/{rid}/publish", _seen(rec)),
        ("post", f"{URL}/{rid}/return-to-draft", _seen(rec)),
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
        {"citations": ["0"]},  # no PMID 0 (#376)
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
        "services/gene_curator_import.py",  # admin-triggered, drafts only (#448)
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
    record = MagicMock(
        curator_id=1,
        status="draft",
        gene_id=1,
        id=5,
        relationship_type="mendelian",
        evidence_strength="Strong",
        source="kgdb",
        moi=None,
        external_id=None,
        external_url=None,
    )
    locked = db.query.return_value.filter.return_value.with_for_update.return_value
    locked.first.return_value = record
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
    with pytest.raises(ResourceConflictError):
        service.update(db, 5, AssociationUpdate(disease_id="OMIM:137920"), MagicMock(id=1))
    db.rollback.assert_called_once()


@pytest.mark.integration
async def test_zero_padded_pmids_are_one_citation(async_client, db_session, gene) -> None:
    rec = await _create(
        async_client, _auth(db_session, "author"), citations=["000000001", "PMID:1", "1"]
    )
    assert rec["citations"] == ["PMID:1"]


@pytest.mark.integration
async def test_reviewer_cannot_decide_on_a_version_they_did_not_see(
    async_client, db_session, gene
) -> None:
    """#376: an edited and resubmitted record answers 409 to a reviewer's stale view."""
    author, reviewer = _auth(db_session, "author"), _auth(db_session, "reviewer")
    rid = (await _create(async_client, author))["id"]
    seen = (await async_client.post(f"{URL}/{rid}/submit", headers=author)).json()

    other = _auth(db_session, "other")
    resp = await async_client.post(f"{URL}/{rid}/return-to-draft", json=_seen(seen), headers=other)
    assert resp.status_code == 200
    resp = await async_client.patch(
        f"{URL}/{rid}", json={"evidence_strength": "Refuted"}, headers=author
    )
    assert resp.status_code == 200
    current = (await async_client.post(f"{URL}/{rid}/submit", headers=author)).json()

    for action in ("publish", "return-to-draft"):
        resp = await async_client.post(f"{URL}/{rid}/{action}", json=_seen(seen), headers=reviewer)
        assert resp.status_code == 409, (action, resp.text)
        assert "reload" in resp.text
    resp = await async_client.post(f"{URL}/{rid}/publish", json=_seen(current), headers=reviewer)
    assert resp.status_code == 200 and resp.json()["evidence_strength"] == "Refuted"


@pytest.mark.integration
async def test_every_action_leaves_a_snapshot(async_client, db_session, gene) -> None:
    """#376: who published which version, and who retracted it, stays answerable."""
    author, reviewer = _auth(db_session, "author"), _auth(db_session, "reviewer")
    rec = await _create(async_client, author)
    rid = rec["id"]
    await async_client.patch(f"{URL}/{rid}", json={"evidence_strength": "Strong"}, headers=author)
    rec = (await async_client.post(f"{URL}/{rid}/submit", headers=author)).json()
    rec = (
        await async_client.post(f"{URL}/{rid}/publish", json=_seen(rec), headers=reviewer)
    ).json()
    await async_client.post(f"{URL}/{rid}/return-to-draft", json=_seen(rec), headers=reviewer)

    events = (
        db_session.query(GeneDiseaseAssociationEvent)
        .filter_by(association_id=rid)
        .order_by(GeneDiseaseAssociationEvent.id)
        .all()
    )
    author_id, reviewer_id = rec["curator_id"], rec["reviewer_id"]
    assert [(e.action, e.user_id, e.snapshot["status"]) for e in events] == [
        ("create", author_id, "draft"),
        ("update", author_id, "draft"),
        ("submit", author_id, "in_review"),
        ("publish", reviewer_id, "published"),
        ("return", reviewer_id, "draft"),
    ]
    published = events[3].snapshot
    assert published["evidence_strength"] == "Strong" and published["published_at"]


@pytest.mark.integration
async def test_deleting_an_earlier_reviewer_is_refused_with_409(
    async_client, db_session, gene
) -> None:
    """Their events keep them referenced after reviewer_id moved to someone else (#376)."""
    author, first, second = (_auth(db_session, n) for n in ("author", "first", "second"))
    rid = (await _create(async_client, author))["id"]
    rec = (await async_client.post(f"{URL}/{rid}/submit", headers=author)).json()
    rec = (
        await async_client.post(f"{URL}/{rid}/return-to-draft", json=_seen(rec), headers=first)
    ).json()
    rec = (await async_client.post(f"{URL}/{rid}/submit", headers=author)).json()
    rec = (await async_client.post(f"{URL}/{rid}/publish", json=_seen(rec), headers=second)).json()

    first_id = db_session.query(User).filter(User.username == "gda26_first").one().id
    assert rec["reviewer_id"] != first_id
    admin = _auth(db_session, "deleter", "admin")
    resp = await async_client.delete(f"/api/auth/users/{first_id}", headers=admin)
    assert resp.status_code == 409, resp.text


# --- relationship type, MOI, provenance and diagnostics (#437) ---

GC = {
    "source": "gene_curator",
    "external_id": "GC-1",
    "external_url": "https://example.org/curations/1",
    "external_curator": "Curator A",
    "external_reviewer": "Reviewer B",
    "methodology": "Kidney Gene Curation",
    "methodology_version": "draft iteration 3",
    "scores": {"genetic": 10, "experimental": 5, "total": 15},
}
DIAGNOSTICS = {
    "recommended_transcript": {
        "refseq": None,
        "ensembl": "ENST00000620103.4",
        "mane_status": "none",
        "legacy_transcript": "NM_002456.5",
        "numbering_conversion": "No MANE Select; literature uses NM_002456.5.",
    },
    "detectability": [
        {
            "challenge": "VNTR frameshift (dupC) not called by short-read pipelines",
            "share_of_variants": "~99%",
            "affected_variants": None,
            "methods": ["long_read_sequencing"],
            "tools": [
                {"name": "VNtyper 2", "url": "https://example.org/vntyper", "pmid_or_doi": None}
            ],
            "negative_report_does_not_exclude": True,
            "sources": ["PMID:12345678"],
        }
    ],
    "resources": [
        {
            "type": "patient_organisation",
            "name": "Example ADTKD group",
            "url": "https://example.org/adtkd",
            "language": "de",
            "audiences": ["patients"],
            "maintainer": None,
            "conflict_of_interest": None,
            "verified": {"method": "fetched", "date": "2026-10-30"},
        }
    ],
}


async def _post(client: AsyncClient, headers: dict, **overrides):
    return await client.post(f"{URL}/", json={**RECORD, **overrides}, headers=headers)


@pytest.mark.integration
async def test_create_susceptibility_record(async_client, db_session, gene) -> None:
    author, reviewer = _auth(db_session, "author"), _auth(db_session, "reviewer", "admin")
    rec = await _create(
        async_client,
        author,
        relationship_type="susceptibility",
        evidence_strength="Likely association",
        moi="HP:0001426",
    )
    rec = (await async_client.post(f"{URL}/{rec['id']}/submit", headers=author)).json()
    resp = await async_client.post(f"{URL}/{rec['id']}/publish", json=_seen(rec), headers=reviewer)
    assert resp.status_code == 200, resp.text
    [public] = await _public(async_client)
    assert public["relationship_type"] == "susceptibility"
    assert public["moi"] == "HP:0001426" and public["moi_label"] == "Non-Mendelian inheritance"


@pytest.mark.integration
async def test_strength_must_match_relationship_type(async_client, db_session, gene) -> None:
    author = _auth(db_session, "author")
    resp = await _post(async_client, author, relationship_type="susceptibility")
    assert resp.status_code == 400, resp.text
    rec = await _create(async_client, author)
    resp = await async_client.patch(
        f"{URL}/{rec['id']}", json={"relationship_type": "susceptibility"}, headers=author
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.integration
async def test_no_known_only_mendelian(async_client, db_session, gene) -> None:
    author = _auth(db_session, "author")
    no_known = {"evidence_strength": "No Known Disease Relationship"}
    assert (await _post(async_client, author, **no_known)).status_code == 201
    resp = await _post(
        async_client,
        author,
        disease_id="MONDO:0000001",
        relationship_type="susceptibility",
        **no_known,
    )
    assert resp.status_code == 400


@pytest.mark.integration
async def test_gene_curator_source_needs_provenance(async_client, db_session, gene) -> None:
    author = _auth(db_session, "author")
    resp = await _post(async_client, author, **{**GC, "external_url": None})
    assert resp.status_code == 400, resp.text
    rec = await _create(async_client, author, **GC)
    assert rec["source"] == "gene_curator" and rec["scores"]["total"] == 15
    resp = await _post(async_client, author, disease_id="MONDO:0000002", **GC)
    assert resp.status_code == 409, resp.text


@pytest.mark.integration
@pytest.mark.parametrize(
    "overrides",
    [
        {"external_url": "javascript:alert(1)"},
        {
            "diagnostics": {
                "resources": [{**DIAGNOSTICS["resources"][0], "url": "data:text/html,x"}]
            }
        },
        {
            "diagnostics": {
                "detectability": [
                    {**DIAGNOSTICS["detectability"][0], "tools": [{"name": "x", "url": "ftp://x"}]}
                ]
            }
        },
    ],
)
async def test_rejects_non_http_links(async_client, db_session, gene, overrides) -> None:
    resp = await _post(async_client, _auth(db_session, "author"), **overrides)
    assert resp.status_code == 400, resp.text


@pytest.mark.integration
async def test_diagnostics_round_trip(async_client, db_session, gene) -> None:
    author = _auth(db_session, "author")
    rec = await _create(async_client, author, diagnostics=DIAGNOSTICS)
    assert rec["diagnostics"] == DIAGNOSTICS
    bad_key = {**DIAGNOSTICS, "surprise": 1}
    assert (
        await _post(async_client, author, disease_id="MONDO:0000003", diagnostics=bad_key)
    ).status_code == 400
    bad_mane = {
        **DIAGNOSTICS,
        "recommended_transcript": {**DIAGNOSTICS["recommended_transcript"], "mane_status": "maybe"},
    }
    assert (
        await _post(async_client, author, disease_id="MONDO:0000004", diagnostics=bad_mane)
    ).status_code == 400


@pytest.mark.integration
async def test_unique_per_moi(async_client, db_session, gene) -> None:
    author = _auth(db_session, "author")
    assert (await _post(async_client, author, moi="HP:0000006")).status_code == 201
    assert (await _post(async_client, author, moi="HP:0000007")).status_code == 201
    assert (await _post(async_client, author, moi="HP:0000006")).status_code == 409
    other = {"disease_id": "MONDO:0000005"}
    assert (await _post(async_client, author, **other)).status_code == 201
    assert (await _post(async_client, author, **other)).status_code == 409
    assert (await _post(async_client, author, moi="HP:9999999")).status_code == 400


@pytest.mark.integration
async def test_imported_record_needs_distinct_confirmer(async_client, db_session, gene) -> None:
    author, other = _auth(db_session, "author"), _auth(db_session, "reviewer", "admin")
    rec = await _create(async_client, author, **GC)
    rec = (await async_client.post(f"{URL}/{rec['id']}/submit", headers=author)).json()
    resp = await async_client.post(f"{URL}/{rec['id']}/publish", json=_seen(rec), headers=author)
    assert resp.status_code == 403
    resp = await async_client.post(f"{URL}/{rec['id']}/publish", json=_seen(rec), headers=other)
    assert resp.status_code == 200 and resp.json()["external_curator"] == "Curator A"


def test_schema_vocabularies_match_the_model() -> None:
    from typing import get_args

    from app.models.gene_disease_association import EVIDENCE_STRENGTHS, MOI_TERMS
    from app.schemas.gene_disease_association import EvidenceStrength, Moi

    assert set(get_args(Moi)) == set(MOI_TERMS)
    assert set(get_args(EvidenceStrength)) == set(EVIDENCE_STRENGTHS)
