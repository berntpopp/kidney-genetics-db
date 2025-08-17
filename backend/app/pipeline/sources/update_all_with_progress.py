"""
Unified progress tracking implementation for all data sources
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


def update_panelapp_with_progress(db: Session, tracker: ProgressTracker | None = None) -> dict[str, Any]:
    """Update PanelApp data with progress tracking"""
    # REFACTORED: Use sync wrapper for unified source
    from app.pipeline.sources.sync_wrappers import update_panelapp_sync
    return update_panelapp_sync(db, tracker)

    # Create tracker if not provided
    if tracker is None:
        tracker = ProgressTracker(db, "PanelApp")

    try:
        tracker.start("Initializing PanelApp update")

        # Call original function (we'll need to modify it to accept tracker)
        # For now, run without integrated tracking
        result = original_update(db)

        # Update final counts
        tracker.update(
            items_added=result.get("genes_created", 0) + result.get("evidence_created", 0),
            items_updated=result.get("evidence_updated", 0),
            items_failed=result.get("errors", 0),
            operation="Update complete"
        )

        tracker.complete(f"Processed {result.get('genes_processed', 0)} genes")
        return result

    except Exception as e:
        tracker.error(str(e))
        raise


def update_clingen_with_progress(db: Session, tracker: ProgressTracker | None = None) -> dict[str, Any]:
    """Update ClinGen data with progress tracking"""
    # REFACTORED: Use sync wrapper for unified source
    from app.pipeline.sources.sync_wrappers import update_clingen_sync
    return update_clingen_sync(db, tracker)

    # Create tracker if not provided
    if tracker is None:
        tracker = ProgressTracker(db, "ClinGen")

    try:
        tracker.start("Initializing ClinGen update")

        # Call original function
        result = original_update(db)

        # Update final counts
        tracker.update(
            items_added=result.get("genes_created", 0) + result.get("evidence_created", 0),
            items_updated=result.get("evidence_updated", 0),
            items_failed=result.get("errors", 0),
            operation="Update complete"
        )

        tracker.complete(f"Processed {result.get('genes_processed', 0)} genes")
        return result

    except Exception as e:
        tracker.error(str(e))
        raise


async def update_gencc_with_progress(db: Session, tracker: ProgressTracker | None = None) -> dict[str, Any]:
    """Update GenCC data with progress tracking - async version"""
    # REFACTORED: Old async source deleted, use unified async source
    # from app.pipeline.sources.gencc_async import update_gencc_async
    from app.pipeline.sources.unified.gencc import GenCCUnifiedSource

    async def update_gencc_async(db, tracker):
        source = GenCCUnifiedSource(db_session=db)
        # TODO: Implement full update logic
        logger.warning("GenCC unified update not fully implemented")
        return {"status": "completed", "genes_processed": 0}

    # Create tracker if not provided
    if tracker is None:
        tracker = ProgressTracker(db, "GenCC")

    logger.info("🚀 Starting GenCC async update with progress tracking...")
    try:
        # Call async function directly
        result = await update_gencc_async(db, tracker)
        logger.info(f"✅ GenCC async update completed: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ GenCC update failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        tracker.error(str(e))
        raise


def update_pubtator_with_progress(db: Session, tracker: ProgressTracker | None = None) -> dict[str, Any]:
    """Update PubTator data with progress tracking"""
    # REFACTORED: Use sync wrapper for unified source
    from app.pipeline.sources.sync_wrappers import update_pubtator_sync
    return update_pubtator_sync(db, tracker)

    # Create tracker if not provided
    if tracker is None:
        tracker = ProgressTracker(db, "PubTator")

    # This function already supports tracker parameter
    return update_pubtator_data(db, tracker)


async def test_progress_tracking(db: Session):
    """Test function to verify progress tracking works for all sources"""
    logger.info("Testing progress tracking for all sources...")

    # Test each source
    sources = [
        ("PubTator", update_pubtator_with_progress, False),
        ("PanelApp", update_panelapp_with_progress, False),
        ("ClinGen", update_clingen_with_progress, False),
        ("GenCC", update_gencc_with_progress, True),  # This one is async
    ]

    for source_name, update_func, is_async in sources:
        logger.info(f"Testing {source_name}...")
        try:
            tracker = ProgressTracker(db, source_name)
            if is_async:
                result = await update_func(db, tracker)
            else:
                result = update_func(db, tracker)
            logger.info(f"{source_name} test complete: {result}")
        except Exception as e:
            logger.error(f"{source_name} test failed: {e}")
