"""Descartes must not cache a download that parses to 0 genes (#365.7)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.pipeline.sources.annotations.descartes import DescartesAnnotationSource


@pytest.mark.unit
@pytest.mark.asyncio
async def test_challenge_page_is_not_cached() -> None:
    src = DescartesAnnotationSource.__new__(DescartesAnnotationSource)
    src._load_from_cache = AsyncMock(return_value=None)  # type: ignore[method-assign]
    src._load_from_local_files = AsyncMock(return_value=False)  # type: ignore[method-assign]
    src._save_to_cache = AsyncMock()  # type: ignore[method-assign]
    src.apply_rate_limit = AsyncMock()  # type: ignore[method-assign]
    page = MagicMock(status_code=200, text="<html><body>Checking your browser</body></html>")
    src.get_http_client = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=page)))  # type: ignore[method-assign]

    await src._load_data()

    src._save_to_cache.assert_not_called()
