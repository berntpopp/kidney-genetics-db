"""Uploads store evidence under the normalized gene, not the raw symbol (#366)."""

import json
from io import BytesIO
from unittest.mock import patch

import pytest
from fastapi import UploadFile
from sqlalchemy import select

from app.api.endpoints.ingestion import upload_evidence_file
from app.models.gene import Gene, GeneEvidence
from app.models.user import User

APPROVED = "KGTW3CPLANE"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_alias_and_approved_symbol_land_on_one_gene(db_session):
    gene = Gene(approved_symbol=APPROVED, hgnc_id="HGNC:9936602")
    user = User(email="w3@example.org", username="w3curator", hashed_password="x", role="curator")
    db_session.add_all([gene, user])
    db_session.flush()

    async def normalize(db, symbols, source_name):
        # The outdated alias and the approved symbol both resolve to the same gene.
        return {
            s: {"status": "normalized", "approved_symbol": APPROVED, "hgnc_id": gene.hgnc_id}
            for s in symbols
        }

    payload = {
        "genes": [
            {"symbol": "KGTW3ORF42", "panels": ["Alias panel"]},
            {"symbol": APPROVED, "panels": ["Approved panel"]},
        ]
    }
    upload = UploadFile(BytesIO(json.dumps(payload).encode()), filename="W3 Lab.json")
    with patch("app.core.gene_normalizer.normalize_genes_batch_async", normalize):
        result = await upload_evidence_file(
            source_name="DiagnosticPanels",
            file=upload,
            provider_name="W3 Lab",
            mode="merge",
            db=db_session,
            current_user=user,
        )

    assert result["data"]["storage_stats"]["failed"] == 0
    evidence = db_session.execute(
        select(GeneEvidence).where(
            GeneEvidence.gene_id == gene.id, GeneEvidence.source_name == "DiagnosticPanels"
        )
    ).scalar_one()
    assert evidence.evidence_data["panels"] == ["Alias panel", "Approved panel"]
