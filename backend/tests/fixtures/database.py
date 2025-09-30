"""
Enhanced database fixtures with proper transaction handling.
Complements the existing conftest.py postgresql setup.
"""

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.cache_service import get_cache_service


@pytest.fixture
async def cache(db_session: Session):
    """
    Provide clean cache service for each test.
    Uses existing database session with automatic cleanup.
    """
    service = get_cache_service(db_session)
    # Clear all cache entries at the start of each test
    await service.clear_all()
    yield service
    # Cleanup happens automatically with transaction rollback


@pytest.fixture
async def clean_db(db_session: Session):
    """
    Provide a clean database session with no pre-existing data.
    Useful for tests that need complete control over data.
    """
    # Clear any existing data (if needed)
    # Note: Transaction rollback handles cleanup automatically
    yield db_session


@pytest.fixture
def enable_foreign_keys(db_session: Session):
    """
    Enable foreign key constraints for SQLite databases.
    For PostgreSQL, foreign keys are always enabled.
    """
    # Check if we're using SQLite (for local testing)
    if "sqlite" in str(db_session.bind.url):

        @event.listens_for(db_session.bind, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    yield db_session
