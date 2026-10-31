"""Gene Curator export import (#448), against a fixture in the pinned export v1 shape."""

import copy
import importlib.util
import json
from functools import partial
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.core.config import settings
from app.core.security import create_access_token
from app.models.gene import Gene
from app.models.gene_disease_association import GeneDiseaseAssociation as GDA
from app.models.gene_disease_association import GeneDiseaseAssociationEvent as Event
from app.schemas.gene_disease_association import AssociationUpdate, ReviewDecision
from app.services import gene_curator_import as gc
from app.services import gene_disease_association_service as workflow
from tests.fixtures.auth import get_or_create_user

BACKEND = Path(__file__).resolve().parents[1]
PAGE = json.loads((BACKEND / "tests/fixtures/gene_curator_export.json").read_text())
SNAPSHOT = json.loads((BACKEND / "contract/gene_curator_export.snapshot.json").read_text())
MENDELIAN, SUSCEPTIBILITY, PROBABLE, DIGENIC, NOT_IN_KGDB = PAGE["items"]


def _row(base: dict, **changes) -> dict:
    return {**copy.deepcopy(base), **changes}


@pytest.fixture
def admin(db_session):
    return get_or_create_user(
        db_session, "gc448_admin", "gc448_admin@example.com", "Pw-1!", "admin"
    )


@pytest.fixture
def reviewer(db_session):
    return get_or_create_user(db_session, "gc448_rev", "gc448_rev@example.com", "Pw-1!", "curator")


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


def _actions(db_session, record: GDA) -> list[str]:
    rows = db_session.query(Event.action).filter(Event.association_id == record.id)
    return [a for (a,) in rows.order_by(Event.id)]


def test_fixture_matches_pinned_contract() -> None:
    schemas = SNAPSHOT["schemas"]
    for name, data in [
        ("CurationExportPage", PAGE),
        *[("ExportCuration", i) for i in PAGE["items"]],
    ]:
        assert set(schemas[name]["required"]) <= set(data), name
        assert set(data) <= set(schemas[name]["properties"]), name


def test_drift_check_fails_on_removed_or_changed_fields_only() -> None:
    spec = importlib.util.spec_from_file_location(
        "gcc", BACKEND / "scripts/gene_curator_contract.py"
    )
    contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contract)
    pinned = SNAPSHOT["schemas"]
    current = copy.deepcopy(pinned)
    current["ExportCuration"]["properties"]["new_field"] = {"type": "string"}
    current["ExportCuration"]["properties"]["summary"]["description"] = "reworded"
    assert contract.drift(pinned, current) == ([], ["ExportCuration.new_field"])
    del current["ExportCuration"]["properties"]["mondo_id"]
    current["ExportCuration"]["properties"]["total_score"] = {"type": "string"}
    breaking, _ = contract.drift(pinned, current)
    assert [b.split(":")[0] for b in breaking] == [
        "ExportCuration.mondo_id",
        "ExportCuration.total_score",
    ]


@pytest.mark.integration
def test_import_creates_mapped_draft_and_is_idempotent(db_session, genes, admin) -> None:
    report = gc.import_export(db_session, [MENDELIAN], admin, full=True)
    assert [c["gene_symbol"] for c in report["created"]] == ["GC448A"]
    [record] = _records(db_session)
    assert (record.status, record.curator_id, record.gene_id) == ("draft", admin.id, genes[0].id)
    assert (record.disease_id, record.moi, record.relationship_type) == (
        "MONDO:0009633",
        "HP:0000007",
        "mendelian",
    )
    assert record.evidence_strength == "Definitive"
    assert (
        record.external_id == MENDELIAN["curation_id"] and record.external_url == MENDELIAN["url"]
    )
    assert (record.external_curator, record.external_reviewer) == ("Alice Curator", "Bob Reviewer")
    assert (record.methodology, record.methodology_version) == ("KGDB Mendelian Curation", "1")
    assert record.scores == {"genetic": 10.0, "experimental": 6.0, "total": 16.0}
    assert record.citations[0] == "PMID:31000001" and len(record.citations) == 14
    assert record.evidence_summary.startswith("Ten unrelated")
    # Reshaped per Gene Curator's KGDB mapping; fields KGDB's Diagnostics lacks are reported
    transcript = record.diagnostics["recommended_transcript"]
    assert (transcript["refseq"], transcript["mane_status"]) == ("NM_006580.4", "not_checked")
    [row] = record.diagnostics["detectability"]
    assert row["tools"] == [
        {
            "name": "ExomeDepth",
            "url": "https://github.com/vplagnol/ExomeDepth",
            "pmid_or_doi": "PMID:22942019",
        }
    ]
    [resource] = record.diagnostics["resources"]
    assert resource["verified"] == {"method": "fetched", "date": "2026-10-30"}
    assert "country_or_scope" not in resource
    assert report["dropped_fields"][0]["fields"] == [
        "diagnostics.resources[].country_or_scope",
        "diagnostics_notes.detectability_note",
    ]
    assert _actions(db_session, record) == ["gc_import"]

    again = gc.import_export(db_session, [MENDELIAN], admin, full=True)
    assert again["unchanged"] == 1 and not again["created"] and not again["retracted"]
    assert _actions(db_session, record) == ["gc_import"]


@pytest.mark.integration
def test_unknown_values_rejected_and_missing_genes_reported(db_session, genes, admin) -> None:
    rows = [
        PROBABLE,
        DIGENIC,
        NOT_IN_KGDB,
        _row(
            MENDELIAN, curation_id="11111111-0000-4000-8000-0000000000aa", moi_hpo_id="HP:0000001"
        ),
        _row(
            MENDELIAN, curation_id="11111111-0000-4000-8000-0000000000ab", relationship_type="risk"
        ),
        # A susceptibility tier is only valid for a susceptibility relationship
        _row(
            MENDELIAN,
            curation_id="11111111-0000-4000-8000-0000000000ac",
            final_classification="likely",
        ),
    ]
    report = gc.import_export(db_session, rows, admin, full=False)
    reasons = {r["curation_id"][-2:]: r["reason"] for r in report["rejected"]}
    assert "'probable' is not a mendelian class" in reasons["03"]
    assert "'Digenic' has no HPO term" in reasons["04"]
    assert "unknown MOI 'HP:0000001'" in reasons["aa"]
    assert "unknown relationship_type 'risk'" in reasons["ab"]
    assert "'likely' is not a mendelian class" in reasons["ac"]
    assert [g["hgnc_id"] for g in report["genes_not_in_kgdb"]] == ["HGNC:99944899"]
    assert _records(db_session) == []


@pytest.mark.integration
def test_recuration_updates_the_same_record(db_session, genes, admin) -> None:
    gc.import_export(db_session, [MENDELIAN], admin, full=True)
    new_id = "11111111-0000-4000-8000-000000000011"
    recurated = _row(
        MENDELIAN,
        curation_id=new_id,
        url=MENDELIAN["url"].replace(MENDELIAN["curation_id"], new_id),
        final_classification="Strong",  # labels compare by key
        total_score=13,
    )
    replaced = _row(MENDELIAN, status="archived", archive_reason="Replaced by new active curation")
    report = gc.import_export(db_session, [replaced, recurated], admin, full=True)
    [record] = _records(db_session)
    assert [u["record_id"] for u in report["updated"]] == [record.id]
    assert {"evidence_strength", "external_id", "external_url", "scores"} <= set(
        report["updated"][0]["fields"]
    )
    assert (record.external_id, record.evidence_strength) == (new_id, "Strong")
    assert not report["retracted"] and not report["created"]
    assert _actions(db_session, record) == ["gc_import", "gc_import"]


@pytest.mark.integration
def test_kgdb_edits_and_published_records_are_not_overwritten(
    db_session, genes, admin, reviewer
) -> None:
    gc.import_export(db_session, [MENDELIAN], admin, full=True)
    [record] = _records(db_session)
    workflow.update(db_session, record.id, AssociationUpdate(evidence_summary="KGDB edit"), admin)
    recurated = _row(MENDELIAN, final_classification="strong")
    report = gc.import_export(db_session, [recurated], admin, full=True)
    [conflict] = report["conflicts"]
    assert conflict["reason"] == "a KGDB curator edited the record since its last import"
    assert conflict["differences"]["evidence_strength"] == {
        "kgdb": "Definitive",
        "gene_curator": "Strong",
    }
    assert conflict["differences"]["evidence_summary"]["kgdb"] == "KGDB edit"
    db_session.refresh(record)
    assert (record.evidence_strength, record.evidence_summary) == ("Definitive", "KGDB edit")

    # Untouched content, but published: still reported, not overwritten
    workflow.update(
        db_session,
        record.id,
        AssociationUpdate(evidence_summary=MENDELIAN["evidence"]["evidence_summary"]),
        admin,
    )
    workflow.submit(db_session, record.id, admin)
    workflow.publish(
        db_session, record.id, ReviewDecision(expected_updated_at=record.updated_at), reviewer
    )
    report = gc.import_export(db_session, [recurated], admin, full=True)
    assert report["conflicts"][0]["reason"].startswith("record is published")
    db_session.refresh(record)
    assert (record.status, record.evidence_strength) == ("published", "Definitive")


@pytest.mark.integration
def test_retraction_on_archive_and_on_full_sync_absence(db_session, genes, admin, reviewer) -> None:
    other = _row(
        MENDELIAN,
        curation_id="11111111-0000-4000-8000-000000000021",
        entity_key="MONDO:0011111|AD",
        mondo_id="MONDO:0011111",
        moi_hpo_id="HP:0000006",
        mode_of_inheritance="AD",
    )
    gc.import_export(db_session, [MENDELIAN, other], admin, full=True)
    first, second = _records(db_session)
    workflow.submit(db_session, first.id, admin)
    workflow.publish(
        db_session, first.id, ReviewDecision(expected_updated_at=first.updated_at), reviewer
    )

    # An incremental sync never retracts by absence
    assert gc.import_export(db_session, [], admin, full=False)["retracted"] == []

    deleted = _row(other, status="archived", archive_reason="Curation deleted")
    report = gc.import_export(db_session, [deleted], admin, full=False)
    assert [(r["record_id"], r["reason"]) for r in report["retracted"]] == [
        (second.id, "Curation deleted")
    ]

    # Hard-deleted in Gene Curator: absent from a full sync, so taken offline
    report = gc.import_export(db_session, [], admin, full=True)
    assert [(r["record_id"], r["was"]) for r in report["retracted"]] == [(first.id, "published")]
    db_session.refresh(first)
    assert (first.status, first.published_at, first.reviewer_id) == ("draft", None, reviewer.id)
    assert _actions(db_session, first)[-1] == "gc_retract"
    assert gc.import_export(db_session, [], admin, full=True)["retracted"] == []


@pytest.mark.integration
def test_kgdb_record_on_the_same_entity_is_a_conflict(db_session, genes, admin) -> None:
    db_session.add(
        GDA(
            gene_id=genes[0].id,
            disease_id="MONDO:0009633",
            disease_name="x",
            evidence_strength="Strong",
            moi="HP:0000007",
            citations=["PMID:1"],
            curator_id=admin.id,
        )
    )
    db_session.commit()
    report = gc.import_export(db_session, [MENDELIAN], admin, full=True)
    assert "already recorded" in report["conflicts"][0]["reason"] and not report["created"]


@pytest.mark.integration
def test_susceptibility_tier_imported_as_is(db_session, genes, admin) -> None:
    report = gc.import_export(db_session, [SUSCEPTIBILITY], admin, full=True)
    assert len(report["created"]) == 1
    [record] = _records(db_session)
    assert (record.relationship_type, record.evidence_strength) == (
        "susceptibility",
        "Established association",
    )
    assert record.scores == {"genetic": None, "experimental": 1.0, "total": 5.0}


@pytest.mark.integration
@pytest.mark.xfail(
    reason="#472: uq_gda_gene_disease_moi lacks relationship_type, so the second entity "
    "collides; passes once #472 adds it to the key",
    strict=False,
)
def test_mendelian_and_susceptibility_for_one_gene_disease_moi(db_session, genes, admin) -> None:
    report = gc.import_export(db_session, [MENDELIAN, SUSCEPTIBILITY], admin, full=True)
    assert report["conflicts"] == []
    assert sorted(r.evidence_strength for r in _records(db_session)) == [
        "Definitive",
        "Established association",
    ]


def test_fetch_pages_with_member_token(monkeypatch) -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if "cursor" not in request.url.params:
            return httpx.Response(
                200, json={**PAGE, "items": PAGE["items"][:2], "next_cursor": "c1"}
            )
        return httpx.Response(200, json={**PAGE, "items": PAGE["items"][2:], "next_cursor": None})

    monkeypatch.setattr(settings, "GENE_CURATOR_URL", "https://gc.test")
    monkeypatch.setattr(settings, "GENE_CURATOR_TOKEN", SecretStr("gc_pat_test"))
    monkeypatch.setattr(
        gc.httpx, "Client", partial(httpx.Client, transport=httpx.MockTransport(handler))
    )
    items = gc.fetch_export(None)
    assert len(items) == 5 and len(seen) == 2
    assert seen[0].headers["Authorization"] == "Bearer gc_pat_test"
    assert seen[0].url.params["scope_name"] == "kidney-genetics"
    assert "updated_since" not in seen[0].url.params and seen[1].url.params["cursor"] == "c1"

    monkeypatch.setattr(
        gc.httpx,
        "Client",
        partial(
            httpx.Client,
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={**PAGE, "export_version": "2"})
            ),
        ),
    )
    with pytest.raises(HTTPException) as e:
        gc.fetch_export(None)
    assert e.value.status_code == 502

    monkeypatch.setattr(settings, "GENE_CURATOR_TOKEN", None)
    with pytest.raises(HTTPException) as e:
        gc.fetch_export(None)
    assert e.value.status_code == 503


@pytest.mark.integration
async def test_endpoint_is_admin_only(
    async_client, db_session, genes, admin, reviewer, monkeypatch
) -> None:
    monkeypatch.setattr(gc, "fetch_export", lambda updated_since: [MENDELIAN])
    url = "/api/admin/gene-curator/import"
    assert (await async_client.post(url)).status_code == 401
    as_curator = {"Authorization": f"Bearer {create_access_token(subject=reviewer.username)}"}
    assert (await async_client.post(url, headers=as_curator)).status_code == 403
    as_admin = {"Authorization": f"Bearer {create_access_token(subject=admin.username)}"}
    resp = await async_client.post(url, headers=as_admin)
    assert resp.status_code == 200, resp.text
    assert resp.json()["full_sync"] is True and len(resp.json()["created"]) == 1
