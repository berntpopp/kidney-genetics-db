"""Refs #331: Leiden clustering is reproducible under a fixed seed and reports its parameters."""

from unittest.mock import MagicMock

import igraph as ig
import pytest

from app.schemas.network import NetworkClusterRequest
from app.services.network_analysis_service import NetworkAnalysisService


def _graph() -> ig.Graph:
    # Zachary karate club with weight 2 has many near-tied CPM partitions, so an
    # unseeded Leiden run varies between calls
    g = ig.Graph.Famous("Zachary")
    g.vs["gene_id"] = list(range(1, g.vcount() + 1))
    g.es["weight"] = [2.0] * g.ecount()
    return g


def _membership(graph: ig.Graph, seed: int) -> dict[int, int]:
    clusters, _, _ = NetworkAnalysisService()._detect_communities_sync(graph, "leiden", seed)
    return clusters


@pytest.mark.unit
def test_same_seed_gives_identical_membership():
    graph = _graph()
    assert _membership(graph, 7) == _membership(graph, 7)
    # Different seeds must be able to differ, otherwise the seed is not wired through
    assert any(_membership(graph, 7) != _membership(graph, s) for s in range(8, 20))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_leiden_parameters_are_echoed():
    service = NetworkAnalysisService()
    _, _, params = await service.detect_communities(_graph(), MagicMock(), "leiden", seed=11)
    assert params == {
        "objective": "CPM",
        "resolution": service.config["leiden_resolution"],
        "iterations": service.config["leiden_iterations"],
        "seed": 11,
    }


@pytest.mark.unit
def test_request_seed_has_fixed_default():
    assert NetworkClusterRequest(gene_ids=[1]).seed == 0  # None would mean unseeded runs
