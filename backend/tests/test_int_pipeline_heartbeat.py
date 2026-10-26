"""#359 review follow-up: own heartbeat, and a paused run that is still finishing holds the lock."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.security import create_access_token
from app.models.progress import DataSourceProgress, SourceStatus
from app.pipeline import annotation_pipeline
from app.pipeline.annotation_pipeline import pipeline_run_active
from tests.fixtures.auth import get_or_create_user


def _row(db_session, status, *, completed: bool, beat_minutes_ago: float = 1):
    row = db_session.query(DataSourceProgress).filter_by(source_name="annotation_pipeline").first()
    if row is None:
        row = DataSourceProgress(source_name="annotation_pipeline")
        db_session.add(row)
    now = datetime.now(timezone.utc)
    row.status = status
    row.last_update_at = now - timedelta(minutes=beat_minutes_ago)
    row.completed_at = now if completed else None
    row.progress_metadata = {}
    db_session.flush()
    return row


def test_paused_run_still_finishing_is_active(db_session):
    _row(db_session, SourceStatus.paused, completed=False)
    assert pipeline_run_active(db_session)


def test_paused_run_that_stopped_is_not_active(db_session):
    _row(db_session, SourceStatus.paused, completed=True)
    assert not pipeline_run_active(db_session)


def test_silent_run_is_not_active(db_session):
    _row(db_session, SourceStatus.running, completed=False, beat_minutes_ago=30)
    assert not pipeline_run_active(db_session)


@pytest.mark.asyncio
async def test_resume_while_sources_are_finishing_answers_409(db_session, async_client):
    _row(db_session, SourceStatus.paused, completed=False)
    admin = get_or_create_user(db_session, "int_admin", "int_admin@example.com", "Pw-1!", "admin")
    headers = {"Authorization": f"Bearer {create_access_token(subject=admin.username)}"}

    with patch("app.core.background_tasks.task_manager.run_source", AsyncMock()) as run_source:
        response = await async_client.post(
            "/api/progress/resume/annotation_pipeline", headers=headers
        )

    assert response.status_code == 409
    run_source.assert_not_called()


@pytest.mark.asyncio
async def test_heartbeat_task_keeps_publishing_until_cancelled(monkeypatch):
    monkeypatch.setattr(annotation_pipeline, "_HEARTBEAT_SECONDS", 0.01)
    pipeline = annotation_pipeline.AnnotationPipeline(MagicMock())
    beats: list[bool] = []
    monkeypatch.setattr(pipeline, "_publish", lambda force=False: beats.append(force))

    task = asyncio.create_task(pipeline._beat())
    await asyncio.sleep(0.1)
    task.cancel()

    assert len(beats) >= 3
    assert all(beats)  # forced: the heartbeat must reach the DB and the page every time
