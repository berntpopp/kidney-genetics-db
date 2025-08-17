"""
Sync wrappers for unified async data sources.

This module provides synchronous wrappers for the unified async data sources,
allowing them to be used from sync contexts like CLI commands.
"""

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.progress_tracker import ProgressTracker
from app.pipeline.sources.unified.clingen import ClinGenUnifiedSource
from app.pipeline.sources.unified.gencc import GenCCUnifiedSource
from app.pipeline.sources.unified.hpo import HPOUnifiedSource
from app.pipeline.sources.unified.panelapp import PanelAppUnifiedSource
from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def update_gencc_sync(
    db: Session,
    tracker: ProgressTracker | None = None
) -> dict[str, Any]:
    """
    Synchronous wrapper for GenCC update.
    
    Args:
        db: Database session
        tracker: Optional progress tracker
        
    Returns:
        Update statistics
    """
    async def _update():
        source = GenCCUnifiedSource(db_session=db)

        if tracker:
            tracker.start("Fetching GenCC data")

        # Fetch and process data
        raw_data = await source.fetch_raw_data()
        processed_data = await source.process_data(raw_data)

        # Save to database
        if tracker:
            tracker.update(operation="Saving to database")

        stats = await source.save_to_database(db, processed_data, tracker)

        if tracker:
            tracker.complete(f"GenCC update complete: {stats}")

        return stats

    logger.info("Starting synchronous GenCC update")
    return run_async(_update())


def update_panelapp_sync(
    db: Session,
    tracker: ProgressTracker | None = None
) -> dict[str, Any]:
    """
    Synchronous wrapper for PanelApp update.
    
    Args:
        db: Database session
        tracker: Optional progress tracker
        
    Returns:
        Update statistics
    """
    async def _update():
        source = PanelAppUnifiedSource(db_session=db)

        if tracker:
            tracker.start("Fetching PanelApp data")

        # Fetch and process data
        raw_data = await source.fetch_raw_data()
        processed_data = await source.process_data(raw_data)

        # Save to database
        if tracker:
            tracker.update(operation="Saving to database")

        stats = await source.save_to_database(db, processed_data, tracker)

        if tracker:
            tracker.complete(f"PanelApp update complete: {stats}")

        return stats

    logger.info("Starting synchronous PanelApp update")
    return run_async(_update())


def update_pubtator_sync(
    db: Session,
    tracker: ProgressTracker | None = None
) -> dict[str, Any]:
    """
    Synchronous wrapper for PubTator update.
    
    Args:
        db: Database session
        tracker: Optional progress tracker
        
    Returns:
        Update statistics
    """
    async def _update():
        source = PubTatorUnifiedSource(db_session=db)

        if tracker:
            tracker.start("Fetching PubTator data")

        # Fetch and process data
        raw_data = await source.fetch_raw_data()
        processed_data = await source.process_data(raw_data)

        # Save to database
        if tracker:
            tracker.update(operation="Saving to database")

        stats = await source.save_to_database(db, processed_data, tracker)

        if tracker:
            tracker.complete(f"PubTator update complete: {stats}")

        return stats

    logger.info("Starting synchronous PubTator update")
    return run_async(_update())


def update_hpo_sync(
    db: Session,
    tracker: ProgressTracker | None = None
) -> dict[str, Any]:
    """
    Synchronous wrapper for HPO update.
    
    Args:
        db: Database session
        tracker: Optional progress tracker
        
    Returns:
        Update statistics
    """
    async def _update():
        source = HPOUnifiedSource(db_session=db)

        if tracker:
            tracker.start("Fetching HPO data")

        # Fetch and process data
        raw_data = await source.fetch_raw_data()
        processed_data = await source.process_data(raw_data)

        # Save to database
        if tracker:
            tracker.update(operation="Saving to database")

        stats = await source.save_to_database(db, processed_data, tracker)

        if tracker:
            tracker.complete(f"HPO update complete: {stats}")

        return stats

    logger.info("Starting synchronous HPO update")
    return run_async(_update())


def update_clingen_sync(
    db: Session,
    tracker: ProgressTracker | None = None
) -> dict[str, Any]:
    """
    Synchronous wrapper for ClinGen update.
    
    Args:
        db: Database session
        tracker: Optional progress tracker
        
    Returns:
        Update statistics
    """
    async def _update():
        source = ClinGenUnifiedSource(db_session=db)

        if tracker:
            tracker.start("Fetching ClinGen data")

        # Fetch and process data
        raw_data = await source.fetch_raw_data()
        processed_data = await source.process_data(raw_data)

        # Save to database
        if tracker:
            tracker.update(operation="Saving to database")

        stats = await source.save_to_database(db, processed_data, tracker)

        if tracker:
            tracker.complete(f"ClinGen update complete: {stats}")

        return stats

    logger.info("Starting synchronous ClinGen update")
    return run_async(_update())


# Aliases for backward compatibility
update_gencc_data = update_gencc_sync
update_panelapp_data = update_panelapp_sync
update_pubtator_data = update_pubtator_sync
update_hpo_data = update_hpo_sync
update_clingen_data = update_clingen_sync
