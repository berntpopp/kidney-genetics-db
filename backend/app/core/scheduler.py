"""
Scheduler for automated annotation updates.
"""

from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.gene_annotation import AnnotationSource
from app.pipeline.annotation_pipeline import AnnotationPipeline, UpdateStrategy

logger = get_logger(__name__)


class AnnotationScheduler:
    """
    Manages scheduled updates for gene annotations.

    Runs periodic updates based on configured intervals for each source.
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def start(self):
        """Start the scheduler."""
        if not self.is_running:
            # Schedule daily incremental updates at 2 AM
            self.scheduler.add_job(
                self._run_incremental_update,
                CronTrigger(hour=2, minute=0),
                id="daily_incremental",
                name="Daily Incremental Update",
                replace_existing=True,
            )

            # Schedule weekly full update on Sundays at 3 AM
            self.scheduler.add_job(
                self._run_full_update,
                CronTrigger(day_of_week=6, hour=3, minute=0),
                id="weekly_full",
                name="Weekly Full Update",
                replace_existing=True,
            )

            # Schedule source-specific updates based on their TTL
            self._schedule_source_updates()

            self.scheduler.start()
            self.is_running = True
            logger.sync_info("Annotation scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.sync_info("Annotation scheduler stopped")

    def _schedule_source_updates(self):
        """Schedule updates for each source based on their configuration."""
        db = SessionLocal()
        try:
            sources = db.query(AnnotationSource).filter(AnnotationSource.is_active.is_(True)).all()

            for source in sources:
                if source.update_frequency == "daily":
                    # Schedule daily at 1 AM
                    self.scheduler.add_job(
                        self._run_source_update,
                        CronTrigger(hour=1, minute=0),
                        args=[source.source_name],
                        id=f"source_{source.source_name}",
                        name=f"Update {source.display_name}",
                        replace_existing=True,
                    )
                elif source.update_frequency == "weekly":
                    # Schedule weekly on Mondays at 1 AM
                    self.scheduler.add_job(
                        self._run_source_update,
                        CronTrigger(day_of_week=0, hour=1, minute=0),
                        args=[source.source_name],
                        id=f"source_{source.source_name}",
                        name=f"Update {source.display_name}",
                        replace_existing=True,
                    )
                elif source.update_frequency == "monthly":
                    # Schedule monthly on the 1st at 1 AM
                    self.scheduler.add_job(
                        self._run_source_update,
                        CronTrigger(day=1, hour=1, minute=0),
                        args=[source.source_name],
                        id=f"source_{source.source_name}",
                        name=f"Update {source.display_name}",
                        replace_existing=True,
                    )
                elif source.update_frequency == "quarterly":
                    # Schedule quarterly on the 1st of Jan, Apr, Jul, Oct at 1 AM
                    self.scheduler.add_job(
                        self._run_source_update,
                        CronTrigger(month="1,4,7,10", day=1, hour=1, minute=0),
                        args=[source.source_name],
                        id=f"source_{source.source_name}",
                        name=f"Update {source.display_name}",
                        replace_existing=True,
                    )

                if source.update_frequency in ["daily", "weekly", "monthly", "quarterly"]:
                    logger.sync_info(
                        f"Scheduled {source.update_frequency} update for {source.display_name}"
                    )
        finally:
            db.close()

    async def _run_incremental_update(self):
        """Run incremental update for all sources."""
        logger.sync_info("Starting scheduled incremental update")

        db = SessionLocal()
        try:
            pipeline = AnnotationPipeline(db)
            results = await pipeline.run_update(strategy=UpdateStrategy.INCREMENTAL, force=False)

            logger.sync_info("Scheduled incremental update completed", results=results)
        except Exception as e:
            logger.sync_error(f"Scheduled incremental update failed: {str(e)}")
        finally:
            db.close()

    async def _run_full_update(self):
        """Run full update for all sources."""
        logger.sync_info("Starting scheduled full update")

        db = SessionLocal()
        try:
            pipeline = AnnotationPipeline(db)
            results = await pipeline.run_update(strategy=UpdateStrategy.FULL, force=False)

            logger.sync_info("Scheduled full update completed", results=results)
        except Exception as e:
            logger.sync_error(f"Scheduled full update failed: {str(e)}")
        finally:
            db.close()

    async def _run_source_update(self, source_name: str):
        """Run update for a specific source."""
        logger.sync_info(f"Starting scheduled update for {source_name}")

        db = SessionLocal()
        try:
            pipeline = AnnotationPipeline(db)
            results = await pipeline.run_update(
                strategy=UpdateStrategy.SELECTIVE, sources=[source_name], force=False
            )

            logger.sync_info(f"Scheduled update for {source_name} completed", results=results)
        except Exception as e:
            logger.sync_error(f"Scheduled update for {source_name} failed: {str(e)}")
        finally:
            db.close()

    def get_jobs(self):
        """Get list of scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
            )
        return jobs

    def trigger_job(self, job_id: str):
        """Manually trigger a scheduled job."""
        job = self.scheduler.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())
            logger.sync_info(f"Manually triggered job: {job_id}")
            return True
        return False


# Global scheduler instance
annotation_scheduler = AnnotationScheduler()
