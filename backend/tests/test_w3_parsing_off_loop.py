"""GenCC row processing and xlsx upload parsing run off the event loop (#363)."""

import threading

import pandas as pd
import pytest

from app.pipeline.sources.unified.diagnostic_panels import DiagnosticPanelsSource
from app.pipeline.sources.unified.gencc import GenCCUnifiedSource


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gencc_rows_are_processed_in_a_worker_thread(monkeypatch):
    seen: list[int] = []
    source = GenCCUnifiedSource.__new__(GenCCUnifiedSource)
    monkeypatch.setattr(
        source, "kidney_match", lambda row: seen.append(threading.get_ident()) or None
    )

    assert await source.process_data(pd.DataFrame([{"gene_symbol": "X"}])) == {}
    assert seen and threading.get_ident() not in seen


@pytest.mark.unit
@pytest.mark.asyncio
async def test_excel_upload_is_parsed_in_a_worker_thread(monkeypatch):
    seen: list[int] = []
    source = DiagnosticPanelsSource.__new__(DiagnosticPanelsSource)

    def parse(content):
        seen.append(threading.get_ident())
        return pd.DataFrame([{"symbol": "X"}])

    monkeypatch.setattr(source, "_parse_excel", parse)

    await source.parse_uploaded_file(b"xlsx", "xlsx", "Lab")
    assert seen and threading.get_ident() not in seen
