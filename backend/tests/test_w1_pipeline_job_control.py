"""#370: pause stops between sources with a checkpoint; reset makes the source due again."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.progress_tracker import ProgressTracker
from app.models.gene_annotation import AnnotationSource
from app.models.progress import DataSourceProgress, SourceStatus
from app.pipeline.annotation_pipeline import AnnotationPipeline, UpdateStrategy


@pytest.mark.asyncio
async def test_pause_during_hgnc_stops_before_the_next_sources(db_session):
    pipeline = AnnotationPipeline(db_session)
    ran: list[str] = []

    async def update_source(name, gene_ids, force, source_db):
        ran.append(name)
        # the admin presses pause while HGNC runs
        db_session.query(DataSourceProgress).filter_by(source_name="annotation_pipeline").update(
            {"status": SourceStatus.paused}
        )
        return {"successful": 1}

    with (
        patch.object(
            pipeline, "_get_sources_to_update", AsyncMock(return_value=["hgnc", "gnomad", "mondo"])
        ),
        patch.object(pipeline, "_get_genes_to_update", AsyncMock(return_value=[MagicMock(id=7)])),
        patch.object(pipeline, "_update_source_with_session", side_effect=update_source),
        patch.object(pipeline, "_refresh_materialized_view", AsyncMock(return_value=True)),
        patch("app.pipeline.annotation_pipeline.SessionLocal"),
        patch("app.core.progress_tracker.ProgressTracker._commit_and_broadcast"),
    ):
        result = await pipeline.run_update(strategy=UpdateStrategy.FULL)

    assert ran == ["hgnc"]
    assert result["status"] == "paused" and not result["success"]
    row = db_session.query(DataSourceProgress).filter_by(source_name="annotation_pipeline").one()
    db_session.refresh(row)
    assert row.status == SourceStatus.paused
    assert row.progress_metadata["sources_remaining"] == ["gnomad", "mondo"]


def test_progress_update_keeps_a_pause(db_session):
    tracker = ProgressTracker(db_session, "w1_pause_probe")
    tracker.progress_record.status = SourceStatus.paused
    with patch.object(ProgressTracker, "_commit_and_broadcast"):
        tracker.update(current_item=3, force=True)

    assert tracker.progress_record.status == SourceStatus.paused


@pytest.mark.asyncio
async def test_reset_marks_source_due_and_refreshes_views(db_session):
    from app.api.endpoints.annotation_updates import _run_annotation_reset

    source = AnnotationSource(
        source_name="w1reset",
        display_name="W1 reset",
        next_update=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db_session.add(source)
    db_session.flush()

    refresh = AsyncMock(return_value=True)
    with (
        patch("app.core.database.SessionLocal", lambda: db_session),
        patch.object(db_session, "close"),
        patch.object(AnnotationPipeline, "_refresh_materialized_view", refresh),
        patch("app.core.cache_service.get_cache_service", return_value=AsyncMock()),
    ):
        await _run_annotation_reset(source="w1reset", gene_ids=None, task_id="t", user_id=None)

    db_session.refresh(source)
    assert source.is_update_due()
    refresh.assert_awaited_once()
