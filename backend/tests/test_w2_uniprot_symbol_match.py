"""UniProt picks the entry whose gene name is the symbol and pages ID mapping (#365.3)."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.pipeline.sources.annotations.uniprot import UniProtAnnotationSource


def _entry(accession: str, gene: str) -> dict[str, Any]:
    return {"primaryAccession": accession, "genes": [{"geneName": {"value": gene}}]}


def _source() -> UniProtAnnotationSource:
    src = UniProtAnnotationSource.__new__(UniProtAnnotationSource)
    src.base_url = "https://rest.uniprot.org"
    src.rate_limiter = MagicMock(wait=AsyncMock())
    return src


@pytest.mark.unit
@pytest.mark.asyncio
async def test_single_lookup_skips_other_gene_listed_first() -> None:
    src = _source()
    response = MagicMock(status_code=200)
    response.json.return_value = {"results": [_entry("Q9UHE5", "NAT8"), _entry("P06280", "GLA")]}
    src.get_http_client = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=response)))  # type: ignore[method-assign]

    result = await src.fetch_annotation(MagicMock(approved_symbol="GLA"))

    assert result is not None
    assert result["accession"] == "P06280"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_id_mapping_pages_at_500() -> None:
    sizes: list[str | None] = []
    next_link = (
        '<https://rest.uniprot.org/idmapping/uniprotkb/results/J?cursor=2&size=500>; rel="next"'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/run"):
            return httpx.Response(200, json={"jobId": "J"})
        if "/status/" in path:
            return httpx.Response(200, json={"jobStatus": "FINISHED"})
        sizes.append(request.url.params.get("size"))
        if request.url.params.get("cursor"):
            return httpx.Response(
                200, json={"results": [{"from": "GLA", "to": _entry("P06280", "GLA")}]}
            )
        return httpx.Response(
            200,
            json={"results": [{"from": "PKD1", "to": _entry("P98161", "PKD1")}]},
            headers={"Link": next_link},
        )

    real_client = httpx.AsyncClient

    def client_factory(**kwargs: Any) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    genes = [MagicMock(id=1, approved_symbol="PKD1"), MagicMock(id=2, approved_symbol="GLA")]
    with (
        patch("app.pipeline.sources.annotations.uniprot.httpx.AsyncClient", client_factory),
        patch("app.pipeline.sources.annotations.uniprot.asyncio.sleep", AsyncMock()),
    ):
        results = await _source()._fetch_via_id_mapping(genes)

    assert sizes == ["500", "500"]
    assert results[1]["accession"] == "P98161"
    assert results[2]["accession"] == "P06280"
