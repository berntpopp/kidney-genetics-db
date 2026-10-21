"""Regression for #208: whole-core HPO/GO enrichment above 500 genes."""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from app.schemas.network import GOEnrichmentRequest, HPOEnrichmentRequest

LIMIT = 2000  # equals network.max_nodes; timed in #208 (HPO <0.1 s, Enrichr GO 6.6 s)


@pytest.mark.unit
@pytest.mark.parametrize("model", [HPOEnrichmentRequest, GOEnrichmentRequest])
def test_cluster_limit_boundary(model):
    for n in (622, LIMIT):
        assert len(model(cluster_genes=list(range(1, n + 1))).cluster_genes) == n
    with pytest.raises(ValidationError):
        model(cluster_genes=list(range(1, LIMIT + 2)))


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "method", "value"),
    [("hpo", "enrich_hpo_terms", ([], [])), ("go", "enrich_go_terms", [])],
)
async def test_endpoint_forwards_full_gene_set(async_client, path, method, value):
    genes = list(range(1, LIMIT + 1))
    with patch(
        f"app.api.endpoints.network_analysis.enrichment_service.{method}",
        new_callable=AsyncMock,
        return_value=value,
    ) as enrich:
        resp = await async_client.post(f"/api/network/enrich/{path}", json={"cluster_genes": genes})
    assert resp.status_code == 200
    assert enrich.await_args.kwargs["cluster_genes"] == genes
