"""
Task decorator pattern for background tasks with common setup/teardown.

This module provides decorators and mixins to eliminate boilerplate code
in background task management, following DRY principles.
"""

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from app.core.database import get_db_context
from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


def managed_task(source_name: str):
    """
    Decorator for background tasks with common setup/teardown.

    Args:
        source_name: Name of the data source for tracking
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, resume: bool = False) -> dict[str, Any]:
            """Wrapper with ROBUST database management."""
            tracker = None

            # Use context manager for guaranteed cleanup
            with get_db_context() as db:
                try:
                    tracker = ProgressTracker(db, source_name, self.broadcast_callback)
                    logger.info(f"Starting {source_name} update (resume={resume})")

                    # Execute the actual task
                    result = await func(self, db, tracker, resume)

                    db.commit()  # Explicit commit on success
                    logger.info(f"{source_name} update completed: {result}")
                    return result

                except Exception as e:
                    db.rollback()  # Explicit rollback on error
                    logger.error(f"{source_name} update failed: {e}")
                    if tracker:
                        tracker.error(str(e))
                    raise

        return wrapper

    return decorator


def executor_task(source_name: str):
    """
    Decorator for background tasks that need to run in thread executor.

    Args:
        source_name: Name of the data source for tracking
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, resume: bool = False) -> dict[str, Any]:
            """Wrapper with executor and ROBUST database management."""
            tracker = None

            # Use context manager for guaranteed cleanup
            with get_db_context() as db:
                try:
                    tracker = ProgressTracker(db, source_name, self.broadcast_callback)
                    logger.info(f"Starting {source_name} update (resume={resume})")

                    # Execute the actual task in thread executor
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        self.executor, func, self, db, tracker, resume
                    )

                    db.commit()  # Explicit commit on success
                    logger.info(f"{source_name} update completed: {result}")
                    return result

                except Exception as e:
                    db.rollback()  # Explicit rollback on error
                    logger.error(f"{source_name} update failed: {e}")
                    if tracker:
                        tracker.error(str(e))
                    raise

        return wrapper

    return decorator


class TaskMixin:
    """Mixin providing common task functionality with unified client architecture."""

    def _get_source_instance(self, source_name: str, db_session):
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
    async def _run_pubtator(self, db, tracker, resume: bool = False):
        """Run PubTator update using the unified template method."""
        source = self._get_source_instance("PubTator", db)
        return await source.update_data(db, tracker)

    @managed_task("GenCC")
    async def _run_gencc(self, db, tracker, resume: bool = False):
        """Run GenCC update using the unified template method."""
        source = self._get_source_instance("GenCC", db)
        return await source.update_data(db, tracker)

    @managed_task("PanelApp")
    async def _run_panelapp(self, db, tracker, resume: bool = False):
        """Run PanelApp update using the unified template method."""
        source = self._get_source_instance("PanelApp", db)
        return await source.update_data(db, tracker)

    @managed_task("HPO")
    async def _run_hpo(self, db, tracker, resume: bool = False):
        """Run HPO update using the unified template method."""
        source = self._get_source_instance("HPO", db)
        return await source.update_data(db, tracker)

    @managed_task("ClinGen")
    async def _run_clingen(self, db, tracker, resume: bool = False):
        """Run ClinGen update using the unified template method."""
        source = self._get_source_instance("ClinGen", db)
        return await source.update_data(db, tracker)

    @executor_task("HGNC_Normalization")
    def _run_hgnc_normalization(self, db, tracker, resume: bool = False):
        """Run HGNC normalization with managed lifecycle."""
        from app.pipeline.normalize import normalize_all_genes

        with tracker.track_operation("Normalizing gene symbols"):
            result = normalize_all_genes(db)

            tracker.update(
                items_added=result.get("normalized", 0),
                items_updated=result.get("updated", 0),
                items_failed=result.get("failed", 0),
            )
            return result

    @managed_task("Evidence_Aggregation")
    async def _run_evidence_aggregation(self, db, tracker, resume: bool = False):
        """Run evidence aggregation with managed lifecycle."""
        from app.pipeline.aggregate import update_all_curations

        tracker.start("Starting evidence aggregation")
        loop = asyncio.get_event_loop()

        def run_aggregation():
            with get_db_context() as agg_db:
                return update_all_curations(agg_db)

        result = await loop.run_in_executor(self.executor, run_aggregation)

        tracker.update(
            items_updated=result.get("curations_updated", 0),
            items_added=result.get("curations_created", 0),
        )
        tracker.complete(f"Aggregated evidence for {result.get('genes_processed', 0)} genes")
        return result
