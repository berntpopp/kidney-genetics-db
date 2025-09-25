"""
Background task manager for concurrent data source updates with unified architecture.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.task_decorator import TaskMixin
from app.models.progress import DataSourceProgress, SourceStatus

logger = get_logger(__name__)


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
        logger.sync_info("Starting automatic data source updates...")

        db = next(get_db())
        try:
            # Get all sources with auto_update enabled
            all_progress = db.query(DataSourceProgress).all()

            for progress in all_progress:
                metadata = progress.progress_metadata or {}
                if metadata.get("auto_update", False):
                    # Check if source needs updating based on its status
                    if progress.status in [SourceStatus.idle, SourceStatus.failed]:
                        logger.sync_info(
                            "Starting auto-update for source", source_name=progress.source_name
                        )
                        asyncio.create_task(self.run_source(progress.source_name))
                    elif progress.status == SourceStatus.paused:
                        logger.sync_info(
                            "Resuming paused update for source", source_name=progress.source_name
                        )
                        asyncio.create_task(self.run_source(progress.source_name, resume=True))
        finally:
            db.close()

    async def run_source(self, source_name: str, resume: bool = False, mode: str = "smart"):
        """
        Run update for a specific data source using dynamic dispatch.

        Args:
            source_name: Name of the data source
            resume: Whether to resume from previous position
            mode: Update mode - "smart" (incremental) or "full" (complete refresh)
        """
        logger.sync_info(
            "Task manager run_source() called",
            source_name=source_name,
            resume=resume,
            mode=mode,
            running_tasks=list(self.running_tasks.keys()),
        )

        # Check if already running
        if source_name in self.running_tasks and not self.running_tasks[source_name].done():
            logger.sync_warning(
                "Source is already running",
                source_name=source_name,
                task=str(self.running_tasks[source_name]),
            )
            return

        # Dynamic task dispatch
        method_name = f"_run_{source_name.lower().replace('_', '_')}"
        logger.sync_info(
            "Looking for task method",
            method_name=method_name,
            source_name=source_name,
            available_methods=[m for m in dir(self) if m.startswith("_run_")],
        )

        try:
            task_method = getattr(self, method_name, None)
            logger.sync_debug("Task method lookup result", task_method=str(task_method))
        except Exception as e:
            logger.sync_error("Exception in task method lookup", error=e, source_name=source_name)
            return

        if not task_method:
            logger.sync_error(
                "No task method found for source", source_name=source_name, method_name=method_name
            )
            return

        logger.sync_debug(
            "Found task method", task_method=str(task_method), is_callable=callable(task_method)
        )

        try:
            logger.sync_info("Creating asyncio task", source_name=source_name)
            # Pass mode parameter to all sources uniformly
            task = asyncio.create_task(task_method(resume=resume, mode=mode))
            logger.sync_debug("Created task", task=str(task))

            self.running_tasks[source_name] = task
            logger.sync_info(
                "Stored task for source",
                source_name=source_name,
                total_running=len(self.running_tasks),
            )

            # Add task completion callback
            task.add_done_callback(
                lambda t: logger.sync_info(
                    "Task completed",
                    source_name=source_name,
                    done=t.done(),
                    exception=str(t.exception()) if t.done() and t.exception() else None,
                )
            )

        except Exception as e:
            logger.sync_error("Exception creating/storing task", error=e, source_name=source_name)
            import traceback

            logger.sync_error(
                "Full traceback for task creation failure",
                traceback=traceback.format_exc(),
                source_name=source_name,
            )
            raise

    def cancel_task(self, source_name: str) -> bool:
        """
        Cancel a running task for a specific source

        Args:
            source_name: Name of the source to cancel

        Returns:
            True if task was cancelled, False if no task was running
        """
        if source_name in self.running_tasks:
            task = self.running_tasks[source_name]
            if not task.done():
                logger.sync_info(f"Cancelling task for {source_name}")
                task.cancel()
                # Remove from running tasks
                del self.running_tasks[source_name]
                return True
            elif task.done():
                # Clean up completed task
                del self.running_tasks[source_name]
        return False

    async def shutdown(self):
        """Gracefully shutdown all running tasks"""
        logger.sync_info("Shutting down background tasks...")
        self._shutdown = True

        # Cancel all running tasks
        for source_name, task in self.running_tasks.items():
            if not task.done():
                logger.sync_info("Cancelling task", source_name=source_name)
                task.cancel()

        # Wait for all tasks to complete
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)

        # Shutdown executor
        self.executor.shutdown(wait=True)
        logger.sync_info("Background tasks shutdown complete")


# Global task manager instance
task_manager = BackgroundTaskManager()
