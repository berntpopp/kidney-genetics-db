"""
ARQ Worker configuration for background pipeline tasks.

This module defines the worker settings and lifecycle hooks.
Run with: arq app.core.arq_worker.WorkerSettings

Deployment:
    1. Ensure Redis is running (see docker-compose.services.yml)
    2. Set USE_ARQ_WORKER=true in environment
    3. Start worker: cd backend && uv run arq app.core.arq_worker.WorkerSettings

Timeouts:
    - Default job timeout: 6 hours (configurable via ARQ_JOB_TIMEOUT)
    - Single source updates: 2 hours
    - Full annotation pipeline: 6 hours (rate-limited APIs like ClinVar need this)
"""

from typing import Any

from arq.connections import RedisSettings
from arq.worker import func
from sqlalchemy import text

from app.core.arq_tasks import (
    FULL_PIPELINE_TIMEOUT,
    SINGLE_SOURCE_TIMEOUT,
    run_annotation_pipeline_task,
    run_pipeline_task,
)
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

    Per-job timeouts are set using func() wrapper:
    - run_pipeline_task: 2 hours (single source like ClinVar, Ensembl)
    - run_annotation_pipeline_task: 6 hours (full pipeline with all sources)
    """

    # Task functions with per-job timeouts
    # Using func() wrapper allows different timeouts per task type
    # See: https://arq-docs.helpmanual.io/
    functions = [
        func(run_pipeline_task, timeout=SINGLE_SOURCE_TIMEOUT),  # 2 hours
        func(run_annotation_pipeline_task, timeout=FULL_PIPELINE_TIMEOUT),  # 6 hours
    ]

    # Redis connection settings
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    # Queue configuration
    queue_name = settings.ARQ_QUEUE_NAME

    # Concurrency settings
    max_jobs = settings.ARQ_MAX_JOBS  # Max concurrent jobs

    # Timeout settings (default fallback, per-job timeouts override this)
    job_timeout = settings.ARQ_JOB_TIMEOUT  # 6 hours default

    # Retry settings
    max_tries = 3  # Retry failed jobs up to 3 times

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    on_job_start = on_job_start
    on_job_end = on_job_end

    # Health check settings
    health_check_interval = 30  # Seconds between health checks

    # Keep alive settings - match the longest job timeout
    keep_result = FULL_PIPELINE_TIMEOUT  # Keep results for 6 hours
