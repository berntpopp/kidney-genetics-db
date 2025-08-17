"""
Unified progress tracking implementation for all data sources
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


def update_panelapp_with_progress(
    db: Session, tracker: ProgressTracker | None = None
) -> dict[str, Any]:
    """Update PanelApp data with progress tracking"""
    # REFACTORED: Use sync wrapper for unified source
    from app.pipeline.sources.sync_wrappers import update_panelapp_sync

    return update_panelapp_sync(db, tracker)


def update_clingen_with_progress(
    db: Session, tracker: ProgressTracker | None = None
) -> dict[str, Any]:
    """Update ClinGen data with progress tracking"""
    # REFACTORED: Use sync wrapper for unified source
    from app.pipeline.sources.sync_wrappers import update_clingen_sync

    return update_clingen_sync(db, tracker)


async def update_gencc_with_progress(
    db: Session, tracker: ProgressTracker | None = None
) -> dict[str, Any]:
    """Update GenCC data with progress tracking - async version"""
    # REFACTORED: Use sync wrapper for unified source
    from app.pipeline.sources.sync_wrappers import update_gencc_sync

    return update_gencc_sync(db, tracker)


def update_pubtator_with_progress(
    db: Session, tracker: ProgressTracker | None = None
) -> dict[str, Any]:
    """Update PubTator data with progress tracking"""
    # REFACTORED: Use sync wrapper for unified source
    from app.pipeline.sources.sync_wrappers import update_pubtator_sync

    return update_pubtator_sync(db, tracker)


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
