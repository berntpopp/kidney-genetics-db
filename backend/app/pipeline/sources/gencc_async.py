"""
GenCC data source integration - Async implementation

Quick async wrapper for GenCC data processing.
"""

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.progress_tracker import ProgressTracker
from app.pipeline.sources.gencc import update_gencc_data

logger = logging.getLogger(__name__)


async def update_gencc_async(db: Session, tracker: ProgressTracker) -> dict[str, Any]:
    """Update database with GenCC gene-disease data asynchronously

    Args:
        db: Database session
        tracker: Progress tracker

    Returns:
        Statistics about the update
    """
    logger.info("🚀 Starting async GenCC data update...")

    tracker.start("Starting GenCC async update")

    try:
        # Run synchronous GenCC in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await loop.run_in_executor(
                executor,
                update_gencc_data,
                db
            )

        tracker.complete(f"GenCC async update completed: {result.get('genes_processed', 0)} genes processed")
        logger.info(f"✅ GenCC async update completed: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ GenCC async update failed: {e}")
        tracker.error(str(e))
        raise
