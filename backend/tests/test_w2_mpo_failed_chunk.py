"""A failed MouseMine zygosity chunk is not stored as "no kidney phenotype" (#365.4)."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.pipeline.sources.annotations.mpo_mgi import MPOMGIAnnotationSource


@pytest.mark.unit
@pytest.mark.asyncio
async def test_failed_zygosity_chunk_is_left_to_fallback() -> None:
    src = MPOMGIAnnotationSource(Mock())
    src._mpo_terms_cache = {"MP:0000519"}
    src._is_mpo_cache_expired = lambda: False  # type: ignore[method-assign]
    pheno = {
        "PKD1": {
            "has_kidney_phenotype": False,
            "mouse_orthologs": ["Pkd1"],
            "phenotypes": [],
            "phenotype_count": 0,
            "total_phenotypes": 0,
        }
    }
    client = MagicMock(get=AsyncMock(return_value=MagicMock(status_code=503)))
    gene = MagicMock(id=7, approved_symbol="PKD1")
    with (
        patch.object(src, "_bulk_query_phenotypes", AsyncMock(return_value=pheno)),
        patch.object(src, "get_http_client", AsyncMock(return_value=client)),
        patch.object(src, "apply_rate_limit", AsyncMock()),
    ):
        results = await src.fetch_batch([gene])

    assert 7 not in results
