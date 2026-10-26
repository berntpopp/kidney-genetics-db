"""#295: a completed checkpoint must not leak into the next fresh update."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.progress import DataSourceProgress, SourceStatus
from app.pipeline.annotation_pipeline import AnnotationPipeline, UpdateStrategy

CHECKPOINT = {
    "sources_remaining": ["gnomad"],
    "sources_completed": ["hgnc"],
    "gene_ids": [11, 12],
    "strategy": "full",
}


def _progress(db_session, status: SourceStatus, metadata: dict) -> DataSourceProgress:
    row = db_session.query(DataSourceProgress).filter_by(source_name="annotation_pipeline").first()
    if row is None:
        row = DataSourceProgress(source_name="annotation_pipeline")
        db_session.add(row)
    row.status = status
    row.progress_metadata = dict(metadata)
    # A stopped run: the pipeline's paused exit and the startup reset both stamp completed_at
    row.completed_at = datetime.now(timezone.utc)
    db_session.flush()
    return row


async def _run(db_session, *, genes: list | None = None, resume: bool = False):
    """Run the pipeline with I/O stubbed; return what it decided to update."""
    pipeline = AnnotationPipeline(db_session)
    sources_spy = AsyncMock(
        side_effect=lambda requested, force: list(requested or ["hgnc", "gnomad", "gtex"])
    )
    genes_spy = AsyncMock(return_value=genes or [])
    with (
        patch.object(pipeline, "_get_sources_to_update", sources_spy),
        patch.object(pipeline, "_get_genes_to_update", genes_spy),
        patch.object(pipeline, "_update_source_with_session", AsyncMock(return_value={})),
        patch.object(pipeline, "_update_sources_parallel", AsyncMock(return_value={})),
        patch.object(pipeline, "_refresh_materialized_view", AsyncMock(return_value=True)),
        patch("app.core.progress_tracker.ProgressTracker._commit_and_broadcast"),
    ):
        await pipeline.run_update(strategy=UpdateStrategy.FULL, resume=resume)
    return sources_spy.await_args.args[0], genes_spy.await_args.args[1]


@pytest.mark.asyncio
async def test_completed_checkpoint_is_ignored_by_fresh_update(db_session):
    _progress(db_session, SourceStatus.completed, CHECKPOINT)

    requested_sources, requested_genes = await _run(db_session)

    assert requested_sources is None  # all sources, including HGNC and newly enabled ones
    assert requested_genes is None


@pytest.mark.asyncio
async def test_paused_checkpoint_still_resumes_remaining_work(db_session):
    _progress(db_session, SourceStatus.paused, CHECKPOINT)

    requested_sources, requested_genes = await _run(db_session, resume=True)

    assert requested_sources == ["gnomad"]
    assert requested_genes == [11, 12]  # saved key "gene_ids" is the one restored


@pytest.mark.asyncio
async def test_successful_run_clears_consumed_checkpoint(db_session):
    row = _progress(db_session, SourceStatus.paused, CHECKPOINT)

    await _run(db_session, genes=[MagicMock(id=11), MagicMock(id=12)], resume=True)

    assert row.status == SourceStatus.completed
    assert not row.progress_metadata
