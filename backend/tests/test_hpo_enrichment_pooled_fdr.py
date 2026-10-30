"""Regression for #332: batch HPO enrichment pools Benjamini-Hochberg across communities."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from scipy.stats import fisher_exact

from app.services.enrichment_service import EnrichmentService

# Synthetic HPO term -> gene symbol annotations (test fixture, not real data)
ANNOTATIONS = {
    "HP:A": {"G1", "G2", "G3", "G9"},
    "HP:B": {"G1", "G4", "G10", "G11"},
    "HP:C": {"G4", "G5", "G6"},
    "HP:D": {"G2", "G5", "G12", "G13", "G14"},
    "HP:E": {"G7", "G8", "G15"},
}
COMMUNITIES = {(1, 2, 3): ("G1", "G2", "G3"), (4, 5, 6): ("G7", "G10", "G12")}
ID_TO_SYMBOL = {
    i: sym for ids, syms in COMMUNITIES.items() for i, sym in zip(ids, syms, strict=True)
}


def _reference_bh(p: list[float]) -> list[float]:
    """Independent Benjamini-Hochberg step-up (monotone, capped at 1)."""
    m = len(p)
    order = sorted(range(m), key=lambda i: p[i])
    q = [0.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, p[i] * m / rank)
        q[i] = running
    return q


def _reference_raw_p(symbols: set[str]) -> dict[str, float]:
    background = set().union(*ANNOTATIONS.values())
    out = {}
    for term, genes in ANNOTATIONS.items():
        a = len(symbols & genes)
        if a:
            c = len(genes) - a
            table = [[a, len(symbols) - a], [c, len(background) - len(symbols) - c]]
            out[term] = fisher_exact(table, alternative="greater")[1]
    return out


def _session() -> MagicMock:
    def query(*_columns):
        def filt(clause):
            rows = [
                SimpleNamespace(id=i, approved_symbol=ID_TO_SYMBOL[i]) for i in clause.right.value
            ]
            return MagicMock(all=MagicMock(return_value=rows))

        return MagicMock(filter=filt)

    return MagicMock(query=MagicMock(side_effect=query))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_q_values_equal_pooled_bh_over_raw_p_values():
    service = EnrichmentService()
    service._get_hpo_annotations = AsyncMock(return_value=ANNOTATIONS)  # type: ignore[method-assign]
    service.hpo_client.get_term = AsyncMock(return_value=None)  # type: ignore[method-assign]

    per_community, total_tests, _ = await service.enrich_hpo_terms_batch(
        [list(ids) for ids in COMMUNITIES], _session(), fdr_threshold=1.0 + 1e-9
    )

    keys, raw = [], []
    for idx, symbols in enumerate(COMMUNITIES.values()):
        for term, p in _reference_raw_p(set(symbols)).items():
            keys.append((idx, term))
            raw.append(p)
    expected_q = dict(zip(keys, _reference_bh(raw), strict=True))
    expected_p = dict(zip(keys, raw, strict=True))

    got = {(idx, r["term_id"]): r for idx, rs in enumerate(per_community) for r in rs}
    assert total_tests == len(keys)
    assert set(got) == set(keys)
    for key, r in got.items():
        assert r["p_value"] == pytest.approx(expected_p[key])
        assert r["fdr"] == pytest.approx(expected_q[key])

    # Pooling must differ from per-community BH for this fixture, or the test proves nothing
    single, _, _ = await service.enrich_hpo_terms_batch([[1, 2, 3]], _session(), 1.0 + 1e-9)
    assert any(r["fdr"] != pytest.approx(got[(0, r["term_id"])]["fdr"]) for r in single[0])

    # The single-community endpoint path is the one-community case of the batch path
    direct, _ = await service.enrich_hpo_terms([1, 2, 3], _session(), fdr_threshold=1.0 + 1e-9)
    assert direct == single[0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_queries_symbols_once_and_names_only_significant_terms():
    service = EnrichmentService()
    service._get_hpo_annotations = AsyncMock(return_value=ANNOTATIONS)  # type: ignore[method-assign]
    service.hpo_client.get_term = AsyncMock(return_value=None)  # type: ignore[method-assign]
    session = _session()

    per_community, total_tests, _ = await service.enrich_hpo_terms_batch(
        [list(ids) for ids in COMMUNITIES], session, fdr_threshold=0.5
    )

    significant = sum(len(r) for r in per_community)
    assert session.query.call_count == 1
    assert 0 < significant < total_tests
    assert service.hpo_client.get_term.await_count == significant


@pytest.mark.unit
def test_batch_request_rejects_empty_and_over_cap_input():
    from pydantic import ValidationError

    from app.schemas.network import HPOBatchEnrichmentRequest, _enrichment_config

    cap = _enrichment_config["hpo"]["max_communities"]
    assert HPOBatchEnrichmentRequest(communities=[[1]] * cap)
    for bad in ([], [[]], [[1]] * (cap + 1)):
        with pytest.raises(ValidationError):
            HPOBatchEnrichmentRequest(communities=bad)


def _batch_limits() -> tuple[int, int]:
    from app.schemas.network import _enrichment_config, _network_config

    return _enrichment_config["hpo"]["max_cluster_size"], _network_config["max_nodes"]


@pytest.mark.unit
def test_batch_request_enforces_size_total_and_id_limits():
    from pydantic import ValidationError

    from app.schemas.network import HPOBatchEnrichmentRequest

    max_cluster, max_total = _batch_limits()
    community = list(range(1, max_cluster + 1))
    full, rest = divmod(max_total, max_cluster)
    at_total = [community] * full + ([community[:rest]] if rest else [])
    assert sum(map(len, at_total)) == max_total
    assert HPOBatchEnrichmentRequest(communities=at_total)  # both caps exactly at boundary
    for bad in (
        [community + [max_cluster + 1]],  # one community over max_cluster_size
        at_total + [[1]],  # valid-sized communities, total over max_nodes
        [[0, 1]],
        [[-1, 1]],
    ):
        with pytest.raises(ValidationError):
            HPOBatchEnrichmentRequest(communities=bad)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_endpoint_rejects_oversized_community(async_client: AsyncClient):
    max_cluster, _ = _batch_limits()
    resp = await async_client.post(
        "/api/network/enrich/hpo/batch",
        json={"communities": [list(range(1, max_cluster + 2))]},
    )
    assert resp.status_code in (400, 422)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_endpoint_returns_results_per_community(async_client: AsyncClient):
    row = {
        "term_id": "HP:A",
        "term_name": "HP:A",
        "p_value": 0.001,
        "fdr": 0.01,
        "gene_count": 2,
        "cluster_size": 3,
        "background_count": 4,
        "genes": ["G1", "G2"],
        "enrichment_score": 2.0,
        "odds_ratio": 5.0,
    }
    with patch(
        "app.api.endpoints.network_analysis.enrichment_service.enrich_hpo_terms_batch",
        new_callable=AsyncMock,
        return_value=([[row], []], 7, [[], [9]]),
    ):
        resp = await async_client.post(
            "/api/network/enrich/hpo/batch", json={"communities": [[3, 1, 2], [4, 5]]}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_tests"] == 7
    assert [len(r) for r in data["results"]] == [1, 0]
    assert data["results"][0][0]["p_value"] == 0.001
    assert data["excluded_genes"] == [[], [9]]

    bad = await async_client.post("/api/network/enrich/hpo/batch", json={"communities": [[]]})
    assert bad.status_code in (400, 422)  # app maps validation errors to 400


@pytest.mark.unit
@pytest.mark.asyncio
async def test_term_names_come_from_loaded_ontology_without_http():
    service = EnrichmentService()
    service._get_hpo_annotations = AsyncMock(return_value=ANNOTATIONS)  # type: ignore[method-assign]
    service.hpo_client.get_term = AsyncMock(return_value=None)  # type: ignore[method-assign]
    service._term_names = {t: f"name of {t}" for genes in [ANNOTATIONS] for t in genes}

    per_community, _, _ = await service.enrich_hpo_terms_batch(
        [list(ids) for ids in COMMUNITIES], _session(), fdr_threshold=0.5
    )

    results = [r for rs in per_community for r in rs]
    assert results and all(r["term_name"] == f"name of {r['term_id']}" for r in results)
    service.hpo_client.get_term.assert_not_awaited()
