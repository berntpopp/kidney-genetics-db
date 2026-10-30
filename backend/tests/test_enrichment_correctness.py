"""HPO/GO enrichment correctness: true-path rule, background, gene-set size, errors."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.exc import ProgrammingError

from app.services.enrichment_service import EnrichmentService

HP_JSON = Path(__file__).parent / "fixtures" / "hpo" / "hp_golden_subset.json"
RENAL_CYST, MULTIPLE_RENAL_CYSTS = "HP:0000107", "HP:0005562"  # child is_a Renal cyst
ABNORMAL_RENAL_MORPHOLOGY, PHENOTYPIC_ABNORMALITY = "HP:0012210", "HP:0000118"

# Synthetic gene symbols (test fixture, not real data)
ROWS = [
    SimpleNamespace(hpo_term_id=MULTIPLE_RENAL_CYSTS, gene_symbols=["G1"]),
    SimpleNamespace(hpo_term_id=RENAL_CYST, gene_symbols=["G2"]),
]


def _cache(cached=None) -> MagicMock:
    return MagicMock(get=AsyncMock(return_value=cached), set=AsyncMock(return_value=True))


def _session(rows=ROWS) -> MagicMock:
    return MagicMock(execute=MagicMock(return_value=iter(rows)))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_child_only_gene_counts_toward_kidney_ancestors_only():
    service = EnrichmentService()
    cache = _cache()
    with (
        patch("app.services.enrichment_service.get_cache_service", return_value=cache),
        patch(
            "app.services.enrichment_service.download_pinned_hp_json",
            AsyncMock(return_value=HP_JSON),
        ) as download,
    ):
        term_genes = await service._get_hpo_annotations(_session())
        await service._get_hpo_annotations(_session())

    assert term_genes[MULTIPLE_RENAL_CYSTS] == {"G1"}
    assert term_genes[RENAL_CYST] == {"G1", "G2"}  # true-path rule
    assert term_genes[ABNORMAL_RENAL_MORPHOLOGY] == {"G1", "G2"}
    assert PHENOTYPIC_ABNORMALITY not in term_genes  # outside the kidney subtree
    download.assert_awaited_once()  # ontology loaded once per process
    cached = cache.set.await_args.args[1]
    assert cached[RENAL_CYST] == ["G1", "G2"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cached_term_genes_skip_the_database():
    service = EnrichmentService()
    session = _session()
    with patch(
        "app.services.enrichment_service.get_cache_service",
        return_value=_cache({RENAL_CYST: ["G1", "G2"]}),
    ):
        assert await service._get_hpo_annotations(session) == {RENAL_CYST: {"G1", "G2"}}
    session.execute.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sql_error_propagates_instead_of_empty_result():
    service = EnrichmentService()
    session = MagicMock(execute=MagicMock(side_effect=ProgrammingError("SELECT", {}, Exception())))
    with (
        patch("app.services.enrichment_service.get_cache_service", return_value=_cache()),
        pytest.raises(ProgrammingError),
    ):
        await service._get_hpo_annotations(session)


# Synthetic term -> gene symbols (G1-G4 annotated)
ANNOTATIONS = {"HP:X": {"G1", "G2"}, "HP:Y": {"G3", "G4"}, "HP:SINGLE": {"G1"}}
ID_TO_SYMBOL = {i: f"G{i}" for i in range(1, 5)}
ALL = 1.0 + 1e-9  # FDR threshold that keeps every tested term


def _id_session() -> MagicMock:
    def query(*_columns):
        def filt(clause):
            ids = [i for i in clause.right.value if i in ID_TO_SYMBOL]
            rows = [SimpleNamespace(id=i, approved_symbol=ID_TO_SYMBOL[i]) for i in ids]
            return MagicMock(all=MagicMock(return_value=rows))

        return MagicMock(filter=filt)

    return MagicMock(query=MagicMock(side_effect=query))


def _service(min_term_genes: int = 1) -> EnrichmentService:
    service = EnrichmentService()
    service._get_hpo_annotations = AsyncMock(return_value=ANNOTATIONS)  # type: ignore[method-assign]
    service.hpo_client.get_term = AsyncMock(return_value=None)  # type: ignore[method-assign]
    service.min_term_genes = min_term_genes
    return service


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_background_restricts_the_universe():
    service = _service()
    restricted, _, excluded = await service.enrich_hpo_terms_batch(
        [[1], [2]], _id_session(), fdr_threshold=ALL, background_genes=[1, 3, 4]
    )
    default, _, _ = await service.enrich_hpo_terms_batch([[1]], _id_session(), fdr_threshold=ALL)

    # HP:X in universe {G1,G3,G4}: 1 of 3 genes; default universe G1-G4: 2 of 4
    assert {r["term_id"]: r["p_value"] for r in restricted[0]}["HP:X"] == pytest.approx(1 / 3)
    assert {r["term_id"]: r["p_value"] for r in default[0]}["HP:X"] == pytest.approx(1 / 2)
    assert excluded == [[], [2]]  # G2 is outside the custom background


@pytest.mark.unit
@pytest.mark.asyncio
async def test_terms_below_min_size_are_not_tested():
    _, tests_min1, _ = await _service(1).enrich_hpo_terms_batch([[1]], _id_session(), ALL)
    results, tests_min2, _ = await _service(2).enrich_hpo_terms_batch([[1]], _id_session(), ALL)
    assert tests_min1 == 2  # HP:X and HP:SINGLE overlap the cluster
    assert tests_min2 == 1
    assert [r["term_id"] for r in results[0]] == ["HP:X"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_go_background_is_sent_to_enrichr_with_request_timeout():
    service = EnrichmentService()
    service._enrichr_min_interval = 0
    enrichr = MagicMock()
    enrichr.return_value.results = pd.DataFrame()
    with patch("app.services.enrichment_service.gp.Enrichr", enrichr):
        results = await service.enrich_go_terms(
            [1, 2], _id_session(), timeout_seconds=30, background_genes=[1, 3, 4]
        )

    assert results == []
    kwargs = enrichr.call_args.kwargs
    assert kwargs["gene_list"] == ["G1"]  # G2 is outside the background
    assert kwargs["background"] == ["G1", "G3", "G4"]
    assert enrichr.return_value._session.request.keywords == {"timeout": (10, 30)}
    enrichr.return_value.run.assert_called_once()
