"""
ARQ client for enqueueing background pipeline jobs.

This module provides functions to enqueue pipeline tasks to the ARQ worker,
allowing long-running pipelines to run independently of the web server.
"""

import asyncio
from typing import Any

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from arq.jobs import Job

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global pool instance (lazy initialized)
_arq_pool: ArqRedis | None = None
_arq_pool_lock = asyncio.Lock()


async def get_arq_pool() -> ArqRedis:
    """
    Get or create the ARQ Redis connection pool.

    Thread-safe: uses asyncio.Lock to prevent duplicate pool creation.
    """
    global _arq_pool
    if _arq_pool is None:
        async with _arq_pool_lock:
            if _arq_pool is None:
                logger.sync_info("Creating ARQ Redis connection pool", redis_url=settings.REDIS_URL)
                _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    return _arq_pool


async def close_arq_pool() -> None:
    """Close the ARQ connection pool."""
    global _arq_pool
    if _arq_pool is not None:
        await _arq_pool.close()
        _arq_pool = None
        logger.sync_info("ARQ Redis connection pool closed")


async def enqueue_pipeline_job(
    source_name: str,
    mode: str = "smart",
    resume: bool = False,
) -> str:
    """
    Enqueue a pipeline job to run in the ARQ worker.

    Args:
        source_name: Name of the data source (e.g., "PubTator", "PanelApp")
        mode: Update mode - "smart" (incremental) or "full" (complete refresh)
        resume: Whether to resume from previous checkpoint

    Returns:
        Job ID that can be used to track the job status
    """
    pool = await get_arq_pool()

    job = await pool.enqueue_job(
        "run_pipeline_task",
        source_name=source_name,
        mode=mode,
        resume=resume,
        _queue_name=settings.ARQ_QUEUE_NAME,
    )

    if job is None:
        raise RuntimeError(f"Failed to enqueue job for {source_name}")

    job_id: str = str(job.job_id)

    logger.sync_info(
        "Enqueued pipeline job",
        source_name=source_name,
        mode=mode,
        resume=resume,
        job_id=job_id,
    )

    return job_id


async def enqueue_annotation_pipeline_job(
    sources: list[str] | None = None,
    mode: str = "smart",
    resume: bool = False,
) -> str:
    """
    Enqueue the full annotation pipeline job.

    Args:
        sources: Optional list of specific sources to run
        mode: Update mode - "smart" (incremental) or "full" (complete refresh)
        resume: Whether to resume from previous checkpoint

    Returns:
        Job ID
    """
    pool = await get_arq_pool()

    job = await pool.enqueue_job(
        "run_annotation_pipeline_task",
        sources=sources,
        mode=mode,
        resume=resume,
        _queue_name=settings.ARQ_QUEUE_NAME,
    )

    if job is None:
        raise RuntimeError("Failed to enqueue annotation pipeline job")

    job_id: str = str(job.job_id)

    logger.sync_info(
        "Enqueued annotation pipeline job",
        sources=sources,
        mode=mode,
        resume=resume,
        job_id=job_id,
    )

    return job_id


async def get_job_status(job_id: str) -> dict[str, Any]:
    """
    Get the status of a queued or running job.

    Args:
        job_id: The job ID returned from enqueue functions

    Returns:
        Dictionary with job status information
    """
    pool = await get_arq_pool()
    job = Job(job_id, pool)

    status = await job.status()
    info = await job.info()

    result: dict[str, Any] = {
        "job_id": job_id,
        "status": status.value if status else "unknown",
    }

    if info:
        result.update(
            {
                "function": info.function,
                "args": info.args,
                "kwargs": info.kwargs,
                "enqueue_time": info.enqueue_time.isoformat() if info.enqueue_time else None,
                "start_time": info.start_time.isoformat() if info.start_time else None,
                "finish_time": info.finish_time.isoformat() if info.finish_time else None,
                "success": info.success,
                "result": info.result if info.success else None,
            }
        )

    return result


async def cancel_job(job_id: str) -> bool:
    """
    Cancel a queued job (cannot cancel already running jobs).

    Args:
        job_id: The job ID to cancel

    Returns:
        True if job was cancelled, False otherwise
    """
    pool = await get_arq_pool()
    job = Job(job_id, pool)

    # Note: ARQ doesn't support cancelling running jobs
    # This only removes jobs from the queue
    status = await job.status()
    if status and status.value == "queued":
        await job.abort()
        logger.sync_info("Job cancelled", job_id=job_id)
        return True

    logger.sync_warning(
        "Cannot cancel job - not in queue",
        job_id=job_id,
        status=status.value if status else "unknown",
    )
    return False


async def is_job_running(source_name: str) -> bool:
    """
    Check if a job for the given source is currently running or queued.

    Args:
        source_name: Name of the data source

    Returns:
        True if a job is running or queued for this source
    """
    pool = await get_arq_pool()

    # Get all jobs in the queue
    queued = await pool.queued_jobs(queue_name=settings.ARQ_QUEUE_NAME)

    for job_info in queued:
        kwargs = job_info.kwargs or {}
        if kwargs.get("source_name") == source_name:
            return True

    return False
