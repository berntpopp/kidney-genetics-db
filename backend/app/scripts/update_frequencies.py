#!/usr/bin/env python3
"""
Update all annotation sources to quarterly frequency and adjust next_update dates.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.core.database import get_db
from app.models.gene_annotation import AnnotationSource


def update_frequencies():
    """Update all sources to quarterly frequency."""
    db = next(get_db())

    try:
        # Get all annotation sources
        sources = db.query(AnnotationSource).all()

        for source in sources:
            # Update frequency to quarterly
            source.update_frequency = "quarterly"

            # Update cache TTL in config
            if source.config:
                source.config["cache_ttl_days"] = 90
            else:
                source.config = {"cache_ttl_days": 90}

            # If source has a last_update, set next_update to 90 days from it
            if source.last_update:
                source.next_update = source.last_update + timedelta(days=90)
            else:
                # If no last_update, set next_update to 90 days from now
                source.next_update = datetime.now(timezone.utc) + timedelta(days=90)

            print(f"Updated {source.source_name}: frequency=quarterly, next_update={source.next_update}")

        # Commit changes
        db.commit()
        print(f"\n✅ Successfully updated {len(sources)} sources to quarterly frequency")

    except Exception as e:
        print(f"❌ Error updating frequencies: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_frequencies()
