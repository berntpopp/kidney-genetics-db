"""Tests for network analysis API endpoints.

Validates fixes from:
- d7f5f0a: renamed `request` body param to `body` to fix rate limiter CORS crash
- 8adb745: fix undefined stats (nodes/edges/components) after clustering
"""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import igraph as ig
import pytest
from httpx import AsyncClient


def _make_test_graph(gene_ids: list[int], edges: list[tuple[int, int]] | None = None) -> ig.Graph:
    """Create a minimal igraph for testing with gene_id vertex attributes."""
    g = ig.Graph()
    g.add_vertices(len(gene_ids))
    g.vs["gene_id"] = gene_ids

    if edges:
        g.add_edges(edges)
        g.es["weight"] = [0.9] * len(edges)
        g.es["string_score"] = [900] * len(edges)

    return g


# ---------------------------------------------------------------------------
# Unit tests: endpoint function signatures and parameter naming
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEndpointParameterNaming:
    """Verify endpoints use 'body' (not 'request') for the Pydantic model param.

    The rate limiter inspects `request` by name to extract the Starlette Request.
    If the Pydantic body is also called `request`, the limiter crashes with a
    CORS-breaking error.  Commit d7f5f0a renamed them to `body`.
    """

    def test_build_network_uses_body_param(self):
        """build_network should have 'body' param for NetworkBuildRequest."""
        from app.api.endpoints.network_analysis import build_network

        sig = inspect.signature(build_network)
        assert "body" in sig.parameters, "build_network must use 'body', not 'request'"
        assert sig.parameters["body"].annotation.__name__ == "NetworkBuildRequest"

    def test_cluster_network_uses_body_param(self):
        """cluster_network should have 'body' param for NetworkClusterRequest."""
        from app.api.endpoints.network_analysis import cluster_network

        sig = inspect.signature(cluster_network)
        assert "body" in sig.parameters, "cluster_network must use 'body', not 'request'"
        assert sig.parameters["body"].annotation.__name__ == "NetworkClusterRequest"

    def test_extract_subgraph_uses_body_param(self):
        """extract_subgraph should have 'body' param for SubgraphRequest."""
        from app.api.endpoints.network_analysis import extract_subgraph

        sig = inspect.signature(extract_subgraph)
        assert "body" in sig.parameters, "extract_subgraph must use 'body', not 'request'"
        assert sig.parameters["body"].annotation.__name__ == "SubgraphRequest"

    def test_enrich_hpo_uses_body_param(self):
        """enrich_hpo should have 'body' param for HPOEnrichmentRequest."""
        from app.api.endpoints.network_analysis import enrich_hpo

        sig = inspect.signature(enrich_hpo)
        assert "body" in sig.parameters, "enrich_hpo must use 'body', not 'request'"

    def test_enrich_go_uses_body_param(self):
        """enrich_go should have 'body' param for GOEnrichmentRequest."""
        from app.api.endpoints.network_analysis import enrich_go

        sig = inspect.signature(enrich_go)
        assert "body" in sig.parameters, "enrich_go must use 'body', not 'request'"

    def test_all_endpoints_still_have_request_for_starlette(self):
        """All endpoints must still accept a Starlette Request named 'request'."""
        from fastapi import Request

        from app.api.endpoints.network_analysis import (
            build_network,
            cluster_network,
            enrich_go,
            enrich_hpo,
            extract_subgraph,
        )

        for fn in [build_network, cluster_network, extract_subgraph, enrich_hpo, enrich_go]:
            sig = inspect.signature(fn)
            assert "request" in sig.parameters, f"{fn.__name__} must have 'request' (Starlette)"
            assert sig.parameters["request"].annotation is Request, (
                f"{fn.__name__} 'request' must be typed as starlette Request"
            )


# ---------------------------------------------------------------------------
# Unit tests: response schema fields (the stats fix)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResponseSchemas:
    """Verify response models include all required stats fields.

    Commit 8adb745 fixed undefined nodes/edges/components after clustering.
    """

    def test_network_build_response_has_stats(self):
        """NetworkBuildResponse must have nodes, edges, components."""
        from app.schemas.network import NetworkBuildResponse

        fields = NetworkBuildResponse.model_fields
        assert "nodes" in fields
        assert "edges" in fields
        assert "components" in fields
        assert "cytoscape_json" in fields

    def test_network_cluster_response_has_stats(self):
        """NetworkClusterResponse must have nodes, edges, components, num_clusters, modularity."""
        from app.schemas.network import NetworkClusterResponse

        fields = NetworkClusterResponse.model_fields
        for field in ["nodes", "edges", "components", "clusters", "num_clusters", "modularity"]:
            assert field in fields, f"NetworkClusterResponse missing '{field}'"

    def test_cluster_response_can_serialize_all_stats(self):
        """NetworkClusterResponse must accept concrete stat values (not None/undefined)."""
        from app.schemas.network import NetworkClusterResponse

        resp = NetworkClusterResponse(
            nodes=10,
            edges=15,
            components=2,
            clusters={1: 0, 2: 0, 3: 1},
            num_clusters=2,
            modularity=0.45,
            algorithm="leiden",
            cytoscape_json={"elements": []},
        )

        assert resp.nodes == 10
        assert resp.edges == 15
        assert resp.components == 2
        assert resp.num_clusters == 2
        assert resp.modularity == 0.45


# ---------------------------------------------------------------------------
# Unit tests: input validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInputValidation:
    """Verify schema-level validation on request bodies."""

    def test_build_request_rejects_empty_gene_ids(self):
        """NetworkBuildRequest must reject empty gene_ids list."""
        from pydantic import ValidationError

        from app.schemas.network import NetworkBuildRequest

        with pytest.raises(ValidationError):
            NetworkBuildRequest(gene_ids=[])

    def test_cluster_request_rejects_empty_gene_ids(self):
        """NetworkClusterRequest must reject empty gene_ids list."""
        from pydantic import ValidationError

        from app.schemas.network import NetworkClusterRequest

        with pytest.raises(ValidationError):
            NetworkClusterRequest(gene_ids=[])

    def test_build_request_rejects_negative_gene_ids(self):
        """NetworkBuildRequest must reject negative gene IDs."""
        from pydantic import ValidationError

        from app.schemas.network import NetworkBuildRequest

        with pytest.raises(ValidationError):
            NetworkBuildRequest(gene_ids=[-1, 2, 3])

    def test_cluster_request_rejects_invalid_algorithm(self):
        """NetworkClusterRequest must reject unknown algorithm."""
        from pydantic import ValidationError

        from app.schemas.network import NetworkClusterRequest

        with pytest.raises(ValidationError):
            NetworkClusterRequest(gene_ids=[1, 2, 3], algorithm="unknown")

    def test_cluster_request_accepts_valid_algorithms(self):
        """NetworkClusterRequest must accept leiden, louvain, walktrap."""
        from app.schemas.network import NetworkClusterRequest

        for algo in ["leiden", "louvain", "walktrap"]:
            req = NetworkClusterRequest(gene_ids=[1, 2, 3], algorithm=algo)
            assert req.algorithm == algo

    def test_build_request_sorts_gene_ids_for_cache(self):
        """Gene IDs should be sorted for deterministic cache keys."""
        from app.schemas.network import NetworkBuildRequest

        req = NetworkBuildRequest(gene_ids=[5, 1, 3])
        assert req.gene_ids == [1, 3, 5]


# ---------------------------------------------------------------------------
# Integration tests: endpoint responses via async_client with mocked service
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildNetworkEndpoint:
    """Test POST /api/network/build with mocked service."""

    @pytest.mark.asyncio
    async def test_build_returns_stats(self, async_client: AsyncClient, db_session):
        """Build endpoint must return nodes, edges, components (not undefined)."""
        graph = _make_test_graph([1, 2, 3], edges=[(0, 1), (1, 2)])

        mock_gene_1 = MagicMock()
        mock_gene_1.id = 1
        mock_gene_1.approved_symbol = "PKD1"
        mock_gene_2 = MagicMock()
        mock_gene_2.id = 2
        mock_gene_2.approved_symbol = "PKD2"
        mock_gene_3 = MagicMock()
        mock_gene_3.id = 3
        mock_gene_3.approved_symbol = "PKHD1"

        with (
            patch(
                "app.api.endpoints.network_analysis.network_service.build_network_from_string_data",
                new_callable=AsyncMock,
                return_value=graph,
            ),
            patch(
                "app.api.endpoints.network_analysis.network_service.filter_network",
                new_callable=AsyncMock,
                return_value=graph,
            ),
            patch("app.api.endpoints.network_analysis.cache", lambda **kw: lambda fn: fn),
            patch.object(
                db_session,
                "query",
                return_value=MagicMock(
                    filter=MagicMock(
                        return_value=MagicMock(all=MagicMock(return_value=[mock_gene_1, mock_gene_2, mock_gene_3]))
                    )
                ),
            ),
        ):
            resp = await async_client.post(
                "/api/network/build",
                json={"gene_ids": [1, 2, 3]},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["nodes"] == 3
        assert data["edges"] == 2
        assert data["components"] >= 1
        assert "cytoscape_json" in data

    @pytest.mark.asyncio
    async def test_build_404_when_no_genes_found(self, async_client: AsyncClient, db_session):
        """Build endpoint must return 404 when gene IDs don't match any DB records."""
        with patch.object(
            db_session,
            "query",
            return_value=MagicMock(
                filter=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            ),
        ):
            resp = await async_client.post(
                "/api/network/build",
                json={"gene_ids": [99999]},
            )

        assert resp.status_code == 404


@pytest.mark.unit
class TestClusterNetworkEndpoint:
    """Test POST /api/network/cluster with mocked service."""

    @pytest.mark.asyncio
    async def test_cluster_returns_all_stats(self, async_client: AsyncClient, db_session):
        """Cluster endpoint must return nodes, edges, components, num_clusters, modularity."""
        graph = _make_test_graph([1, 2, 3, 4], edges=[(0, 1), (2, 3)])

        mock_genes = []
        for gid, sym in [(1, "PKD1"), (2, "PKD2"), (3, "PKHD1"), (4, "NPHP1")]:
            g = MagicMock()
            g.id = gid
            g.approved_symbol = sym
            mock_genes.append(g)

        gene_to_cluster = {1: 0, 2: 0, 3: 1, 4: 1}
        modularity = 0.5

        with (
            patch(
                "app.api.endpoints.network_analysis.network_service.build_network_from_string_data",
                new_callable=AsyncMock,
                return_value=graph,
            ),
            patch(
                "app.api.endpoints.network_analysis.network_service.detect_communities",
                new_callable=AsyncMock,
                return_value=(gene_to_cluster, modularity),
            ),
            patch(
                "app.api.endpoints.network_analysis.network_service.filter_network",
                new_callable=AsyncMock,
                return_value=graph,
            ),
            patch("app.api.endpoints.network_analysis.cache", lambda **kw: lambda fn: fn),
            patch.object(
                db_session,
                "query",
                return_value=MagicMock(
                    filter=MagicMock(
                        return_value=MagicMock(all=MagicMock(return_value=mock_genes))
                    )
                ),
            ),
        ):
            resp = await async_client.post(
                "/api/network/cluster",
                json={"gene_ids": [1, 2, 3, 4], "algorithm": "leiden"},
            )

        assert resp.status_code == 200
        data = resp.json()
        # The fix from 8adb745: these must be actual integers, not null/undefined
        assert isinstance(data["nodes"], int)
        assert isinstance(data["edges"], int)
        assert isinstance(data["components"], int)
        assert isinstance(data["num_clusters"], int)
        assert isinstance(data["modularity"], float)
        assert data["num_clusters"] == 2
        assert data["modularity"] == 0.5
        assert data["algorithm"] == "leiden"
        assert "clusters" in data
        assert "cytoscape_json" in data


# ---------------------------------------------------------------------------
# Unit tests: helper functions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHelperFunctions:
    """Test igraph_to_cytoscape and generate_cluster_colors."""

    def test_igraph_to_cytoscape_basic(self):
        """igraph_to_cytoscape produces correct Cytoscape.js structure."""
        from app.api.endpoints.network_analysis import igraph_to_cytoscape

        graph = _make_test_graph([10, 20], edges=[(0, 1)])
        symbol_map = {10: "PKD1", 20: "PKD2"}

        result = igraph_to_cytoscape(graph, symbol_map)

        assert "elements" in result
        elements = result["elements"]
        # 2 nodes + 1 edge
        assert len(elements) == 3

        nodes = [e for e in elements if "label" in e.get("data", {})]
        edges = [e for e in elements if "source" in e.get("data", {})]
        assert len(nodes) == 2
        assert len(edges) == 1
        assert edges[0]["data"]["source"] == "10"
        assert edges[0]["data"]["target"] == "20"

    def test_igraph_to_cytoscape_with_cluster_colors(self):
        """Cluster colors should be applied to node data."""
        from app.api.endpoints.network_analysis import igraph_to_cytoscape

        graph = _make_test_graph([10, 20], edges=[(0, 1)])
        graph.vs["cluster_id"] = [0, 1]
        symbol_map = {10: "PKD1", 20: "PKD2"}
        colors = {0: "#ff0000", 1: "#00ff00"}

        result = igraph_to_cytoscape(graph, symbol_map, cluster_colors=colors)
        nodes = [e for e in result["elements"] if "label" in e.get("data", {})]

        for node in nodes:
            assert "cluster_id" in node["data"]
            assert "color" in node["data"]

    def test_generate_cluster_colors_basic(self):
        """generate_cluster_colors returns dict with correct count."""
        from app.api.endpoints.network_analysis import generate_cluster_colors

        colors = generate_cluster_colors(5)
        assert len(colors) == 5
        assert all(isinstance(c, str) and c.startswith("#") for c in colors.values())

    def test_generate_cluster_colors_cycles_beyond_palette(self):
        """Colors cycle when more clusters than palette entries."""
        from app.api.endpoints.network_analysis import generate_cluster_colors

        colors = generate_cluster_colors(25)
        assert len(colors) == 25
        # Colors should cycle: color[0] == color[20]
        assert colors[0] == colors[20]
