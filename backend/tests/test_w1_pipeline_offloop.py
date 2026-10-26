"""#363: the bulk upsert runs in a worker thread, not on the API event loop."""

import threading
from unittest.mock import patch

import pytest

from tests.test_w1_pipeline_no_data import _gene, _NoDataSource, _update


@pytest.mark.asyncio
async def test_bulk_upsert_runs_off_the_event_loop(db_session):
    gene = _gene(db_session)
    threads: list[threading.Thread] = []

    class _WithData(_NoDataSource):
        async def fetch_batch(self, genes):
            return {g.id: {"value": 1} for g in genes}

    def upsert(self, source_name, version, batch_data, db):
        threads.append(threading.current_thread())
        return len(batch_data)

    with patch(
        "app.pipeline.annotation_pipeline.AnnotationPipeline._bulk_upsert_annotations_with_session",
        upsert,
    ):
        result = await _update(db_session, gene.id, _WithData)

    assert result["successful"] == 1
    assert threads and threads[0] is not threading.main_thread()
