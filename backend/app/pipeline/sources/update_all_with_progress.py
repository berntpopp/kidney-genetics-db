"""
Unified progress tracking implementation for all data sources
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


def update_panelapp_with_progress(db: Session, tracker: Optional[ProgressTracker] = None) -> Dict[str, Any]:
    """Update PanelApp data with progress tracking"""
    from app.pipeline.sources.panelapp import update_panelapp_data as original_update
    
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


def update_clingen_with_progress(db: Session, tracker: Optional[ProgressTracker] = None) -> Dict[str, Any]:
    """Update ClinGen data with progress tracking"""
    from app.pipeline.sources.clingen import update_clingen_data as original_update
    
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


def update_gencc_with_progress(db: Session, tracker: Optional[ProgressTracker] = None) -> Dict[str, Any]:
    """Update GenCC data with progress tracking"""
    from app.pipeline.sources.gencc import update_gencc_data as original_update
    
    # Create tracker if not provided
    if tracker is None:
        tracker = ProgressTracker(db, "GenCC")
    
    try:
        tracker.start("Initializing GenCC update")
        
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


def update_pubtator_with_progress(db: Session, tracker: Optional[ProgressTracker] = None) -> Dict[str, Any]:
    """Update PubTator data with progress tracking"""
    from app.pipeline.sources.pubtator import update_pubtator_data
    
    # Create tracker if not provided
    if tracker is None:
        tracker = ProgressTracker(db, "PubTator")
    
    # This function already supports tracker parameter
    return update_pubtator_data(db, tracker)


def test_progress_tracking(db: Session):
    """Test function to verify progress tracking works for all sources"""
    logger.info("Testing progress tracking for all sources...")
    
    # Test each source
    sources = [
        ("PubTator", update_pubtator_with_progress),
        ("PanelApp", update_panelapp_with_progress),
        ("ClinGen", update_clingen_with_progress),
        ("GenCC", update_gencc_with_progress),
    ]
    
    for source_name, update_func in sources:
        logger.info(f"Testing {source_name}...")
        try:
            tracker = ProgressTracker(db, source_name)
            result = update_func(db, tracker)
            logger.info(f"{source_name} test complete: {result}")
        except Exception as e:
            logger.error(f"{source_name} test failed: {e}")