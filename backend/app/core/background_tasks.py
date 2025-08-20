"""
Background task manager for concurrent data source updates with unified architecture.
"""

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.core.database import get_db
from app.core.task_decorator import TaskMixin
from app.models.progress import DataSourceProgress, SourceStatus

logger = logging.getLogger(__name__)

class BackgroundTaskManager(TaskMixin):
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
        Run update for a specific data source using dynamic dispatch.

        Args:
            source_name: Name of the data source
            resume: Whether to resume from previous position
        """
        logger.info(
            f"🏃 TASK MANAGER: run_source() CALLED for source: {source_name}, resume: {resume}"
        )
        logger.info(f"🏃 TASK MANAGER: Current running tasks: {list(self.running_tasks.keys())}")

        # Check if already running
        if source_name in self.running_tasks and not self.running_tasks[source_name].done():
            logger.warning(
                f"🏃 TASK MANAGER: {source_name} is already running, task: {self.running_tasks[source_name]}"
            )
            return

        # Dynamic task dispatch
        method_name = f"_run_{source_name.lower().replace('_', '_')}"
        logger.info(
            f"🏃 TASK MANAGER: Looking for method '{method_name}' for source '{source_name}'"
        )
        logger.info(
            f"🏃 TASK MANAGER: Available methods on self: {[m for m in dir(self) if m.startswith('_run_')]}"
        )

        try:
            task_method = getattr(self, method_name, None)
            logger.info(f"🏃 TASK MANAGER: getattr result: {task_method}")
        except Exception as e:
            logger.error(f"🏃 TASK MANAGER: Exception in getattr: {e}")
            return

        if not task_method:
            logger.error(f"🏃 TASK MANAGER: No method found for source: {source_name}")
            logger.error(f"🏃 TASK MANAGER: Tried method name: {method_name}")
            return

        logger.info(f"🏃 TASK MANAGER: Found method: {task_method}")
        logger.info(f"🏃 TASK MANAGER: Method callable: {callable(task_method)}")

        try:
            logger.info(f"🏃 TASK MANAGER: Creating asyncio task for {source_name}")
            task = asyncio.create_task(task_method(resume=resume))
            logger.info(f"🏃 TASK MANAGER: Created task: {task}")

            self.running_tasks[source_name] = task
            logger.info(
                f"🏃 TASK MANAGER: Stored task for {source_name}, total running: {len(self.running_tasks)}"
            )

            # Add task completion callback
            task.add_done_callback(
                lambda t: logger.info(
                    f"🏃 TASK MANAGER: Task {source_name} completed: {t.done()}, exception: {t.exception() if t.done() else 'N/A'}"
                )
            )

        except Exception as e:
            logger.error(f"🏃 TASK MANAGER: Exception creating/storing task for {source_name}: {e}")
            import traceback

            logger.error(f"🏃 TASK MANAGER: Full traceback: {traceback.format_exc()}")
            raise

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
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)

        # Shutdown executor
        self.executor.shutdown(wait=True)
        logger.info("Background tasks shutdown complete")

# Global task manager instance
task_manager = BackgroundTaskManager()
