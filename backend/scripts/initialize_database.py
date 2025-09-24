#!/usr/bin/env python
"""
Database initialization script for automatic setup on reset/clean.
"""

import asyncio
import sys

from app.core.database import get_db_context
from app.core.database_init import initialize_database


def main():
    """Run database initialization."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        with get_db_context() as db:
            result = loop.run_until_complete(initialize_database(db))

            # Print results
            print("✅ Initialization complete:")
            print(f"   Views created: {result.get('views_created')}")
            print(f"   Admin created: {result.get('admin_created')}")
            print(f"   Cache cleared: {result.get('cache_cleared')} entries")
            print(f"   Aggregation: {result.get('aggregation_completed')}")

            # Check for errors
            if result.get('errors'):
                print(f"⚠️  Errors encountered: {result.get('errors')}")
                sys.exit(1)

    except Exception as e:
        print(f"❌ Initialization failed: {str(e)}")
        sys.exit(1)
    finally:
        loop.close()


if __name__ == "__main__":
    main()
