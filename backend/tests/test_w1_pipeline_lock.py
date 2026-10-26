"""#359: a second annotation run must not start while one is alive (heartbeat-based lock)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.core.security import create_access_token
from app.models.progress import DataSourceProgress, SourceStatus
from app.pipeline.annotation_pipeline import AnnotationPipeline, UpdateStrategy
from tests.fixtures.auth import get_or_create_user


def _running_row(db_session, *, heartbeat_minutes_ago: float) -> DataSourceProgress:
    row = db_session.query(DataSourceProgress).filter_by(source_name="annotation_pipeline").first()
    if row is None:
        row = DataSourceProgress(source_name="annotation_pipeline")
        db_session.add(row)
    now = datetime.now(timezone.utc)
    row.status = SourceStatus.running
    row.started_at = now - timedelta(days=120)  # an old start must not make a live run look stale
    row.last_update_at = now - timedelta(minutes=heartbeat_minutes_ago)
    row.progress_metadata = {}
    db_session.flush()
    return row


async def _run(db_session) -> tuple[dict, AsyncMock]:
    pipeline = AnnotationPipeline(db_session)
    sources_spy = AsyncMock(return_value=[])
    with (
        patch.object(pipeline, "_get_sources_to_update", sources_spy),
        patch.object(pipeline, "_get_genes_to_update", AsyncMock(return_value=[])),
        patch("app.core.progress_tracker.ProgressTracker._commit_and_broadcast"),
    ):
        result = await pipeline.run_update(strategy=UpdateStrategy.FULL)
    return result, sources_spy


@pytest.mark.asyncio
async def test_second_run_during_active_run_does_nothing(db_session):
    row = _running_row(db_session, heartbeat_minutes_ago=1)

    result, sources_spy = await _run(db_session)

    assert result["status"] == "already_running"
    sources_spy.assert_not_awaited()
    assert row.status == SourceStatus.running


@pytest.mark.asyncio
async def test_run_with_stale_heartbeat_is_recovered(db_session):
    _running_row(db_session, heartbeat_minutes_ago=30)

    result, sources_spy = await _run(db_session)

    assert result.get("status") != "already_running"
    sources_spy.assert_awaited_once()


@pytest.mark.asyncio
async def test_trigger_endpoint_answers_409_during_active_run(db_session, async_client):
    _running_row(db_session, heartbeat_minutes_ago=1)
    admin = get_or_create_user(db_session, "w1_admin", "w1_admin@example.com", "Pw-1!", "admin")
    headers = {"Authorization": f"Bearer {create_access_token(subject=admin.username)}"}

    run = "app.api.endpoints.annotation_updates._run_pipeline_update"
    with patch(run, AsyncMock()) as background_run:  # never start a real pipeline here
        response = await async_client.post("/api/annotations/pipeline/update", headers=headers)

    assert response.status_code == 409
    background_run.assert_not_awaited()
