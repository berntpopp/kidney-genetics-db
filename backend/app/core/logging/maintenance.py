"""
Automated maintenance tasks for the logging system.

Provides scheduled tasks for log cleanup, optimization, and monitoring.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.logging import get_logger

logger = get_logger(__name__)


class LogMaintenance:
    """Handles automated log maintenance tasks."""

    def __init__(
        self,
        retention_days: int = 30,
        cleanup_interval_hours: int = 24,
        optimization_interval_days: int = 7,
    ):
        """
        Initialize log maintenance configuration.

        Args:
            retention_days: Number of days to retain logs
            cleanup_interval_hours: Hours between cleanup runs
            optimization_interval_days: Days between table optimization
        """
        self.retention_days = retention_days
        self.cleanup_interval_hours = cleanup_interval_hours
        self.optimization_interval_days = optimization_interval_days
        self._cleanup_task = None
        self._monitor_task = None

    async def start(self):
        """Start automated maintenance tasks."""
        await logger.info(
            "Starting log maintenance",
            retention_days=self.retention_days,
            cleanup_interval_hours=self.cleanup_interval_hours,
        )

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Stop automated maintenance tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()

        if self._monitor_task:
            self._monitor_task.cancel()

        await logger.info("Log maintenance stopped")

    async def _cleanup_loop(self):
        """Background loop for periodic log cleanup."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
                await self.cleanup_old_logs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                await logger.error("Cleanup loop error", error=str(e))

    async def _monitor_loop(self):
        """Background loop for monitoring log volume."""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                await self.monitor_log_volume()
            except asyncio.CancelledError:
                break
            except Exception as e:
                await logger.error("Monitor loop error", error=str(e))

    async def cleanup_old_logs(self) -> dict:
        """
        Clean up logs older than retention period.

        Returns:
            Statistics about the cleanup operation
        """
        # Import here to avoid circular import
        from app.core.database import get_db

        db = next(get_db())
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

            # Count logs to be deleted
            count_query = "SELECT COUNT(*) FROM system_logs WHERE timestamp < :cutoff"
            count_result = db.execute(text(count_query), {"cutoff": cutoff_time}).scalar()

            if count_result > 0:
                # Delete old logs in batches to avoid locking
                batch_size = 1000
                total_deleted = 0

                while True:
                    delete_query = """
                        DELETE FROM system_logs
                        WHERE id IN (
                            SELECT id FROM system_logs
                            WHERE timestamp < :cutoff
                            LIMIT :batch_size
                        )
                    """

                    result = db.execute(
                        text(delete_query), {"cutoff": cutoff_time, "batch_size": batch_size}
                    )

                    deleted = result.rowcount
                    total_deleted += deleted
                    db.commit()

                    if deleted < batch_size:
                        break

                    await asyncio.sleep(0.1)  # Brief pause between batches

                await logger.info(
                    "Log cleanup completed",
                    logs_deleted=total_deleted,
                    cutoff_date=cutoff_time.isoformat(),
                )

                return {"logs_deleted": total_deleted, "cutoff_date": cutoff_time.isoformat()}
            else:
                await logger.debug("No logs to cleanup", cutoff_date=cutoff_time.isoformat())
                return {"logs_deleted": 0}

        except Exception as e:
            await logger.error("Log cleanup failed", error=str(e))
            raise
        finally:
            db.close()

    async def monitor_log_volume(self) -> dict:
        """
        Monitor log volume and alert if growing too fast.

        Returns:
            Current log volume statistics
        """
        # Import here to avoid circular import
        from app.core.database import get_db

        db = next(get_db())
        try:
            # Get current statistics
            stats_query = """
                SELECT
                    COUNT(*) as total_logs,
                    COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '1 hour') as last_hour,
                    COUNT(*) FILTER (WHERE timestamp > NOW() - INTERVAL '24 hours') as last_day,
                    COUNT(*) FILTER (WHERE level = 'ERROR' AND timestamp > NOW() - INTERVAL '1 hour') as errors_last_hour,
                    pg_total_relation_size('system_logs') as table_size_bytes
                FROM system_logs
            """

            result = db.execute(text(stats_query)).first()

            stats = {
                "total_logs": result.total_logs,
                "last_hour": result.last_hour,
                "last_day": result.last_day,
                "errors_last_hour": result.errors_last_hour,
                "table_size_mb": round(result.table_size_bytes / 1024 / 1024, 2),
            }

            # Check for anomalies
            if result.last_hour > 10000:
                await logger.warning("High log volume detected", logs_last_hour=result.last_hour)

            if result.errors_last_hour > 100:
                await logger.warning(
                    "High error rate detected", errors_last_hour=result.errors_last_hour
                )

            if result.table_size_bytes > 1024 * 1024 * 1024:  # 1GB
                await logger.warning("Large log table size", size_mb=stats["table_size_mb"])

            return stats

        except Exception as e:
            await logger.error("Log monitoring failed", error=str(e))
            raise
        finally:
            db.close()

    async def optimize_log_table(self):
        """
        Optimize the log table for better performance.

        Runs VACUUM and ANALYZE on the system_logs table.
        """
        # Import here to avoid circular import
        from app.core.database import get_db

        db = next(get_db())
        try:
            # Note: VACUUM cannot run in a transaction
            db.execute(text("COMMIT"))  # End any existing transaction
            db.execute(text("VACUUM ANALYZE system_logs"))

            await logger.info("Log table optimized")

        except Exception as e:
            await logger.error("Table optimization failed", error=str(e))
            raise
        finally:
            db.close()


# Global instance
log_maintenance = LogMaintenance()


async def setup_log_maintenance(retention_days: int = 30, cleanup_interval_hours: int = 24):
    """
    Setup and start log maintenance tasks.

    Should be called during application startup.
    """
    global log_maintenance
    log_maintenance = LogMaintenance(
        retention_days=retention_days, cleanup_interval_hours=cleanup_interval_hours
    )
    await log_maintenance.start()


async def shutdown_log_maintenance():
    """
    Stop log maintenance tasks.

    Should be called during application shutdown.
    """
    if log_maintenance:
        await log_maintenance.stop()
