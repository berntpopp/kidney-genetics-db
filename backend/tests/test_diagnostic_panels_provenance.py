"""Diagnostic panels: per-lab panels (provider_panels), upload provenance and upload fixes."""

import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy import select

from app.api.endpoints.datasources import get_diagnostic_panel_providers
from app.api.endpoints.ingestion import upload_evidence_file
from app.core.exceptions import ValidationError
from app.core.security import create_access_token
from app.models.gene import Gene, GeneEvidence
from app.models.static_sources import StaticEvidenceUpload
from app.pipeline.sources.unified.diagnostic_panels import DiagnosticPanelsSource
from app.services.hybrid_source_manager import get_source_manager
from tests.fixtures.auth import get_or_create_user

merge = DiagnosticPanelsSource.merge_provider_panels


@pytest.mark.unit
def test_provider_panels_merge_and_remove_recount_everything():
    data = merge({}, {"Lab A": ["A1", "Shared"]})
    data = merge(data, {"Lab B": ["Shared", "B1"]})
    data = merge(data, {"Lab A": ["A2"]})  # merge mode adds to the lab's panels
    assert data["provider_panels"] == {"Lab A": ["A1", "A2", "Shared"], "Lab B": ["B1", "Shared"]}
    assert (data["panel_count"], data["provider_count"]) == (4, 2)

    data = merge(data, {"Lab A": None})
    assert data["provider_panels"] == {"Lab B": ["B1", "Shared"]}
    assert data["panels"] == ["B1", "Shared"]
    assert data["providers"] == ["Lab B"]
    assert (data["panel_count"], data["provider_count"]) == (2, 1)


@pytest.mark.unit
def test_legacy_rows_without_provider_panels():
    single = {"panels": ["Old"], "providers": ["Lab A"], "panel_count": 1, "provider_count": 1}
    assert merge(single, {"Lab B": ["New"]})["provider_panels"] == {
        "Lab A": ["Old"],
        "Lab B": ["New"],
    }
    # Several unattributed labs: their panels stay while one of them remains
    legacy = {"panels": ["X", "Y"], "providers": ["Lab A", "Lab B"]}
    kept = merge(legacy, {"Lab A": None})
    assert kept["panels"] == ["X", "Y"]
    assert kept["providers"] == ["Lab B"]
    gone = merge(kept, {"Lab B": None})
    assert (gone["panels"], gone["providers"], gone["panel_count"]) == ([], [], 0)


@pytest.mark.unit
def test_upload_provenance_from_scraper_json():
    doc = {
        "provider_name": "Lab",
        "main_url": "https://lab.example/kidney",
        "scraped_at": "2025-08-24T19:36:00",
        "metadata": {"scraper_version": "1.0.0"},
        "sub_panels": [{"name": "Alport", "url": "https://lab.example/alport", "gene_count": 6}],
    }
    assert DiagnosticPanelsSource.upload_provenance(doc, "Lab", {}) == {
        "provider_name": "Lab",
        "main_url": "https://lab.example/kidney",
        "scraped_at": "2025-08-24T19:36:00",
        "scraper_version": "1.0.0",
        "panels": [{"name": "Alport", "url": "https://lab.example/alport", "gene_count": 6}],
    }
    genes = {"PKD1": {"panels": ["Kidney"]}, "PKD2": {"panels": ["Kidney"]}}
    fallback = DiagnosticPanelsSource.upload_provenance({"sub_panels": None}, "Lab", genes)
    assert fallback["panels"] == [{"name": "Kidney", "url": None, "gene_count": 2}]
    assert fallback["main_url"] is None


@pytest.mark.unit
async def test_csv_empty_cells_and_commas_in_panel_names():
    source = DiagnosticPanelsSource.__new__(DiagnosticPanelsSource)
    csv = (
        b"symbol,panel_name,panels,hgnc_id\n"
        b'PKD1,,"Alport syndrome, TBMN panel;Cystic panel",\n'
        b"PKD2,Cystic panel,,HGNC:9009\n"
    )
    df = source._parse_csv(csv, "csv")
    df["provider"] = "Lab"
    result = await source.process_data(df)
    assert result["PKD1"]["panels"] == ["Alport syndrome, TBMN panel", "Cystic panel"]
    assert result["PKD1"]["hgnc_ids"] == []
    assert result["PKD2"]["panels"] == ["Cystic panel"]
    assert result["PKD2"]["provider_panels"] == {"Lab": ["Cystic panel"]}


@pytest.mark.unit
def test_batch_provider_file_is_rejected():
    source = DiagnosticPanelsSource.__new__(DiagnosticPanelsSource)
    batch = {"providers": [{"provider_name": "Lab", "genes": [{"symbol": "PKD1"}]}]}
    with pytest.raises(ValueError, match="one provider file at a time"):
        source._parse_json(json.dumps(batch).encode())


def _gene(db, symbol: str) -> Gene:
    gene = Gene(approved_symbol=symbol, hgnc_id=f"HGNC:97{uuid4().int % 10**6:06d}")
    db.add(gene)
    db.flush()
    return gene


def _evidence(db, gene: Gene) -> GeneEvidence | None:
    return db.execute(
        select(GeneEvidence).where(
            GeneEvidence.gene_id == gene.id, GeneEvidence.source_name == "DiagnosticPanels"
        )
    ).scalar_one_or_none()


async def _store(db, provider: str, genes: dict[str, list[str]]) -> None:
    source = DiagnosticPanelsSource(db_session=db)
    doc = {"genes": [{"symbol": s, "panels": p} for s, p in genes.items()]}
    df = await source.parse_uploaded_file(json.dumps(doc).encode(), "json", provider)
    await source.store_evidence(db, await source.process_data(df), provider)
    db.flush()


@pytest.mark.integration
async def test_delete_provider_removes_its_panels_and_rebuilds_source_detail(db_session):
    shared, only_a = _gene(db_session, "KGTDPSHARED"), _gene(db_session, "KGTDPONLYA")
    await _store(db_session, "DP Lab A", {shared.approved_symbol: ["A1", "A2"]})
    await _store(db_session, "DP Lab A", {only_a.approved_symbol: ["A1"]})
    await _store(db_session, "DP Lab B", {shared.approved_symbol: ["B1"]})
    assert _evidence(db_session, shared).evidence_data["provider_panels"] == {
        "DP Lab A": ["A1", "A2"],
        "DP Lab B": ["B1"],
    }

    stats = await get_source_manager("DiagnosticPanels", db_session).delete_by_identifier(
        "DP Lab A", "test"
    )
    assert (stats["evidence_updated"], stats["evidence_deleted"]) == (1, 1)
    assert _evidence(db_session, only_a) is None
    kept = _evidence(db_session, shared)
    assert kept.evidence_data["provider_panels"] == {"DP Lab B": ["B1"]}
    assert kept.evidence_data["panels"] == ["B1"]
    assert (kept.evidence_data["panel_count"], kept.evidence_data["provider_count"]) == (1, 1)
    assert kept.source_detail == "DiagnosticPanels: 1 panels from DP Lab B"


def _upload(name: str, doc: dict) -> UploadFile:
    return UploadFile(BytesIO(json.dumps(doc).encode()), filename=name)


@pytest.mark.integration
async def test_upload_stores_provenance_under_the_json_provider_name(db_session):
    user = get_or_create_user(db_session, "dpprov", "dpprov@example.com", "Unused-Pw-1!", "curator")
    gene = _gene(db_session, "KGTDPPROV")
    provider = f"Provenance Lab {uuid4().hex[:6]}"
    doc = {
        "provider_name": provider,
        "main_url": "https://lab.example/kidney",
        "scraped_at": "2025-08-24T19:36:00",
        "metadata": {"scraper_version": "2.0.0"},
        "sub_panels": [{"name": "Kidney", "url": "https://lab.example/k", "gene_count": 1}],
        "genes": [{"symbol": gene.approved_symbol, "panels": ["Kidney"]}],
    }
    with (
        patch("app.core.gene_normalizer.normalize_genes_batch_async", AsyncMock(return_value={})),
        patch(
            "app.services.hybrid_source_manager.HybridSourceManager.recalculate_evidence_scores",
            AsyncMock(),
        ),
    ):
        result = await upload_evidence_file(
            source_name="DiagnosticPanels",
            file=_upload("provenance_lab.json", doc),  # filename must not become the name
            provider_name=None,
            mode="replace",
            db=db_session,
            current_user=user,
        )
    assert result["data"]["provider"] == provider
    assert _evidence(db_session, gene).evidence_data["provider_panels"] == {provider: ["Kidney"]}

    upload = db_session.execute(
        select(StaticEvidenceUpload).where(StaticEvidenceUpload.evidence_name == provider)
    ).scalar_one()
    assert upload.upload_metadata["mode"] == "replace"
    assert upload.upload_metadata["main_url"] == "https://lab.example/kidney"

    response = await get_diagnostic_panel_providers(db=db_session)
    names = [p["provider_name"] for p in response["data"]]
    assert names == sorted(names)
    assert response["meta"]["count"] == len(names)
    entry = next(p for p in response["data"] if p["provider_name"] == provider)
    assert set(entry) == {
        "provider_name",
        "main_url",
        "scraped_at",
        "scraper_version",
        "panels",
        "gene_count",
        "uploaded_at",
    }
    assert entry["scraper_version"] == "2.0.0"
    assert entry["panels"] == [{"name": "Kidney", "url": "https://lab.example/k", "gene_count": 1}]
    assert entry["gene_count"] == 1
    assert entry["uploaded_at"]
    assert upload.file_hash not in json.dumps(response["data"])
    assert user.username not in json.dumps(response["data"])


@pytest.mark.integration
async def test_empty_replace_upload_is_rejected_before_delete(db_session):
    gene = _gene(db_session, "KGTDPEMPTY")
    await _store(db_session, "DP Empty Lab", {gene.approved_symbol: ["P"]})
    user = SimpleNamespace(id=None, username="dpempty", role="curator")
    with pytest.raises(ValidationError):
        await upload_evidence_file(
            source_name="DiagnosticPanels",
            file=_upload("x.json", {"provider_name": "DP Empty Lab", "genes": []}),
            provider_name=None,
            mode="replace",
            db=db_session,
            current_user=user,
        )
    assert _evidence(db_session, gene).evidence_data["providers"] == ["DP Empty Lab"]


@pytest.mark.integration
async def test_hgnc_id_fallback_refuses_a_different_gene(db_session):
    stored = Gene(approved_symbol="KGTDLX", hgnc_id="HGNC:9715673", aliases=["KGTOLD"])
    db_session.add(stored)
    db_session.flush()
    source = DiagnosticPanelsSource(db_session=db_session)
    stats = {"genes_created": 0, "genes_updated": 0}

    other = {"approved_symbol": "KGTPHIP", "hgnc_id": "HGNC:9715673"}
    assert await source._get_or_create_gene(db_session, other, "KGTPHIP", stats) is None
    assert db_session.query(Gene).filter(Gene.approved_symbol == "KGTPHIP").count() == 0
    # A renamed symbol still finds its gene through an alias
    renamed = {"approved_symbol": "KGTNEW", "hgnc_id": "HGNC:9715673"}
    assert await source._get_or_create_gene(db_session, renamed, "KGTOLD", stats) is stored


@pytest.mark.integration
async def test_upload_history_and_audit_need_a_curator(async_client, db_session):
    viewer = get_or_create_user(
        db_session, "dpview", "dpview@example.com", "Unused-Pw-1!", "viewer"
    )
    curator = get_or_create_user(
        db_session, "dpcur", "dpcur@example.com", "Unused-Pw-1!", "curator"
    )
    for path in ("uploads", "audit"):
        url = f"/api/ingestion/DiagnosticPanels/{path}"
        assert (await async_client.get(url)).status_code == 401, url
        headers = {"Authorization": f"Bearer {create_access_token(subject=viewer.username)}"}
        assert (await async_client.get(url, headers=headers)).status_code == 403, url
        headers = {"Authorization": f"Bearer {create_access_token(subject=curator.username)}"}
        assert (await async_client.get(url, headers=headers)).status_code == 200, url
    assert (
        await async_client.get("/api/datasources/DiagnosticPanels/providers")
    ).status_code == 200
