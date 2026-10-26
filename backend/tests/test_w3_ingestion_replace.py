"""A REPLACE upload must not delete the provider's evidence before the new file parses (#366)."""

from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import UploadFile
from sqlalchemy import select

from app.api.endpoints.ingestion import upload_evidence_file
from app.models.gene import Gene, GeneEvidence

PROVIDER = "W3 Replace Lab"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_malformed_replace_upload_keeps_old_evidence(db_session):
    gene = Gene(approved_symbol="KGTW3REPL", hgnc_id="HGNC:9936601")
    db_session.add(gene)
    db_session.flush()
    db_session.add(
        GeneEvidence(
            gene_id=gene.id,
            source_name="DiagnosticPanels",
            source_detail="w3",
            evidence_data={"panels": ["P"], "providers": [PROVIDER], "provider_count": 1},
        )
    )
    db_session.flush()

    upload = UploadFile(BytesIO(b"{not json"), filename=f"{PROVIDER}.json")
    with pytest.raises(Exception):  # noqa: B017 - any rejection; the point is what survives
        await upload_evidence_file(
            source_name="DiagnosticPanels",
            file=upload,
            provider_name=PROVIDER,
            mode="replace",
            db=db_session,
            current_user=SimpleNamespace(id=1, username="w3", role="curator"),
        )

    kept = db_session.execute(
        select(GeneEvidence).where(GeneEvidence.gene_id == gene.id)
    ).scalar_one_or_none()
    assert kept is not None
    assert kept.evidence_data["providers"] == [PROVIDER]
