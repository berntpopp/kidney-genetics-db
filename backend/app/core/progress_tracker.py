"""
Progress tracker utility for real-time data source updates
OPTIMIZED: Uses event bus for notifications instead of direct callbacks
"""

import asyncio
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.events import EventTypes, event_bus
from app.core.logging import get_logger
from app.models.progress import DataSourceProgress, SourceStatus

logger = get_logger(__name__)


class ProgressTracker:
    """Tracks and reports progress for data source updates"""

    def __init__(self, db: Session, source_name: str, broadcast_callback: Callable | None = None):
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
        # Don't create progress records for manual upload sources
        manual_upload_sources = ["DiagnosticPanels"]
        if self.source_name in manual_upload_sources:
            # Return a temporary non-persisted record for manual sources
            return DataSourceProgress(
                source_name=self.source_name,
                status=SourceStatus.idle,
                progress_metadata={"upload_type": "manual"},
            )

        progress = self.db.query(DataSourceProgress).filter_by(source_name=self.source_name).first()

        if not progress:
            logger.sync_info(
                "Creating new progress record",
                source_name=self.source_name,
            )
            progress = DataSourceProgress(
                source_name=self.source_name, status=SourceStatus.idle, progress_metadata={}
            )
            self.db.add(progress)
            self.db.commit()
            logger.sync_info(
                "Progress record created",
                source_name=self.source_name,
                progress_id=progress.id,
            )
        else:
            logger.sync_info(
                "Found existing progress record",
                source_name=self.source_name,
                progress_id=progress.id,
                current_status=str(progress.status),
                last_updated=str(progress.updated_at),
            )
            # Ensure the progress record is attached to current session
            if progress not in self.db:
                logger.sync_warning(
                    "Progress record not in current session, merging",
                    source_name=self.source_name,
                    current_status=str(progress.status),
                )
                # Store the current status before merge
                current_status = progress.status
                progress = self.db.merge(progress)
                # Restore status if it was changed by merge
                if progress.status != current_status:
                    logger.sync_warning(
                        "Status changed during merge, restoring",
                        source_name=self.source_name,
                        old_status=str(current_status),
                        new_status=str(progress.status),
                    )
                    progress.status = current_status

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
        logger.sync_debug(
            "ProgressTracker.start() called",
            source_name=self.source_name,
            operation=operation,
            old_status=str(self.progress_record.status),
        )
        self._start_time = datetime.now(timezone.utc)
        self.progress_record.status = SourceStatus.running
        self.progress_record.current_operation = operation
        self.progress_record.started_at = self._start_time
        self.progress_record.completed_at = None
        self.progress_record.error_message = None
        self.progress_record.items_processed = 0
        self.progress_record.items_added = 0
        self.progress_record.items_updated = 0
        self.progress_record.items_failed = 0
        self.progress_record.progress_percentage = 0.0
        self.progress_record.current_item = 0
        self.progress_record.total_items = None
        self._commit_and_broadcast()
        logger.sync_debug(
            "ProgressTracker.start() completed",
            source_name=self.source_name,
            new_status=str(self.progress_record.status),
        )

    def update(
        self,
        current_item: int | None = None,
        total_items: int | None = None,
        current_page: int | None = None,
        total_pages: int | None = None,
        operation: str | None = None,
        items_added: int | None = None,
        items_updated: int | None = None,
        items_failed: int | None = None,
        force: bool = False,
    ):
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
        # Log update call
        logger.sync_debug(
            "ProgressTracker.update() called",
            source_name=self.source_name,
            current_page=current_page,
            current_item=current_item,
            operation=operation,
            force=force,
            current_status=str(self.progress_record.status),
        )

        # Preserve running status if already set
        if self.progress_record.status != SourceStatus.running:
            logger.sync_warning(
                "Update called but status is not running!",
                source_name=self.source_name,
                current_status=str(self.progress_record.status),
            )

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
        # Prefer pages over items for better accuracy when both are available
        if self.progress_record.total_pages and self.progress_record.total_pages > 0:
            self.progress_record.progress_percentage = (
                self.progress_record.current_page / self.progress_record.total_pages * 100
            )
        elif self.progress_record.total_items and self.progress_record.total_items > 0:
            self.progress_record.progress_percentage = (
                self.progress_record.current_item / self.progress_record.total_items * 100
            )

        # Estimate completion time
        if self._start_time and self.progress_record.progress_percentage > 0:
            elapsed = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            if self.progress_record.progress_percentage > 0:
                total_time = elapsed / (self.progress_record.progress_percentage / 100)
                remaining = total_time - elapsed
                self.progress_record.estimated_completion = datetime.now(timezone.utc) + timedelta(
                    seconds=remaining
                )

        # Only commit if enough time has passed or forced
        now = datetime.now(timezone.utc)
        time_since_last = (now - self._last_update_time).total_seconds()
        should_update = force or time_since_last >= self._update_interval

        logger.sync_debug(
            "ProgressTracker.update() commit decision",
            source_name=self.source_name,
            force=force,
            time_since_last=time_since_last,
            update_interval=self._update_interval,
            should_update=should_update,
        )

        if should_update:
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
        self.progress_record.error_message = error_message
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
        logger.sync_debug(
            "ProgressTracker.resume() called",
            source_name=self.source_name,
            old_status=str(self.progress_record.status),
            progress_id=self.progress_record.id if hasattr(self.progress_record, "id") else None,
        )
        self.progress_record.status = SourceStatus.running
        self.progress_record.current_operation = "Resumed"
        self._start_time = datetime.now(timezone.utc)  # Reset start time for accurate estimates
        # Force immediate database commit to persist status change
        self._commit_and_broadcast()
        logger.sync_debug(
            "ProgressTracker.resume() completed",
            source_name=self.source_name,
            new_status=str(self.progress_record.status),
        )

    def is_paused(self) -> bool:
        """Check if the source is currently paused"""
        return self.progress_record.status == SourceStatus.paused

    def set_metadata(self, metadata: dict[str, Any]):
        """Update metadata"""
        self.progress_record.progress_metadata = metadata
        self._commit_and_broadcast()

    def _commit_and_broadcast(self):
        """Commit to database and publish update to event bus - NO MORE DIRECT CALLBACKS!"""
        # Always recalculate progress percentage before committing
        # Prefer pages over items for better accuracy when both are available
        if self.progress_record.total_pages and self.progress_record.total_pages > 0:
            self.progress_record.progress_percentage = (
                self.progress_record.current_page / self.progress_record.total_pages * 100
            )
        elif self.progress_record.total_items and self.progress_record.total_items > 0:
            self.progress_record.progress_percentage = (
                self.progress_record.current_item / self.progress_record.total_items * 100
            )

        logger.sync_debug(
            "_commit_and_broadcast() called",
            source_name=self.source_name,
            status=str(self.progress_record.status),
            current_page=self.progress_record.current_page,
            current_operation=self.progress_record.current_operation,
            progress_percentage=self.progress_record.progress_percentage,
        )

        try:
            # Don't commit manual upload sources to database
            manual_upload_sources = ["DiagnosticPanels"]
            if self.source_name not in manual_upload_sources:
                logger.sync_debug(
                    "Committing to database",
                    source_name=self.source_name,
                    progress_id=self.progress_record.id
                    if hasattr(self.progress_record, "id")
                    else None,
                )
                # Ensure the progress record is marked as modified
                if self.progress_record in self.db:
                    # Mark object as dirty to ensure SQLAlchemy tracks changes
                    # Explicitly set the status to ensure it's not overwritten
                    current_status = self.progress_record.status
                    self.db.add(self.progress_record)
                    # Double-check status didn't change after adding to session
                    if self.progress_record.status != current_status:
                        logger.sync_warning(
                            "Status changed after adding to session!",
                            source_name=self.source_name,
                            expected_status=str(current_status),
                            actual_status=str(self.progress_record.status),
                        )
                        # Force the correct status
                        self.progress_record.status = current_status
                else:
                    logger.sync_warning(
                        "Progress record not in session, merging it",
                        source_name=self.source_name,
                    )
                    # Use merge instead of add to avoid conflicts
                    self.progress_record = self.db.merge(self.progress_record)

                self.db.commit()
                logger.sync_debug(
                    "Database commit successful",
                    source_name=self.source_name,
                )
            else:
                logger.sync_debug(
                    "Skipping database commit for manual upload source",
                    source_name=self.source_name,
                )

            # Publish to event bus instead of direct callback
            # This eliminates the need for complex async/sync handling
            progress_data = self.progress_record.to_dict()

            # Determine event type based on status
            if self.progress_record.status == SourceStatus.running:
                event_type = EventTypes.PROGRESS_UPDATE
            elif self.progress_record.status == SourceStatus.completed:
                event_type = EventTypes.TASK_COMPLETED
            elif self.progress_record.status == SourceStatus.failed:
                event_type = EventTypes.TASK_FAILED
            else:
                event_type = EventTypes.PROGRESS_UPDATE

            # Try to publish event if in async context
            try:
                asyncio.get_running_loop()
                asyncio.create_task(event_bus.publish(event_type, progress_data))
                logger.sync_debug(
                    "Event published to event bus",
                    source_name=self.source_name,
                    event_type=event_type,
                )
            except RuntimeError:
                # Not in async context, log instead
                logger.sync_debug(
                    "Progress update (sync context - no event bus)",
                    source_name=self.source_name,
                    status=self.progress_record.status.value
                    if hasattr(self.progress_record.status, "value")
                    else str(self.progress_record.status),
                )
        except Exception as e:
            logger.sync_error(
                "Failed to update progress - rolling back",
                source_name=self.source_name,
                error=str(e),
            )
            self.db.rollback()
            raise  # Re-raise to see what's failing

    async def _broadcast_update(self):
        """Broadcast update via callback"""
        try:
            if self.broadcast_callback:
                await self.broadcast_callback(
                    {
                        "type": "progress_update",
                        "source": self.source_name,
                        "data": self.progress_record.to_dict(),
                    }
                )
        except Exception as e:
            logger.sync_error("Failed to broadcast progress update", error=str(e))

    def get_current_operation(self) -> str | None:
        """Get the current operation being performed"""
        return self.progress_record.current_operation if self.progress_record else None

    def get_status(self) -> dict[str, Any]:
        """Get current status as dictionary"""
        return self.progress_record.to_dict()

    def log_progress(self, level: str = "INFO"):
        """Log current progress"""
        status = self.get_status()

        # Use structured logging with appropriate level
        log_data = {
            "source_name": self.source_name,
            "progress_percentage": round(status["progress_percentage"], 1),
            "items_processed": status["items_processed"],
            "items_added": status["items_added"],
            "items_updated": status["items_updated"],
            "items_failed": status["items_failed"],
            "current_operation": status["current_operation"],
        }

        if level.upper() == "DEBUG":
            logger.sync_debug("Progress update", **log_data)
        elif level.upper() == "WARNING":
            logger.sync_warning("Progress update", **log_data)
        elif level.upper() == "ERROR":
            logger.sync_error("Progress update", **log_data)
        else:
            logger.sync_info("Progress update", **log_data)
