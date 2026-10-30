"""Regression for #289: HPO enrichment honours the background population."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from scipy.stats import fisher_exact

from app.services.enrichment_service import EnrichmentService

# Synthetic HPO term -> gene symbol annotations (test fixture, not real data).
# G1-G4 are annotated; G5-G7 have no HPO annotation.
ANNOTATIONS = {"HP:X": {"G1", "G2"}, "HP:Y": {"G3", "G4"}}
ID_TO_SYMBOL = {i: f"G{i}" for i in range(1, 8)}


def _session() -> MagicMock:
    def query(*_columns):
        def filt(clause):
            ids = [i for i in clause.right.value if i in ID_TO_SYMBOL]
            rows = [SimpleNamespace(id=i, approved_symbol=ID_TO_SYMBOL[i]) for i in ids]
            return MagicMock(all=MagicMock(return_value=rows))

        return MagicMock(filter=filt)

    return MagicMock(query=MagicMock(side_effect=query))


def _service() -> EnrichmentService:
    service = EnrichmentService()
    service._get_hpo_annotations = AsyncMock(return_value=ANNOTATIONS)  # type: ignore[method-assign]
    service.hpo_client.get_term = AsyncMock(return_value=None)  # type: ignore[method-assign]
    service.min_term_genes = 1  # custom backgrounds leave single-gene terms in this fixture
    return service


ALL = 1.0 + 1e-9  # FDR threshold that keeps every tested term


@pytest.mark.unit
@pytest.mark.asyncio
async def test_custom_backgrounds_change_the_p_value():
    service = _service()
    # Cluster {G1}; HP:X restricted to the universe: 1 of 3 genes, then 2 of 4 genes
    small, excluded_small = await service.enrich_hpo_terms(
        [1], _session(), background_genes=[1, 3, 4], fdr_threshold=ALL
    )
    full, excluded_full = await service.enrich_hpo_terms(
        [1], _session(), background_genes=[1, 2, 3, 4], fdr_threshold=ALL
    )
    p = {r["term_id"]: r["p_value"] for r in small}
    assert p["HP:X"] == pytest.approx(1 / 3)
    assert small[0]["background_count"] == 1  # term genes counted within the universe
    assert {r["term_id"]: r["p_value"] for r in full}["HP:X"] == pytest.approx(1 / 2)
    assert excluded_small == excluded_full == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_out_of_universe_cluster_genes_are_excluded_and_cells_never_negative():
    tables = []

    def recording_fisher(table, alternative):
        tables.append(table)
        return fisher_exact(table, alternative=alternative)

    service = _service()
    with patch("app.services.enrichment_service.fisher_exact", side_effect=recording_fisher):
        # G5-G7 unannotated, G2 outside the custom background, 99 unknown
        results, excluded = await service.enrich_hpo_terms(
            [1, 2, 5, 6, 7, 99], _session(), background_genes=[1, 3, 4, 5], fdr_threshold=ALL
        )
        default, default_excluded = await service.enrich_hpo_terms(
            [1, 5, 6, 7], _session(), fdr_threshold=ALL
        )
        batch, _, batch_excluded = await service.enrich_hpo_terms_batch(
            [[1, 5, 6, 7], [3]], _session(), fdr_threshold=ALL
        )

    assert excluded == [2, 5, 6, 7, 99]
    assert [r["cluster_size"] for r in results] == [1]
    assert results[0]["p_value"] == pytest.approx(1 / 3)
    # Default universe: all HPO-annotated genes (G1-G4)
    assert default_excluded == [5, 6, 7]
    assert default[0]["p_value"] == pytest.approx(1 / 2)
    assert batch_excluded == [[5, 6, 7], []]
    assert batch[0][0]["p_value"] == pytest.approx(1 / 2)
    assert tables and all(cell >= 0 for t in tables for row in t for cell in row)


@pytest.mark.unit
def test_negative_cell_is_rejected_before_fisher():
    # Cluster gene outside the universe would make d negative; must never reach Fisher
    with (
        patch("app.services.enrichment_service.fisher_exact") as fisher,
        pytest.raises(ValueError),
    ):
        EnrichmentService._hpo_fisher_tests({"G1", "G9"}, {"HP:X": {"G1", "G2"}}, 2)
    fisher.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_endpoint_forwards_background_and_reports_excluded(async_client):
    with patch(
        "app.api.endpoints.network_analysis.enrichment_service.enrich_hpo_terms",
        new_callable=AsyncMock,
        return_value=([], [5]),
    ) as enrich:
        resp = await async_client.post(
            "/api/network/enrich/hpo", json={"cluster_genes": [1, 5], "background_genes": [1, 3]}
        )
    assert resp.status_code == 200
    assert resp.json()["excluded_genes"] == [5]
    assert enrich.await_args.kwargs["background_genes"] == [1, 3]
