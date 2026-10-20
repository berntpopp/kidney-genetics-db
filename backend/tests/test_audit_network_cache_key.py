"""Regression for #287: network graph cache must key on the gene selection."""

from unittest.mock import MagicMock

import igraph as ig
import pytest

from app.services.network_analysis_service import NetworkAnalysisService


@pytest.mark.asyncio
async def test_equal_sized_selections_do_not_share_cached_graph():
    service = NetworkAnalysisService()
    calls: list[list[int]] = []

    def fake_build(gene_ids: list[int], min_string_score: int) -> ig.Graph:
        calls.append(list(gene_ids))
        g = ig.Graph()
        g.add_vertices(len(gene_ids))
        g.vs["gene_id"] = gene_ids
        return g

    service._build_graph_sync = fake_build  # type: ignore[method-assign]
    session = MagicMock()

    first = await service.build_network_from_string_data([1, 2], session, 400)
    second = await service.build_network_from_string_data([3, 4], session, 400)
    again = await service.build_network_from_string_data([1, 2], session, 400)

    assert first.vs["gene_id"] == [1, 2]
    assert second.vs["gene_id"] == [3, 4]
    assert again is first  # identical selection stays a cache hit
    assert calls == [[1, 2], [3, 4]]
