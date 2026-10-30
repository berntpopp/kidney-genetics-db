"""Regression for #280: per-gene diagnostic provider identities survive seed/store.

Runs against real PostgreSQL via the rolled-back ``db_session`` fixture.
"""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.initial_seeder import _seed_source
from app.models.gene import Gene, GeneEvidence
from app.pipeline.sources.unified.diagnostic_panels import DiagnosticPanelsSource

SHARED, SINGLE, NEWGENE = "KGT280SHARED", "KGT280SINGLE", "KGT280NEW"
PROVIDERS = [f"Synthetic Lab {i}" for i in range(1, 10)]


def _evidence(db, symbol):
    return db.execute(
        select(GeneEvidence)
        .join(Gene, Gene.id == GeneEvidence.gene_id)
        .where(Gene.approved_symbol == symbol, GeneEvidence.source_name == "DiagnosticPanels")
    ).scalar_one()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_seeded_and_merged_providers_keep_real_identities(db_session, tmp_path):
    for i, symbol in enumerate((SHARED, SINGLE, NEWGENE)):
        db_session.add(Gene(approved_symbol=symbol, hgnc_id=f"HGNC:9928{i}0"))
    db_session.flush()

    # Nine providers all list SHARED; only the first also lists SINGLE.
    for i, name in enumerate(PROVIDERS):
        genes = [{"symbol": SHARED, "panels": [f"Panel {i}"]}]
        if i == 0:
            genes.append({"symbol": SINGLE, "panels": ["Panel 0"]})
        (tmp_path / f"p{i}.json").write_text(json.dumps({"provider_name": name, "genes": genes}))

    with patch("app.core.gene_normalizer.normalize_genes_batch_async", AsyncMock(return_value={})):
        result = await _seed_source(
            db_session, "DiagnosticPanels", {"dir": tmp_path, "id_field": "provider_name"}
        )
    assert result["status"] == "seeded"

    shared = _evidence(db_session, SHARED).evidence_data
    assert shared["providers"] == sorted(PROVIDERS)
    assert shared["provider_count"] == 9
    single = _evidence(db_session, SINGLE).evidence_data
    assert single["providers"] == ["Synthetic Lab 1"]
    assert single["provider_count"] == 1

    # Ordinary single-provider upload: merge into existing + create new record.
    source = DiagnosticPanelsSource(db_session=db_session)
    df = await source.parse_uploaded_file(
        json.dumps(
            {
                "genes": [
                    {"symbol": SHARED, "panels": ["New"]},
                    {"symbol": NEWGENE, "panels": ["New"]},
                ]
            }
        ).encode(),
        "json",
        "New Lab",
    )
    await source.store_evidence(db_session, await source.process_data(df), "New Lab")
    db_session.flush()

    merged = _evidence(db_session, SHARED).evidence_data
    assert merged["providers"] == sorted([*PROVIDERS, "New Lab"])
    assert merged["provider_count"] == 10
    new = _evidence(db_session, NEWGENE).evidence_data
    assert new["providers"] == ["New Lab"]
    assert new["provider_count"] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_legacy_seed_label_is_repaired_by_upload_then_identifier_delete(db_session):
    """Rows seeded before #280 list the pseudo-provider "Seeded from 9 files".

    The documented API repair: re-upload each provider file (merge), then
    DELETE /api/ingestion/DiagnosticPanels/identifiers/Seeded from 9 files.
    """
    from app.services.hybrid_source_manager import get_source_manager

    # Real seeded rows carry the same legacy label; a unique one keeps this test to its rows
    label = f"Seeded from 9 files {uuid4().hex[:8]}"
    legacy, orphan = "KGTLEGACY", "KGTORPHAN"
    for i, symbol in enumerate((legacy, orphan)):
        gene = Gene(approved_symbol=symbol, hgnc_id=f"HGNC:9938{i}")
        db_session.add(gene)
        db_session.flush()
        db_session.add(
            GeneEvidence(
                gene_id=gene.id,
                source_name="DiagnosticPanels",
                source_detail=label,
                evidence_data={
                    "panels": ["Kidney Panel"],
                    "providers": [label],
                    "panel_count": 1,
                    "provider_count": 1,
                },
            )
        )
    db_session.flush()

    source = DiagnosticPanelsSource(db_session=db_session)
    df = await source.parse_uploaded_file(
        json.dumps({"genes": [{"symbol": legacy, "panels": ["Kidney Panel"]}]}).encode(),
        "json",
        "CeGaT",
    )
    await source.store_evidence(db_session, await source.process_data(df), "CeGaT")
    db_session.flush()

    stats = await get_source_manager("DiagnosticPanels", db_session).delete_by_identifier(
        label, "test"
    )
    assert stats["evidence_updated"] == 1
    assert stats["evidence_deleted"] == 1  # no real provider lists the orphan: no provenance

    repaired = _evidence(db_session, legacy).evidence_data
    assert repaired["providers"] == ["CeGaT"]
    assert repaired["provider_count"] == 1
