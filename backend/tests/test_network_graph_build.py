"""PPI graph build and clustering correctness: simple graph, batched partner lookup,
edgeless clustering, request dedupe, score floor, modularity resolution."""

import math
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import igraph as ig
import pytest
from httpx import AsyncClient
from sqlalchemy import event

from app.api.endpoints.network_analysis import igraph_to_cytoscape
from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation
from app.services import network_analysis_service as nas
from app.services.network_analysis_service import NetworkAnalysisService


@pytest.fixture
def build(db_session, monkeypatch):
    """_build_graph_sync running against the rolled-back test session."""

    @contextmanager
    def ctx():
        yield db_session

    monkeypatch.setattr(nas, "get_db_context", ctx)
    return NetworkAnalysisService()._build_graph_sync


def _gene(db, symbol: str) -> Gene:
    gene = Gene(approved_symbol=symbol)
    db.add(gene)
    db.flush()
    return gene


def _ppi(db, gene: Gene, interactions: list[dict]) -> None:
    db.add(
        GeneAnnotation(
            gene_id=gene.id, source="string_ppi", annotations={"interactions": interactions}
        )
    )
    db.flush()


def _graph(gene_ids: list[int], edges: list[tuple[int, int]] | None = None) -> ig.Graph:
    g = ig.Graph()
    g.add_vertices(len(gene_ids))
    g.vs["gene_id"] = gene_ids
    g.vs["symbol"] = [f"S{gid}" for gid in gene_ids]
    g["unknown_gene_ids"] = []
    if edges:
        g.add_edges(edges)
        g.es["weight"] = [0.9] * len(edges)
        g.es["string_score"] = [900] * len(edges)
    return g


def test_mutual_listing_collapses_to_one_edge_with_max_score(db_session, build):
    a, b = _gene(db_session, "TPPI_A"), _gene(db_session, "TPPI_B")
    _ppi(db_session, a, [{"partner_symbol": "TPPI_B", "string_score": 700}])
    _ppi(db_session, b, [{"partner_symbol": "TPPI_A", "string_score": 900}])

    g = build([a.id, b.id], 400)

    assert g.ecount() == 1
    assert g.is_simple()
    assert g.degree() == [1, 1]
    assert g.es["string_score"] == [900]
    assert g.es["weight"] == [0.9]
    edges = [e for e in igraph_to_cytoscape(g)["elements"] if "source" in e["data"]]
    assert len({e["data"]["id"] for e in edges}) == len(edges) == 1


def test_partner_lookup_is_batched_and_uses_partner_gene_id(db_session, build):
    genes = [_gene(db_session, f"TPPI_{i}") for i in range(6)]
    hub = genes[0]
    interactions = [{"partner_symbol": g.approved_symbol, "string_score": 800} for g in genes[1:5]]
    # partner_gene_id wins over a stale symbol
    interactions.append(
        {"partner_symbol": "STALE", "partner_gene_id": genes[5].id, "string_score": 800}
    )
    _ppi(db_session, hub, interactions)

    statements: list[str] = []

    def count(conn, cursor, statement, *args):
        statements.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", count)
    try:
        g = build([x.id for x in genes], 400)
    finally:
        event.remove(engine, "before_cursor_execute", count)

    assert g.ecount() == 5
    assert g.degree()[0] == 5
    # one gene lookup + one annotation chunk, independent of the interaction count
    assert len([s for s in statements if s.lstrip().upper().startswith("SELECT")]) == 2


def test_unknown_gene_ids_are_dropped_not_invented(db_session, build):
    a = _gene(db_session, "TPPI_KNOWN")

    g = build([a.id, 987654321], 400)

    assert g.vs["gene_id"] == [a.id]
    assert g.vs["symbol"] == ["TPPI_KNOWN"]
    assert g["unknown_gene_ids"] == [987654321]


@pytest.mark.parametrize("algorithm", ["leiden", "louvain", "walktrap"])
def test_edgeless_graph_clusters_with_zero_modularity(algorithm):
    mapping, modularity, _ = NetworkAnalysisService()._detect_communities_sync(
        _graph([1, 2, 3]), algorithm
    )
    assert sorted(mapping) == [1, 2, 3]
    assert modularity == 0.0


def test_modularity_uses_the_optimised_resolution():
    service = NetworkAnalysisService()
    service.config = {**service.config, "leiden_resolution": 0.5}
    # two triangles joined by one bridge
    g = _graph([1, 2, 3, 4, 5, 6], [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5), (2, 3)])

    mapping, modularity, params = service._detect_communities_sync(g, "leiden")

    membership = [mapping[gid] for gid in g.vs["gene_id"]]
    assert params["modularity_resolution"] == 0.5
    assert modularity == pytest.approx(g.modularity(membership, weights="weight", resolution=0.5))
    assert modularity != pytest.approx(g.modularity(membership, weights="weight"))


@pytest.mark.asyncio
async def test_cluster_edgeless_returns_200_and_keeps_cache_unmutated(async_client: AsyncClient):
    graph = _graph([71001, 71002, 71003])
    with patch(
        "app.api.endpoints.network_analysis.network_service.build_network_from_string_data",
        new_callable=AsyncMock,
        return_value=graph,
    ):
        resp = await async_client.post(
            "/api/network/cluster", json={"gene_ids": [71001, 71002, 71003, 71003]}
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["edges"] == 0
    assert data["modularity"] == 0.0 and math.isfinite(data["modularity"])
    assert "cluster_id" not in graph.vs.attributes()


@pytest.mark.parametrize("model", ["NetworkBuildRequest", "NetworkClusterRequest"])
def test_requests_dedupe_gene_ids(model):
    from app.schemas import network

    assert getattr(network, model)(gene_ids=[3, 1, 3, 1]).gene_ids == [1, 3]


def test_subgraph_and_background_dedupe():
    from app.schemas.network import GOEnrichmentRequest, HPOBatchEnrichmentRequest, SubgraphRequest

    req = SubgraphRequest(gene_ids=[2, 2, 1], seed_gene_ids=[1, 1])
    assert (req.gene_ids, req.seed_gene_ids) == ([1, 2], [1])
    assert HPOBatchEnrichmentRequest(
        communities=[[1, 2]], background_genes=[5, 5, 4]
    ).background_genes == [4, 5]
    assert GOEnrichmentRequest(cluster_genes=[1], background_genes=[2, 2]).background_genes == [2]


@pytest.mark.asyncio
async def test_min_string_score_below_ingest_floor_is_rejected(async_client: AsyncClient):
    from app.core.config import settings

    for path in ("/api/network/build", "/api/network/cluster"):
        resp = await async_client.post(
            path, json={"gene_ids": [1], "min_string_score": settings.STRING_MIN_SCORE - 1}
        )
        # the app's RequestValidationError handler answers 400, not FastAPI's default 422
        assert resp.status_code == 400, path
        assert "min_string_score" in resp.text


@pytest.mark.asyncio
async def test_batch_hpo_passes_background_genes(async_client: AsyncClient):
    with patch(
        "app.api.endpoints.network_analysis.enrichment_service.enrich_hpo_terms_batch",
        new_callable=AsyncMock,
        return_value=([[]], 0, [[]]),
    ) as mocked:
        resp = await async_client.post(
            "/api/network/enrich/hpo/batch",
            json={"communities": [[72001]], "background_genes": [72003, 72002, 72003]},
        )

    assert resp.status_code == 200
    assert mocked.call_args.kwargs["background_genes"] == [72002, 72003]
