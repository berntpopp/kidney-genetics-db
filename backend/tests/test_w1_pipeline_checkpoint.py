"""#362: a fresh request must not adopt an old paused checkpoint, and a (re)start is dated now."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.progress import SourceStatus
from tests.test_audit_pipeline_checkpoint import CHECKPOINT, _progress, _run


@pytest.mark.asyncio
async def test_fresh_request_ignores_old_paused_checkpoint(db_session):
    row = _progress(db_session, SourceStatus.paused, CHECKPOINT)
    row.started_at = datetime.now(timezone.utc) - timedelta(days=120)

    requested_sources, requested_genes = await _run(db_session)

    assert requested_sources is None  # its own selection: all sources, incl. hgnc and mondo
    assert requested_genes is None
    assert datetime.now(timezone.utc) - row.started_at < timedelta(minutes=1)


@pytest.mark.asyncio
async def test_resumed_run_reports_current_started_at(db_session):
    row = _progress(db_session, SourceStatus.paused, CHECKPOINT)
    row.started_at = datetime.now(timezone.utc) - timedelta(days=120)

    await _run(db_session, resume=True)

    assert datetime.now(timezone.utc) - row.started_at < timedelta(minutes=1)
