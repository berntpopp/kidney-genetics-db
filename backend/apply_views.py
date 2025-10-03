#!/usr/bin/env python
"""Apply database views using the ReplaceableObject system."""

from sqlalchemy import create_engine, text

from app.db.replaceable_objects import topological_sort
from app.db.views import ALL_VIEWS

# Database connection
DATABASE_URL = "postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics"
engine = create_engine(DATABASE_URL)

def apply_views():
    """Apply all views in dependency order."""
    # Sort views by dependencies
    sorted_views = topological_sort(ALL_VIEWS)

    print(f"Applying {len(sorted_views)} views in dependency order...")

    for view in sorted_views:
        # Use separate connection for each view to avoid transaction issues
        with engine.begin() as conn:
            try:
                # Use CREATE OR REPLACE to update existing views
                sql = view.replace_statement()
                print(f"  Creating/updating view: {view.name}")
                conn.execute(text(sql))
                print(f"    ✓ {view.name} created successfully")
            except Exception as e:
                print(f"    ✗ {view.name} failed: {e}")
                # Continue with other views
                continue

    print("\nView application complete!")

    # Verify views exist
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))

        views = [row[0] for row in result]
        print(f"\nTotal views in database: {len(views)}")
        for view in views:
            print(f"  - {view}")

if __name__ == "__main__":
    apply_views()
