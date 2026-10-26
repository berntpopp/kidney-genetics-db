"""Bulk-file parsing runs in a worker thread, not on the event loop (#363)."""

import threading
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.pipeline.sources.annotations.ensembl import EnsemblAnnotationSource
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mixin_parses_in_worker_thread(tmp_path: Path) -> None:
    threads: list[threading.Thread] = []

    class Source(BulkDataSourceMixin):
        def parse_bulk_file(self, path: Path) -> dict[str, dict[str, Any]]:
            threads.append(threading.current_thread())
            return {}

    src = Source()
    (tmp_path / "f.tsv").write_text("x")
    src.download_bulk_file = AsyncMock(return_value=tmp_path / "f.tsv")  # type: ignore[method-assign]
    await src.ensure_bulk_data_loaded()
    assert threads and threads[0] is not threading.main_thread()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensembl_parses_gtf_and_mane_in_worker_threads(tmp_path: Path) -> None:
    threads: list[threading.Thread] = []
    src = EnsemblAnnotationSource.__new__(EnsemblAnnotationSource)
    src._bulk_data = None
    src._mane_data = None
    (tmp_path / "a.gtf").write_text("")
    (tmp_path / "m.txt").write_text("")
    src.download_bulk_file_streaming = AsyncMock(return_value=tmp_path / "a.gtf")  # type: ignore[method-assign]
    src.download_bulk_file = AsyncMock(return_value=tmp_path / "m.txt")  # type: ignore[method-assign]

    def record(result: dict[str, Any]) -> Any:
        def parse(path: Path) -> dict[str, Any]:
            threads.append(threading.current_thread())
            return result

        return parse

    src.parse_bulk_file = record({})  # type: ignore[method-assign]
    src.parse_mane_file = record({})  # type: ignore[method-assign]
    await src.ensure_bulk_data_loaded()
    assert len(threads) == 2
    assert all(t is not threading.main_thread() for t in threads)
