"""STRING PPI ingest stores every kidney partner (no top-N cap) with its KGDB gene id."""

import math
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.sources.annotations.string_ppi import StringPPIAnnotationSource

# Synthetic hub: HUB interacts with 45 kidney partners P0..P44 (test data, not STRING)
PARTNERS = [(f"P{i}", 400 + i * 13) for i in range(45)]
EVIDENCE = {"HUB": 90.0, **{f"P{i}": float(100 - 2 * i) for i in range(45)}}
GENE_IDS = {symbol: 1000 + n for n, symbol in enumerate(EVIDENCE)}


def _source() -> StringPPIAnnotationSource:
    source = StringPPIAnnotationSource.__new__(StringPPIAnnotationSource)
    source.session = SimpleNamespace(commit=lambda: None)
    source._protein_to_gene = {}  # data counts as loaded
    source._partners = {"HUB": [*PARTNERS, ("NOT_KIDNEY", 999)]}
    source._kidney_genes = set(EVIDENCE)
    source._gene_evidence_scores = dict(EVIDENCE)
    source._gene_ids = dict(GENE_IDS)
    return source


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hub_keeps_all_kidney_partners_sorted_by_string_score():
    with patch(
        "app.core.percentile_service.PercentileService.get_cached_percentiles_only",
        AsyncMock(return_value={1: 0.5}),
    ):
        result = (await _source().fetch_batch([SimpleNamespace(id=1, approved_symbol="HUB")]))[1]

    interactions = result["interactions"]
    assert len(interactions) == 45 == result["ppi_degree"]  # > the former cap of 30
    scores = [i["string_score"] for i in interactions]
    assert scores == sorted(scores, reverse=True)
    assert all(i["partner_gene_id"] == GENE_IDS[i["partner_symbol"]] for i in interactions)
    # Scoring is unchanged: all partners, sqrt(degree) hub correction
    weighted = sum(round(s / 1000 * EVIDENCE[p], 2) for p, s in PARTNERS)
    assert result["ppi_score"] == round(weighted / math.sqrt(45), 2)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kidney_gene_ids_are_loaded_with_evidence_scores():
    source = StringPPIAnnotationSource.__new__(StringPPIAnnotationSource)
    source._kidney_genes = None
    source.session = MagicMock(execute=MagicMock(return_value=[(7, "PKD1", 95.5), (9, "WT1", 80)]))
    await source._load_kidney_genes()
    assert source._gene_ids == {"PKD1": 7, "WT1": 9}
    assert source._kidney_genes == {"PKD1", "WT1"}
    assert source._gene_evidence_scores == {"PKD1": 95.5, "WT1": 80.0}
