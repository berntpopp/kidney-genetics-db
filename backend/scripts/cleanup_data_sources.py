#!/usr/bin/env python3
"""
Script to clean up obsolete data source entries and ensure consistency
between data_source_progress table and DATA_SOURCE_CONFIG.

This addresses the issue where:
- ClinVar shows up as a source but is now an annotation
- Literature was changed to a hybrid source
- DiagnosticPanels wasn't appearing in progress tracking
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datasource_config import DATA_SOURCE_CONFIG
from app.core.logging import get_logger
from app.models.progress import DataSourceProgress, SourceStatus

logger = get_logger(__name__)


def cleanup_data_sources():
    """Remove obsolete entries and add missing ones to data_source_progress"""

    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db:
        # Get current entries
        current_entries = db.query(DataSourceProgress).all()
        current_names = {entry.source_name for entry in current_entries}

        logger.sync_info("Current entries in data_source_progress", entries=list(current_names))

        # Get valid source names from config
        valid_sources = set(DATA_SOURCE_CONFIG.keys())
        # Add internal processes that should be tracked
        internal_processes = {"Evidence_Aggregation", "HGNC_Normalization", "annotation_pipeline"}
        all_valid_names = valid_sources | internal_processes

        logger.sync_info("Valid sources from config", sources=list(valid_sources))

        # Find obsolete entries (in DB but not in config)
        obsolete_names = current_names - all_valid_names
        if obsolete_names:
            logger.sync_warning("Found obsolete entries to remove", obsolete=list(obsolete_names))

            # Remove obsolete entries
            for name in obsolete_names:
                entry = db.query(DataSourceProgress).filter_by(source_name=name).first()
                if entry:
                    logger.sync_info(f"Removing obsolete entry: {name}")
                    db.delete(entry)

        # Find missing entries (in config but not in DB)
        missing_names = valid_sources - current_names
        if missing_names:
            logger.sync_info("Found missing entries to add", missing=list(missing_names))

            # Add missing entries
            for name in missing_names:
                config = DATA_SOURCE_CONFIG[name]
                logger.sync_info(f"Adding missing entry: {name}")

                new_entry = DataSourceProgress(
                    source_name=name,
                    status=SourceStatus.idle,
                    current_page=0,
                    total_pages=None,
                    current_item=0,
                    total_items=None,
                    items_processed=0,
                    items_added=0,
                    items_updated=0,
                    items_failed=0,
                    progress_percentage=0.0,
                    current_operation=f"{config['display_name']} - Ready",
                    progress_metadata={
                        "description": config["description"],
                        "auto_update": config.get("auto_update", False),
                        "hybrid_source": config.get("hybrid_source", False),
                    }
                )
                db.add(new_entry)

        # Commit all changes
        db.commit()

        # Verify final state
        final_entries = db.query(DataSourceProgress).all()
        final_names = {entry.source_name for entry in final_entries}

        logger.sync_info(
            "Cleanup complete",
            removed=list(obsolete_names),
            added=list(missing_names),
            final_entries=list(final_names)
        )

        print("\n=== Data Source Cleanup Complete ===")
        print(f"Removed: {', '.join(obsolete_names) if obsolete_names else 'None'}")
        print(f"Added: {', '.join(missing_names) if missing_names else 'None'}")
        print(f"Final entries: {len(final_entries)}")
        print("\nCurrent data sources in progress table:")
        for entry in sorted(final_entries, key=lambda x: x.source_name):
            category = "data_source" if entry.source_name in valid_sources else "internal_process"
            print(f"  - {entry.source_name} ({category}): {entry.status.value}")


if __name__ == "__main__":
    cleanup_data_sources()
