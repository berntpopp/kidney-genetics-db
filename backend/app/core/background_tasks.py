"""
Background task manager for concurrent data source updates
"""

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.core.database import get_db
from app.core.progress_tracker import ProgressTracker
from app.models.progress import DataSourceProgress, SourceStatus

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Manages background tasks for all data sources"""

    def __init__(self):
        self.running_tasks: dict[str, asyncio.Task] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.broadcast_callback = None
        self._shutdown = False

    def set_broadcast_callback(self, callback: Callable):
        """Set the callback for broadcasting updates"""
        self.broadcast_callback = callback

    async def start_auto_updates(self):
        """Start automatic updates for all sources marked with auto_update=true"""
        logger.info("Starting automatic data source updates...")

        db = next(get_db())
        try:
            # Get all sources with auto_update enabled
            all_progress = db.query(DataSourceProgress).all()

            for progress in all_progress:
                metadata = progress.progress_metadata or {}
                if metadata.get("auto_update", False):
                    # Check if source needs updating based on its status
                    if progress.status in [SourceStatus.idle, SourceStatus.failed]:
                        logger.info(f"Starting auto-update for {progress.source_name}")
                        asyncio.create_task(self.run_source(progress.source_name))
                    elif progress.status == SourceStatus.paused:
                        logger.info(f"Resuming paused update for {progress.source_name}")
                        asyncio.create_task(self.run_source(progress.source_name, resume=True))
        finally:
            db.close()

    async def run_source(self, source_name: str, resume: bool = False):
        """
        Run update for a specific data source

        Args:
            source_name: Name of the data source
            resume: Whether to resume from previous position
        """
        # Check if already running
        if source_name in self.running_tasks and not self.running_tasks[source_name].done():
            logger.warning(f"{source_name} is already running")
            return

        # Create task based on source
        if source_name == "PubTator":
            task = asyncio.create_task(self._run_pubtator(resume))
        elif source_name == "PanelApp":
            task = asyncio.create_task(self._run_panelapp(resume))
        elif source_name == "ClinGen":
            task = asyncio.create_task(self._run_clingen(resume))
        elif source_name == "GenCC":
            task = asyncio.create_task(self._run_gencc(resume))
        elif source_name == "HPO":
            task = asyncio.create_task(self._run_hpo(resume))
        elif source_name == "HGNC_Normalization":
            task = asyncio.create_task(self._run_hgnc_normalization(resume))
        elif source_name == "Evidence_Aggregation":
            task = asyncio.create_task(self._run_evidence_aggregation(resume))
        else:
            logger.error(f"Unknown source: {source_name}")
            return

        self.running_tasks[source_name] = task

    async def _run_pubtator(self, resume: bool = False):
        """Run PubTator update with progress tracking"""
        from app.pipeline.sources.pubtator_async import update_pubtator_async

        db = next(get_db())
        tracker = ProgressTracker(db, "PubTator", self.broadcast_callback)

        try:
            # Run async version that won't block
            result = await update_pubtator_async(db, tracker)
            logger.info(f"PubTator update completed: {result}")

        except Exception as e:
            logger.error(f"PubTator update failed: {e}")
            tracker.error(str(e))
        finally:
            db.close()

    async def _run_panelapp(self, resume: bool = False):
        """Run PanelApp update with progress tracking"""
        from app.pipeline.sources.update_all_with_progress import update_panelapp_with_progress

        db = next(get_db())
        tracker = ProgressTracker(db, "PanelApp", self.broadcast_callback)

        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                update_panelapp_with_progress,
                db,
                tracker
            )

            logger.info(f"PanelApp update completed: {result}")

        except Exception as e:
            logger.error(f"PanelApp update failed: {e}")
            tracker.error(str(e))
        finally:
            db.close()

    async def _run_clingen(self, resume: bool = False):
        """Run ClinGen update with progress tracking"""
        from app.pipeline.sources.update_all_with_progress import update_clingen_with_progress

        db = next(get_db())
        tracker = ProgressTracker(db, "ClinGen", self.broadcast_callback)

        try:
            # Run synchronous code in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                update_clingen_with_progress,
                db,
                tracker
            )

            logger.info(f"ClinGen update completed: {result}")

        except Exception as e:
            logger.error(f"ClinGen update failed: {e}")
            tracker.error(str(e))
        finally:
            db.close()

    async def _run_gencc(self, resume: bool = False):
        """Run GenCC update with unified client"""
        logger.info(f"🚀 Starting GenCC update with unified client (resume={resume})")

        db = next(get_db())
        tracker = ProgressTracker(db, "GenCC", self.broadcast_callback)

        try:
            from app.pipeline.sources.gencc_unified import get_gencc_client
            
            client = get_gencc_client(db_session=db)
            result = await client.update_data(db, tracker)
            logger.info(f"✅ GenCC update completed: {result}")

        except Exception as e:
            logger.error(f"❌ GenCC update failed: {e}")
            tracker.error(str(e))
        finally:
            db.close()

    async def _run_hpo(self, resume: bool = False):
        """Run HPO update with progress tracking"""
        from app.pipeline.sources.hpo_async import update_hpo_async

        # Create a tracker for HPO
        db = next(get_db())
        tracker = ProgressTracker(db, "HPO", broadcast_callback=self.broadcast_callback)
        tracker.start("HPO")

        try:
            logger.info("Starting HPO data update...")

            # The tracker already has a database session, use it
            try:
                stats = await update_hpo_async(db, tracker)

                if stats.get("completed"):
                    tracker.complete("HPO")
                    logger.info(f"✅ HPO update completed: {stats}")
                else:
                    tracker.fail("HPO", stats.get("error", "Unknown error"))
                    logger.error(f"❌ HPO update failed: {stats}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"HPO update error: {e}", exc_info=True)
            tracker.error(str(e))

    async def _run_hgnc_normalization(self, resume: bool = False):
        """Run HGNC normalization with progress tracking"""
        from app.pipeline.normalize import normalize_all_genes

        db = next(get_db())
        tracker = ProgressTracker(db, "HGNC_Normalization", self.broadcast_callback)

        try:
            with tracker.track_operation("Normalizing gene symbols"):
                # Run synchronous code in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    normalize_all_genes,
                    db
                )

                tracker.update(
                    items_added=result.get("normalized", 0),
                    items_updated=result.get("updated", 0),
                    items_failed=result.get("failed", 0)
                )

        except Exception as e:
            logger.error(f"HGNC normalization failed: {e}")
            tracker.error(str(e))
        finally:
            db.close()

    async def _run_evidence_aggregation(self, resume: bool = False):
        """Run evidence aggregation with progress tracking"""
        from app.pipeline.aggregate import update_all_curations

        # Create separate sessions for tracker and aggregation
        tracker_db = next(get_db())
        tracker = ProgressTracker(tracker_db, "Evidence_Aggregation", self.broadcast_callback)

        try:
            tracker.start("Starting evidence aggregation")

            # Run synchronous code in executor with its own DB session
            loop = asyncio.get_event_loop()

            def run_aggregation():
                """Run aggregation with its own DB session"""
                agg_db = next(get_db())
                try:
                    result = update_all_curations(agg_db)
                    return result
                finally:
                    agg_db.close()

            result = await loop.run_in_executor(
                self.executor,
                run_aggregation
            )

            tracker.update(
                items_updated=result.get("curations_updated", 0),
                items_added=result.get("curations_created", 0)
            )
            tracker.complete(f"Aggregated evidence for {result.get('genes_processed', 0)} genes")

        except Exception as e:
            logger.error(f"Evidence aggregation failed: {e}")
            tracker.error(str(e))
        finally:
            tracker_db.close()

    async def shutdown(self):
        """Gracefully shutdown all running tasks"""
        logger.info("Shutting down background tasks...")
        self._shutdown = True

        # Cancel all running tasks
        for source_name, task in self.running_tasks.items():
            if not task.done():
                logger.info(f"Cancelling {source_name} task")
                task.cancel()

        # Wait for all tasks to complete
        if self.running_tasks:
            await asyncio.gather(
                *self.running_tasks.values(),
                return_exceptions=True
            )

        # Shutdown executor
        self.executor.shutdown(wait=True)
        logger.info("Background tasks shutdown complete")


# Global task manager instance
task_manager = BackgroundTaskManager()
