"""Two source symbols resolving to one gene: neither is dropped or overwritten (#366)."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.data_source_base import DataSourceClient
from app.core.gene_normalizer import GeneNormalizer
from app.models.gene import Gene, GeneEvidence

SOURCE = "W3SameGeneSource"


class _Source(DataSourceClient):
    def __init__(self, payload: dict[str, Any]):
        super().__init__()
        self.payload = payload

    @property
    def source_name(self) -> str:
        return SOURCE

    @property
    def namespace(self) -> str:
        return "w3_same_gene"

    async def fetch_raw_data(self, tracker=None, mode: str = "smart") -> Any:
        return self.payload

    async def process_data(self, raw_data: Any) -> dict[str, Any]:
        return raw_data

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        return True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_case_variants_both_get_a_normalization_result(db_session):
    db_session.add(Gene(approved_symbol="KGTW3PKD", hgnc_id="HGNC:9936603"))
    db_session.flush()

    results = await GeneNormalizer().normalize_batch_async(
        db_session, ["KGTW3PKD", "Kgtw3pkd"], "W3"
    )

    assert set(results) == {"KGTW3PKD", "Kgtw3pkd"}
    assert {r["approved_symbol"] for r in results.values()} == {"KGTW3PKD"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_alias_and_approved_symbol_merge_panels(db_session):
    gene = Gene(approved_symbol="KGTW3CPL", hgnc_id="HGNC:9936604")
    db_session.add(gene)
    db_session.flush()

    async def normalize(db, symbols, source_name):
        return {
            s: {"status": "normalized", "approved_symbol": "KGTW3CPL", "hgnc_id": gene.hgnc_id}
            for s in symbols
        }

    source = _Source(
        {
            "KGTW3CPL": {"panels": [{"id": 1, "region": "UK"}], "panel_count": 1},
            "KGTW3ORF": {"panels": [{"id": 2, "region": "Australia"}], "panel_count": 1},
        }
    )
    with patch("app.core.gene_normalizer.normalize_genes_batch_async", normalize):
        stats = await source.update_data(db_session, MagicMock(), mode="smart")

    assert stats["errors"] == 0
    evidence = db_session.execute(
        select(GeneEvidence).where(GeneEvidence.source_name == SOURCE)
    ).scalar_one()
    assert evidence.evidence_data["panels"] == [
        {"id": 1, "region": "UK"},
        {"id": 2, "region": "Australia"},
    ]
    assert evidence.evidence_data["panel_count"] == 2
