"""
Async PubTator implementation that doesn't block the API
"""

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


async def update_pubtator_async(db: Session, tracker: ProgressTracker) -> dict[str, Any]:
    """
    Async version of PubTator update that won't block the API
    Delegates to the synchronous version but runs it in a thread pool
    """
    from concurrent.futures import ThreadPoolExecutor

    from app.pipeline.sources.pubtator import update_pubtator_data

    # Run the actual PubTator update in a thread pool
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = await loop.run_in_executor(
            executor,
            update_pubtator_data,
            db,
            tracker
        )

    return result
