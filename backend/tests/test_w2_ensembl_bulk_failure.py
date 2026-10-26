"""A failed Ensembl bulk download fails once per run, not once per gene (#365.1)."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.pipeline.sources.annotations.ensembl import EnsemblAnnotationSource


def _source(tmp_path: Path) -> EnsemblAnnotationSource:
    src = EnsemblAnnotationSource.__new__(EnsemblAnnotationSource)
    src._bulk_data = None
    src._mane_data = None
    src.bulk_cache_dir = tmp_path
    return src


@pytest.mark.unit
def test_urls_are_pinned() -> None:
    assert "/release-115/" in EnsemblAnnotationSource.bulk_file_url
    assert "/release_1.5/" in EnsemblAnnotationSource.mane_file_url


@pytest.mark.unit
@pytest.mark.asyncio
async def test_404_is_downloaded_once_for_all_per_gene_fallbacks(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(404)

    real_client = httpx.AsyncClient

    def client_factory(**kwargs: object) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(handler), **kwargs)  # type: ignore[arg-type]

    src = _source(tmp_path)
    with (
        patch("app.pipeline.sources.unified.bulk_mixin.httpx.AsyncClient", client_factory),
        patch("app.pipeline.sources.unified.bulk_mixin.asyncio.sleep", AsyncMock()),
    ):
        for symbol in ("PKD1", "PKD2", "COL4A5"):
            gene = MagicMock(id=1, approved_symbol=symbol)
            with pytest.raises(httpx.HTTPStatusError):
                await src.fetch_annotation(gene)

    assert len(requests) == 1
