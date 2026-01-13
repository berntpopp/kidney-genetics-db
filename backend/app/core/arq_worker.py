"""
ARQ Worker configuration for background pipeline tasks.

This module defines the worker settings and lifecycle hooks.
Run with: arq app.core.arq_worker.WorkerSettings
"""

from typing import Any

from arq.connections import RedisSettings
from sqlalchemy import text

from app.core.arq_tasks import run_annotation_pipeline_task, run_pipeline_task
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """
    Worker startup hook - initialize shared resources.

    This runs once when the worker starts. We initialize the database
    connection and other shared resources here.
    """
    logger.sync_info(
        "ARQ Worker starting up",
        queue_name=settings.ARQ_QUEUE_NAME,
        max_jobs=settings.ARQ_MAX_JOBS,
        job_timeout=settings.ARQ_JOB_TIMEOUT,
    )

    # Initialize database pool
    from app.core.database import engine

    # Test database connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    ctx["db_initialized"] = True
    logger.sync_info("ARQ Worker startup complete - database connection verified")


async def shutdown(ctx: dict[str, Any]) -> None:
    """
    Worker shutdown hook - cleanup resources.

    This runs when the worker receives a shutdown signal.
    """
    logger.sync_info("ARQ Worker shutting down")

    # Close the ARQ pool if it was initialized
    from app.core.arq_client import close_arq_pool

    await close_arq_pool()

    logger.sync_info("ARQ Worker shutdown complete")


async def on_job_start(ctx: dict[str, Any]) -> None:
    """Called when a job starts executing."""
    job_id = ctx.get("job_id", "unknown")
    logger.sync_info("Job starting", job_id=job_id)


async def on_job_end(ctx: dict[str, Any]) -> None:
    """Called when a job completes (success or failure)."""
    job_id = ctx.get("job_id", "unknown")
    logger.sync_info("Job ended", job_id=job_id)


class WorkerSettings:
    """
    ARQ Worker configuration.

    This class defines all settings for the ARQ worker process.
    """

    # Task functions (imported at module level to avoid class-scoped import)
    functions = [run_pipeline_task, run_annotation_pipeline_task]

    # Redis connection settings
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    # Queue configuration
    queue_name = settings.ARQ_QUEUE_NAME

    # Concurrency settings
    max_jobs = settings.ARQ_MAX_JOBS  # Max concurrent jobs

    # Timeout settings
    job_timeout = settings.ARQ_JOB_TIMEOUT  # 2 hours max per job

    # Retry settings
    max_tries = 3  # Retry failed jobs up to 3 times

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    on_job_start = on_job_start
    on_job_end = on_job_end

    # Health check settings
    health_check_interval = 30  # Seconds between health checks

    # Keep alive settings
    keep_result = 3600  # Keep job results for 1 hour
