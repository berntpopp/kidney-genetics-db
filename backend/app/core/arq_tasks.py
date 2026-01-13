"""
ARQ task definitions for background pipeline jobs.

These tasks run in a separate worker process, isolated from the web server.
They reuse the existing pipeline logic but are immune to web server restarts.
"""

from typing import Any

from arq import Retry

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.core.progress_tracker import ProgressTracker

logger = get_logger(__name__)


async def run_pipeline_task(
    ctx: dict[str, Any],
    source_name: str,
    mode: str = "smart",
    resume: bool = False,
) -> dict[str, Any]:
    """
    ARQ task that runs a single pipeline source.

    This wraps the existing pipeline logic but runs in the worker process.
    Progress is tracked via ProgressTracker which writes to the database,
    so progress survives worker restarts.

    Args:
        ctx: ARQ context (contains worker state)
        source_name: Name of the data source
        mode: Update mode - "smart" or "full"
        resume: Whether to resume from checkpoint

    Returns:
        Result dictionary with update statistics
    """
    logger.sync_info(
        "ARQ task starting",
        source_name=source_name,
        mode=mode,
        resume=resume,
        job_id=ctx.get("job_id"),
    )

    with get_db_context() as db:
        tracker = ProgressTracker(db, source_name)

        try:
            # Get the source instance with all dependencies
            from app.core.cache_service import get_cache_service
            from app.core.cached_http_client import get_cached_http_client
            from app.pipeline.sources.unified import get_unified_source

            cache_service = get_cache_service(db)
            http_client = get_cached_http_client(cache_service, db)

            source = get_unified_source(
                source_name,
                cache_service=cache_service,
                http_client=http_client,
                db_session=db,
            )

            # Run the pipeline update
            result: dict[str, Any] = await source.update_data(db, tracker, mode=mode)

            logger.sync_info(
                "ARQ task completed successfully",
                source_name=source_name,
                result=result,
            )

            db.commit()
            return result

        except Exception as e:
            logger.sync_error(
                "ARQ task failed",
                source_name=source_name,
                error=str(e),
            )

            tracker.error(str(e))
            db.commit()  # Commit the error status

            # Retry with exponential backoff for transient errors
            # Rate limiting (429), server errors (5xx)
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str or "timeout" in error_str:
                logger.sync_info(
                    "Transient error detected, scheduling retry",
                    source_name=source_name,
                    error=str(e),
                )
                raise Retry(defer=60) from None  # Retry in 60 seconds

            # For other errors, fail immediately
            raise


async def run_annotation_pipeline_task(
    ctx: dict[str, Any],
    sources: list[str] | None = None,
    mode: str = "smart",
    resume: bool = False,
) -> dict[str, Any]:
    """
    ARQ task that runs the full annotation pipeline.

    Args:
        ctx: ARQ context
        sources: Optional list of specific sources to run
        mode: Update mode - "smart" or "full"
        resume: Whether to resume from checkpoint

    Returns:
        Result dictionary with pipeline statistics
    """
    from app.pipeline.annotation_pipeline import AnnotationPipeline, UpdateStrategy

    logger.sync_info(
        "ARQ annotation pipeline starting",
        sources=sources,
        mode=mode,
        resume=resume,
        job_id=ctx.get("job_id"),
    )

    with get_db_context() as db:
        tracker = ProgressTracker(db, "annotation_pipeline")

        try:
            pipeline = AnnotationPipeline(db)
            strategy = UpdateStrategy.INCREMENTAL if mode == "smart" else UpdateStrategy.FULL

            # Handle resume from checkpoint
            checkpoint_sources = None
            if resume:
                from app.models.progress import DataSourceProgress

                progress = (
                    db.query(DataSourceProgress)
                    .filter_by(source_name="annotation_pipeline")
                    .first()
                )
                if progress and progress.progress_metadata:
                    checkpoint_sources = progress.progress_metadata.get("sources")
                    logger.sync_info(
                        "Resuming annotation pipeline from checkpoint",
                        checkpoint_sources=checkpoint_sources,
                    )

            # Use checkpoint sources if resuming, otherwise use provided sources
            run_sources = checkpoint_sources if resume and checkpoint_sources else sources

            result: dict[str, Any] = await pipeline.run_update(
                strategy=strategy,
                sources=run_sources,
                force=False,
            )

            if result.get("success"):
                tracker.complete(
                    f"Annotation pipeline completed: {result.get('sources_updated')} sources, "
                    f"{result.get('genes_processed')} genes"
                )
            elif result.get("status") == "paused":
                pause_msg = result.get("message", "Pipeline paused")
                logger.sync_info(
                    f"Annotation pipeline paused: {pause_msg}",
                )

            db.commit()

            logger.sync_info(
                "ARQ annotation pipeline completed",
                result=result,
            )

            return result

        except Exception as e:
            logger.sync_error(
                "ARQ annotation pipeline failed",
                error=str(e),
            )

            tracker.error(str(e))
            db.commit()

            # Retry on transient errors
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str or "timeout" in error_str:
                raise Retry(defer=120) from None  # Longer delay for full pipeline

            raise
