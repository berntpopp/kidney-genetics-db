"""
Task decorator pattern for background tasks with common setup/teardown.

This module provides decorators and mixins to eliminate boilerplate code
in background task management, following DRY principles.
"""

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, cast

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.core.progress_tracker import ProgressTracker

logger = get_logger(__name__)


def managed_task(source_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for background tasks with common setup/teardown.

    Args:
        source_name: Name of the data source for tracking
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(self: Any, resume: bool = False, mode: str = "smart") -> dict[str, Any]:
            """Wrapper with ROBUST database management."""
            tracker = None

            # Use context manager for guaranteed cleanup
            with get_db_context() as db:
                try:
                    tracker = ProgressTracker(db, source_name, self.broadcast_callback)
                    logger.sync_info(
                        "Starting source update", source_name=source_name, resume=resume, mode=mode
                    )

                    # Execute the actual task
                    # Check if the function accepts mode parameter
                    import inspect

                    sig = inspect.signature(func)
                    if "mode" in sig.parameters:
                        result: dict[str, Any] = await func(self, db, tracker, resume, mode)
                    else:
                        result = await func(self, db, tracker, resume)

                    db.commit()  # Explicit commit on success
                    logger.sync_info(
                        "Source update completed", source_name=source_name, result=result
                    )
                    return result

                except Exception as e:
                    db.rollback()  # Explicit rollback on error
                    logger.sync_error("Source update failed", source_name=source_name, error=e)
                    if tracker:
                        tracker.error(str(e))
                    raise

        return wrapper

    return decorator


def executor_task(source_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for background tasks that need to run in thread executor.

    Args:
        source_name: Name of the data source for tracking
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(self: Any, resume: bool = False) -> dict[str, Any]:
            """Wrapper with executor and ROBUST database management."""
            tracker = None

            # Use context manager for guaranteed cleanup
            with get_db_context() as db:
                try:
                    tracker = ProgressTracker(db, source_name, self.broadcast_callback)
                    logger.sync_info(
                        "Starting source update", source_name=source_name, resume=resume
                    )

                    # Execute the actual task in thread executor
                    loop = asyncio.get_event_loop()
                    result: dict[str, Any] = await loop.run_in_executor(
                        self.executor, func, self, db, tracker, resume
                    )

                    db.commit()  # Explicit commit on success
                    logger.sync_info(
                        "Source update completed", source_name=source_name, result=result
                    )
                    return result

                except Exception as e:
                    db.rollback()  # Explicit rollback on error
                    logger.sync_error("Source update failed", source_name=source_name, error=e)
                    if tracker:
                        tracker.error(str(e))
                    raise

        return wrapper

    return decorator


class TaskMixin:
    """Mixin providing common task functionality with unified client architecture."""

    # These will be set by subclasses
    broadcast_callback: Callable[..., Any] | None
    executor: Any

    def _get_source_instance(self, source_name: str, db_session: Any) -> Any:
        """Factory to get a configured source instance."""
        # This helper ensures that all dependencies are correctly instantiated
        # on a per-task basis, using the correct DB session.
        from app.core.cache_service import get_cache_service
        from app.core.cached_http_client import get_cached_http_client
        from app.pipeline.sources.unified import get_unified_source

        cache_service = get_cache_service(db_session)
        http_client = get_cached_http_client(cache_service, db_session)

        return get_unified_source(
            source_name, cache_service=cache_service, http_client=http_client, db_session=db_session
        )

    @managed_task("PubTator")
    async def _run_pubtator(
        self, db: Any, tracker: Any, resume: bool = False, mode: str = "smart"
    ) -> dict[str, Any]:
        """Run PubTator update using the unified template method."""
        source = self._get_source_instance("PubTator", db)
        result: dict[str, Any] = await source.update_data(db, tracker, mode=mode)
        return result

    @managed_task("GenCC")
    async def _run_gencc(
        self, db: Any, tracker: Any, resume: bool = False, mode: str = "smart"
    ) -> dict[str, Any]:
        """Run GenCC update using the unified template method."""
        source = self._get_source_instance("GenCC", db)
        result: dict[str, Any] = await source.update_data(db, tracker, mode=mode)
        return result

    @managed_task("PanelApp")
    async def _run_panelapp(
        self, db: Any, tracker: Any, resume: bool = False, mode: str = "smart"
    ) -> dict[str, Any]:
        """Run PanelApp update using the unified template method."""
        source = self._get_source_instance("PanelApp", db)
        result: dict[str, Any] = await source.update_data(db, tracker, mode=mode)
        return result

    @managed_task("HPO")
    async def _run_hpo(
        self, db: Any, tracker: Any, resume: bool = False, mode: str = "smart"
    ) -> dict[str, Any]:
        """Run HPO update using the unified template method."""
        source = self._get_source_instance("HPO", db)
        result: dict[str, Any] = await source.update_data(db, tracker, mode=mode)
        return result

    @managed_task("ClinGen")
    async def _run_clingen(
        self, db: Any, tracker: Any, resume: bool = False, mode: str = "smart"
    ) -> dict[str, Any]:
        """Run ClinGen update using the unified template method."""
        source = self._get_source_instance("ClinGen", db)
        result: dict[str, Any] = await source.update_data(db, tracker, mode=mode)
        return result

    @executor_task("HGNC_Normalization")
    def _run_hgnc_normalization(
        self, db: Any, tracker: Any, resume: bool = False
    ) -> dict[str, Any]:
        """Run HGNC normalization with managed lifecycle."""
        from app.pipeline.normalize import normalize_all_genes

        with tracker.track_operation("Normalizing gene symbols"):
            result: dict[str, Any] = normalize_all_genes(db)

            tracker.update(
                items_added=result.get("normalized", 0),
                items_updated=result.get("updated", 0),
                items_failed=result.get("failed", 0),
            )
            return result

    @managed_task("Evidence_Aggregation")
    async def _run_evidence_aggregation(
        self, db: Any, tracker: Any, resume: bool = False
    ) -> dict[str, Any]:
        """Run evidence aggregation with managed lifecycle."""
        from app.pipeline.aggregate import update_all_curations

        tracker.start("Starting evidence aggregation")
        loop = asyncio.get_event_loop()

        def run_aggregation() -> dict[str, Any]:
            with get_db_context() as agg_db:
                return cast(dict[str, Any], update_all_curations(agg_db))

        result: dict[str, Any] = await loop.run_in_executor(self.executor, run_aggregation)

        tracker.update(
            items_updated=result.get("curations_updated", 0),
            items_added=result.get("curations_created", 0),
        )
        tracker.complete(f"Aggregated evidence for {result.get('genes_processed', 0)} genes")
        return result

    @managed_task("annotation_pipeline")
    async def _run_annotation_pipeline(
        self, db: Any, tracker: Any, resume: bool = False, mode: str = "smart"
    ) -> dict[str, Any]:
        """Run annotation pipeline with managed lifecycle and pause/resume support."""
        from app.pipeline.annotation_pipeline import AnnotationPipeline, UpdateStrategy

        # Create pipeline instance with the current database session
        pipeline = AnnotationPipeline(db)

        # Determine strategy based on mode
        strategy = UpdateStrategy.INCREMENTAL if mode == "smart" else UpdateStrategy.FULL

        # Check if we're resuming a paused run
        if resume:
            # Get checkpoint data from progress metadata
            from app.models.progress import DataSourceProgress

            progress = (
                db.query(DataSourceProgress).filter_by(source_name="annotation_pipeline").first()
            )

            checkpoint = progress.progress_metadata if progress else None
            sources = checkpoint.get("sources") if checkpoint else None

            logger.sync_info(
                "Resuming annotation pipeline", checkpoint=bool(checkpoint), sources=sources
            )
        else:
            sources = None  # Will use all sources

        # Run the pipeline update
        result: dict[str, Any] = cast(
            dict[str, Any],
            await pipeline.run_update(
                strategy=strategy,
                sources=sources,
                force=False,
                task_id=tracker.task_id if hasattr(tracker, "task_id") else None,
            ),
        )

        # Update progress based on results
        if result.get("success"):
            tracker.complete(
                f"Annotation pipeline completed: {result.get('sources_updated')} sources, "
                f"{result.get('genes_processed')} genes"
            )
        elif result.get("status") == "paused":
            tracker.update(
                current_operation=result.get("message", "Pipeline paused"),
                checkpoint=result.get("checkpoint"),
            )
        else:
            tracker.error(f"Pipeline failed: {result.get('errors', [])}")

        return result
