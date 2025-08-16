"""
Progress tracker utility for real-time data source updates
"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.progress import DataSourceProgress, SourceStatus

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks and reports progress for data source updates"""

    def __init__(self,
                 db: Session,
                 source_name: str,
                 broadcast_callback: Callable | None = None):
        """
        Initialize progress tracker

        Args:
            db: Database session
            source_name: Name of the data source
            broadcast_callback: Optional callback for real-time updates
        """
        self.db = db
        self.source_name = source_name
        self.broadcast_callback = broadcast_callback
        self.progress_record = self._get_or_create_progress()
        self._update_interval = 1.0  # Update database every second
        self._last_update_time = datetime.now(timezone.utc)
        self._start_time = None

    def _get_or_create_progress(self) -> DataSourceProgress:
        """Get or create progress record for this source"""
        progress = self.db.query(DataSourceProgress).filter_by(
            source_name=self.source_name
        ).first()

        if not progress:
            progress = DataSourceProgress(
                source_name=self.source_name,
                status=SourceStatus.idle,
                progress_metadata={}
            )
            self.db.add(progress)
            self.db.commit()

        return progress

    @contextmanager
    def track_operation(self, operation_name: str):
        """Context manager for tracking an operation"""
        self.start(operation_name)
        try:
            yield self
        except Exception as e:
            self.error(str(e))
            raise
        finally:
            if self.progress_record.status == SourceStatus.running:
                self.complete()

    def start(self, operation: str = "Starting update"):
        """Mark source as running"""
        self._start_time = datetime.now(timezone.utc)
        self.progress_record.status = SourceStatus.running
        self.progress_record.current_operation = operation
        self.progress_record.started_at = self._start_time
        self.progress_record.completed_at = None
        self.progress_record.last_error = None
        self.progress_record.items_processed = 0
        self.progress_record.items_added = 0
        self.progress_record.items_updated = 0
        self.progress_record.items_failed = 0
        self.progress_record.progress_percentage = 0.0
        self._commit_and_broadcast()

    def update(self,
               current_item: int | None = None,
               total_items: int | None = None,
               current_page: int | None = None,
               total_pages: int | None = None,
               operation: str | None = None,
               items_added: int | None = None,
               items_updated: int | None = None,
               items_failed: int | None = None,
               force: bool = False):
        """
        Update progress information

        Args:
            current_item: Current item being processed
            total_items: Total number of items
            current_page: Current page (for paginated sources)
            total_pages: Total number of pages
            operation: Current operation description
            items_added: Number of items added (incremental)
            items_updated: Number of items updated (incremental)
            items_failed: Number of items failed (incremental)
            force: Force immediate database update
        """
        # Update counters
        if current_item is not None:
            self.progress_record.current_item = current_item
        if total_items is not None:
            self.progress_record.total_items = total_items
        if current_page is not None:
            self.progress_record.current_page = current_page
        if total_pages is not None:
            self.progress_record.total_pages = total_pages
        if operation is not None:
            self.progress_record.current_operation = operation

        # Update incremental counters
        if items_added is not None:
            self.progress_record.items_added += items_added
            self.progress_record.items_processed += items_added
        if items_updated is not None:
            self.progress_record.items_updated += items_updated
            self.progress_record.items_processed += items_updated
        if items_failed is not None:
            self.progress_record.items_failed += items_failed
            self.progress_record.items_processed += items_failed

        # Calculate progress percentage
        if self.progress_record.total_items and self.progress_record.total_items > 0:
            self.progress_record.progress_percentage = (
                self.progress_record.current_item / self.progress_record.total_items * 100
            )
        elif self.progress_record.total_pages and self.progress_record.total_pages > 0:
            self.progress_record.progress_percentage = (
                self.progress_record.current_page / self.progress_record.total_pages * 100
            )

        # Estimate completion time
        if self._start_time and self.progress_record.progress_percentage > 0:
            elapsed = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            if self.progress_record.progress_percentage > 0:
                total_time = elapsed / (self.progress_record.progress_percentage / 100)
                remaining = total_time - elapsed
                self.progress_record.estimated_completion = datetime.now(timezone.utc) + timedelta(seconds=remaining)

        # Only commit if enough time has passed or forced
        now = datetime.now(timezone.utc)
        if force or (now - self._last_update_time).total_seconds() >= self._update_interval:
            self._commit_and_broadcast()
            self._last_update_time = now

    def complete(self, operation: str = "Update completed"):
        """Mark source as completed"""
        self.progress_record.status = SourceStatus.completed
        self.progress_record.current_operation = operation
        self.progress_record.completed_at = datetime.now(timezone.utc)
        self.progress_record.progress_percentage = 100.0
        self.progress_record.estimated_completion = None
        self._commit_and_broadcast()

    def error(self, error_message: str):
        """Mark source as failed with error"""
        self.progress_record.status = SourceStatus.failed
        self.progress_record.last_error = error_message
        self.progress_record.current_operation = f"Failed: {error_message[:100]}"
        self.progress_record.estimated_completion = None
        self._commit_and_broadcast()

    def pause(self):
        """Mark source as paused"""
        self.progress_record.status = SourceStatus.paused
        self.progress_record.current_operation = "Paused"
        self.progress_record.estimated_completion = None
        self._commit_and_broadcast()

    def resume(self):
        """Resume from paused state"""
        self.progress_record.status = SourceStatus.running
        self.progress_record.current_operation = "Resumed"
        self._start_time = datetime.now(timezone.utc)  # Reset start time for accurate estimates
        self._commit_and_broadcast()

    def set_metadata(self, metadata: dict[str, Any]):
        """Update metadata"""
        self.progress_record.progress_metadata = metadata
        self._commit_and_broadcast()

    def _commit_and_broadcast(self):
        """Commit to database and broadcast update if callback provided"""
        try:
            self.db.commit()
            if self.broadcast_callback:
                # Try to run broadcast in background if in async context
                try:
                    asyncio.get_running_loop()
                    asyncio.create_task(self._broadcast_update())
                except RuntimeError:
                    # Not in async context, skip broadcast
                    pass
        except Exception as e:
            logger.error(f"Failed to update progress for {self.source_name}: {e}")
            self.db.rollback()

    async def _broadcast_update(self):
        """Broadcast update via callback"""
        try:
            if self.broadcast_callback:
                await self.broadcast_callback({
                    "type": "progress_update",
                    "source": self.source_name,
                    "data": self.progress_record.to_dict()
                })
        except Exception as e:
            logger.error(f"Failed to broadcast progress update: {e}")

    def get_status(self) -> dict[str, Any]:
        """Get current status as dictionary"""
        return self.progress_record.to_dict()

    def log_progress(self, level: int = logging.INFO):
        """Log current progress"""
        status = self.get_status()
        message = (
            f"[{self.source_name}] "
            f"{status['progress_percentage']:.1f}% "
            f"({status['items_processed']} processed, "
            f"{status['items_added']} added, "
            f"{status['items_updated']} updated, "
            f"{status['items_failed']} failed) "
            f"- {status['current_operation']}"
        )
        logger.log(level, message)
