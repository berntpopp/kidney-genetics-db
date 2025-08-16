"""
Async PubTator implementation that doesn't block the API
"""

import asyncio
import logging
import os
from datetime import date, datetime, timezone
from typing import Any, Dict

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.progress_tracker import ProgressTracker
from app.crud.gene import gene_crud
from app.models.gene import GeneEvidence
from app.schemas.gene import GeneCreate

logger = logging.getLogger(__name__)


async def update_pubtator_async(db: Session, tracker: ProgressTracker) -> Dict[str, Any]:
    """
    Async version of PubTator update that won't block the API
    Delegates to the synchronous version but runs it in a thread pool
    """
    from app.pipeline.sources.pubtator import update_pubtator_data
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
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