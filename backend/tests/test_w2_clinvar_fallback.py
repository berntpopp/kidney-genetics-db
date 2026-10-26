"""ClinVar API fallback must not store incomplete counts (#365.6)."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource


def _source(pages: list[dict[str, Any]]) -> tuple[ClinVarAnnotationSource, AsyncMock]:
    src = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
    src.ncbi_api_key = None
    src.search_batch_size = 2
    responses = []
    for page in pages:
        r = MagicMock()
        r.json.return_value = {"esearchresult": page}
        responses.append(r)
    get = AsyncMock(side_effect=responses)
    src.get_http_client = AsyncMock(return_value=MagicMock(get=get))  # type: ignore[method-assign]
    src.apply_rate_limit = AsyncMock()  # type: ignore[method-assign]
    return src, get


@pytest.mark.unit
@pytest.mark.asyncio
async def test_esearch_error_raises_instead_of_zero_variants() -> None:
    src, _ = _source([{"ERROR": "Search Backend failed", "idlist": []}])
    with pytest.raises(RuntimeError):
        await src._search_variants("PKD1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_esearch_pages_with_retstart() -> None:
    src, get = _source([{"count": "3", "idlist": ["1", "2"]}, {"count": "3", "idlist": ["3"]}])
    assert await src._search_variants("PKD1") == ["1", "2", "3"]
    assert [c.kwargs["params"]["retstart"] for c in get.call_args_list] == [0, 2]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_failed_esummary_batch_fails_the_gene() -> None:
    src = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
    src.variant_batch_size = 1
    src.max_concurrent_variant_fetches = 2
    src._search_variants = AsyncMock(return_value=["1", "2"])  # type: ignore[method-assign]
    src._fetch_variant_batch = AsyncMock(  # type: ignore[method-assign]
        side_effect=[[{"variant_id": "1"}], RuntimeError("esummary failed")]
    )
    src._aggregate_variants = MagicMock(  # type: ignore[method-assign]
        return_value={"total_count": 1, "pathogenic_count": 0, "likely_pathogenic_count": 0}
    )
    src._build_annotation = MagicMock(return_value={"gene_symbol": "PKD1"})  # type: ignore[method-assign]
    assert await src._fetch_via_api(MagicMock(approved_symbol="PKD1")) is None
