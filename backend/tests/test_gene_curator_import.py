"""One-shot Gene Curator export upload (#448), with a fixture in the pinned export v1 shape."""

import copy
import json
from pathlib import Path

import pytest

from app.core.security import create_access_token
from app.models.gene import Gene
from app.models.gene_disease_association import GeneDiseaseAssociation as GDA
from app.models.gene_disease_association import GeneDiseaseAssociationEvent as Event
from app.models.user import User
from app.schemas.gene_disease_association import AssociationUpdate, ReviewDecision
from app.services import gene_curator_import as gc
from app.services import gene_disease_association_service as workflow
from tests.fixtures.auth import get_or_create_user

URL = "/api/admin/gene-curator/import"
PAGE = json.loads((Path(__file__).parent / "fixtures/gene_curator_export.json").read_text())
MENDELIAN, SUSCEPTIBILITY, PROBABLE, DIGENIC, NOT_IN_KGDB = PAGE["items"]


def _row(base: dict, **changes) -> dict:
    return {**copy.deepcopy(base), **changes}


def _page(*items: dict) -> dict:
    return {**PAGE, "items": list(items)}


def _file(doc) -> dict:
    content = doc if isinstance(doc, bytes) else json.dumps(doc).encode()
    return {"file": ("export.json", content, "application/json")}


def _bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject=user.username)}"}


@pytest.fixture
def admin(db_session):
    return get_or_create_user(
        db_session, "gc448_admin", "gc448_admin@example.com", "Pw-1!", "admin"
    )


@pytest.fixture
def curator(db_session):
    return get_or_create_user(db_session, "gc448_cur", "gc448_cur@example.com", "Pw-1!", "curator")


@pytest.fixture
def genes(db_session):
    rows = [
        Gene(approved_symbol="GC448A", hgnc_id="HGNC:99944801"),
        Gene(approved_symbol="GC448B", hgnc_id="HGNC:99944802"),
    ]
    db_session.add_all(rows)
    db_session.commit()
    return rows


def _records(db_session) -> list[GDA]:
    return db_session.query(GDA).filter(GDA.source == "gene_curator").order_by(GDA.id).all()


def _events(db_session, record: GDA) -> list[tuple[str, int]]:
    rows = db_session.query(Event.action, Event.user_id).filter(Event.association_id == record.id)
    return [tuple(r) for r in rows.order_by(Event.id)]


def test_fixture_matches_pinned_schema_and_extra_fields_pass() -> None:
    assert len(gc.parse_export(json.dumps(PAGE).encode())) == 5
    added = _page(_row(MENDELIAN, field_added_in_v1={"x": 1}))
    assert len(gc.parse_export(json.dumps([added, _page()]).encode())) == 1


@pytest.mark.parametrize(
    "doc, error",
    [
        (_page(_row(MENDELIAN, total_score="16")), "$[0].items[0].total_score: matches no"),
        (
            _page({k: v for k, v in MENDELIAN.items() if k != "hgnc_id"}),
            "items[0].hgnc_id: required",
        ),
        (_page(_row(MENDELIAN, curation_id="not-a-uuid")), "curation_id: not a uuid"),
        (_page(_row(MENDELIAN, relationship_type="risk")), "relationship_type: must be one of"),
        ({**PAGE, "export_version": "2"}, "export_version: must be '1'"),
        ({"items": "x"}, "items: expected array"),
    ],
)
def test_schema_mismatch_is_rejected(doc, error) -> None:
    with pytest.raises(gc.DomainValidationError) as e:
        gc.parse_export(json.dumps(doc).encode())
    assert "not a Gene Curator export v1" in e.value.message and error in e.value.message


@pytest.mark.integration
async def test_upload_is_admin_only_and_bad_files_are_4xx(
    async_client, db_session, admin, curator, monkeypatch
) -> None:
    assert (await async_client.post(URL, files=_file(PAGE))).status_code == 401
    assert (
        await async_client.post(URL, files=_file(PAGE), headers=_bearer(curator))
    ).status_code == 403
    for content in (
        b"not json",
        b"\xff\xfe",
        json.dumps(_page(_row(MENDELIAN, url=None))).encode(),
    ):
        resp = await async_client.post(URL, files=_file(content), headers=_bearer(admin))
        assert resp.status_code == 422, resp.text
    monkeypatch.setattr(gc, "MAX_UPLOAD", 10)
    resp = await async_client.post(URL, files=_file(PAGE), headers=_bearer(admin))
    assert resp.status_code == 422 and "larger than" in resp.json()["error"]["message"]
    assert _records(db_session) == []


@pytest.mark.integration
async def test_upload_creates_drafts_and_reupload_skips(
    async_client, db_session, genes, admin
) -> None:
    resp = await async_client.post(URL, files=_file(PAGE), headers=_bearer(admin))
    assert resp.status_code == 200, resp.text
    report = resp.json()
    # Mendelian and susceptibility on one gene, disease and MOI are two records (#472)
    assert [c["curation_id"] for c in report["created"]] == [
        MENDELIAN["curation_id"],
        SUSCEPTIBILITY["curation_id"],
    ]
    assert [g["hgnc_id"] for g in report["genes_not_in_kgdb"]] == ["HGNC:99944899"]
    assert len(report["rejected"]) == 2 and report["conflicts"] == []

    account = db_session.query(User).filter(User.username == "gene-curator-import").one()
    assert (account.is_active, account.role) == (False, "viewer")
    mendelian, susceptibility = _records(db_session)
    for record in (mendelian, susceptibility):
        assert (record.status, record.curator_id) == ("draft", account.id)
        assert _events(db_session, record) == [("gc_import", admin.id)]
    assert susceptibility.evidence_strength == "Established association"
    assert mendelian.evidence_strength == "Definitive"
    assert (mendelian.disease_id, mendelian.moi) == ("MONDO:0009633", "HP:0000007")
    assert (mendelian.external_id, mendelian.external_url) == (
        MENDELIAN["curation_id"],
        MENDELIAN["url"],
    )
    assert (mendelian.external_curator, mendelian.external_reviewer) == (
        "Alice Curator",
        "Bob Reviewer",
    )
    assert (mendelian.methodology, mendelian.methodology_version) == (
        "KGDB Mendelian Curation",
        "1",
    )
    assert mendelian.scores == {"genetic": 10.0, "experimental": 6.0, "total": 16.0}
    assert mendelian.citations[0] == "PMID:31000001" and len(mendelian.citations) == 14
    assert mendelian.evidence_summary.startswith("Ten unrelated")

    # Re-upload: nothing changes, every imported curation is reported
    again = (await async_client.post(URL, files=_file([PAGE]), headers=_bearer(admin))).json()
    assert [a["record_id"] for a in again["already_imported"]] == [mendelian.id, susceptibility.id]
    assert again["created"] == [] and len(_records(db_session)) == 2
    assert _events(db_session, mendelian) == [("gc_import", admin.id)]


@pytest.mark.integration
def test_diagnostics_map_to_kgdb(db_session, genes, admin) -> None:
    report = gc.import_export(db_session, [MENDELIAN], admin)
    [record] = _records(db_session)
    d = record.diagnostics
    transcript = d["recommended_transcript"]
    assert (transcript["refseq"], transcript["mane_status"]) == ("NM_006580.4", "not_checked")
    assert transcript["verified_via"] == "MANE Select in Ensembl 115"
    assert d["detectability_note"] == "standard short-read testing adequate"
    [row] = d["detectability"]
    assert row["tools"] == [
        {
            "name": "ExomeDepth",
            "url": "https://github.com/vplagnol/ExomeDepth",
            "pmid_or_doi": "PMID:22942019",
        }
    ]
    [resource] = d["resources"]
    assert resource["verified"] == {"method": "fetched", "date": "2026-10-30"}
    assert resource["country_or_scope"] == "EU"
    assert report["dropped_fields"] == []


@pytest.mark.integration
def test_unknown_values_rejected(db_session, genes, admin) -> None:
    rows = [
        PROBABLE,
        DIGENIC,
        _row(
            MENDELIAN, curation_id="11111111-0000-4000-8000-0000000000aa", moi_hpo_id="HP:0000001"
        ),
        # A susceptibility tier is only valid for a susceptibility relationship
        _row(
            MENDELIAN,
            curation_id="11111111-0000-4000-8000-0000000000ab",
            final_classification="likely",
        ),
        _row(
            MENDELIAN,
            curation_id="11111111-0000-4000-8000-0000000000ac",
            status="archived",
            archive_reason="Curation deleted",
        ),
    ]
    report = gc.import_export(db_session, rows, admin)
    reasons = {r["curation_id"][-2:]: r["reason"] for r in report["rejected"]}
    assert "'probable' is not a mendelian class" in reasons["03"]
    assert "'Digenic' has no HPO term" in reasons["04"]
    assert "unknown MOI 'HP:0000001'" in reasons["aa"]
    assert "'likely' is not a mendelian class" in reasons["ab"]
    assert "archived" in reasons["ac"]
    assert _records(db_session) == []


@pytest.mark.integration
def test_existing_record_on_the_entity_is_a_conflict(db_session, genes, admin) -> None:
    kgdb = GDA(
        gene_id=genes[0].id,
        disease_id="MONDO:0009633",
        disease_name="x",
        evidence_strength="Strong",
        moi="HP:0000007",
        citations=["PMID:1"],
        curator_id=admin.id,
    )
    db_session.add(kgdb)
    db_session.commit()
    # A Gene Curator re-curation has a new curation_id; the KGDB key still decides
    recurated = _row(MENDELIAN, curation_id="11111111-0000-4000-8000-000000000011")
    report = gc.import_export(db_session, [MENDELIAN, recurated], admin)
    assert [(c["existing_record_id"], c["existing_source"]) for c in report["conflicts"]] == [
        (kgdb.id, "kgdb"),
        (kgdb.id, "kgdb"),
    ]
    assert report["created"] == [] and _records(db_session) == []


@pytest.mark.integration
def test_one_curator_takes_over_submits_and_publishes(db_session, genes, admin, curator) -> None:
    gc.import_export(db_session, [MENDELIAN], admin)
    [record] = _records(db_session)
    workflow.update(db_session, record.id, AssociationUpdate(evidence_summary="Checked"), curator)
    workflow.submit(db_session, record.id, curator)
    seen = ReviewDecision(expected_updated_at=record.updated_at)
    workflow.publish(db_session, record.id, seen, curator)
    db_session.refresh(record)
    assert (record.status, record.reviewer_id) == ("published", curator.id)
    assert record.curator_id != curator.id  # reviewer is still not the author
    actions = [a for a, _ in _events(db_session, record)]
    assert actions == ["gc_import", "update", "submit", "publish"]

    # Someone else's KGDB draft stays author-only
    other = get_or_create_user(db_session, "gc448_other", "gc448_o@example.com", "Pw-1!", "curator")
    mine = workflow.create(
        db_session,
        workflow.AssociationCreate(
            gene_symbol="GC448B",
            disease_id="MONDO:0011111",
            disease_name="y",
            evidence_strength="Limited",
            citations=["1"],
        ),
        curator,
    )
    with pytest.raises(workflow.PermissionDeniedError):
        workflow.submit(db_session, mine.id, other)
