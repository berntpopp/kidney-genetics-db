"""
Test configuration and fixtures.

Uses the existing PostgreSQL database from Docker/hybrid development setup.
Each test uses a transaction that is rolled back after the test for isolation.
"""

import asyncio
import os
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


def get_test_database_url() -> str:
    """
    Get the database URL for testing.
    Uses the existing PostgreSQL instance from Docker/hybrid setup.
    Falls back to the default development database URL.
    """
    # Allow override via environment variable for CI/CD
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url:
        return test_url

    # Use the main DATABASE_URL if available (hybrid/docker mode)
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics",
    )
    return db_url


# Create engine once for all tests - uses existing PostgreSQL from Docker
_test_engine = None
_TestingSessionLocal = None


def get_test_engine():
    """Get or create the test database engine (singleton)."""
    global _test_engine, _TestingSessionLocal

    if _test_engine is None:
        database_url = get_test_database_url()
        _test_engine = create_engine(
            database_url,
            poolclass=NullPool,  # Don't pool connections for tests
            echo=False,
        )
        _TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

        # Verify connection works
        try:
            with _test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            pytest.skip(
                f"Database not available at {database_url}. "
                f"Start the database with 'make hybrid-up' or 'make dev-up'. Error: {e}"
            )

    return _test_engine, _TestingSessionLocal


@pytest.fixture(scope="session")
def test_engine():
    """
    Session-scoped fixture for the test database engine.
    Uses the existing PostgreSQL from Docker/hybrid setup.
    """
    engine, _ = get_test_engine()
    yield engine


@pytest.fixture(scope="function")
def db_session(test_engine):
    """
    Create a test database session with transaction rollback.
    Each test gets its own database transaction that's rolled back after the test.
    This provides isolation without requiring pg_config or spawning new PostgreSQL instances.
    """
    _, TestingSessionLocal = get_test_engine()

    # Create a new connection for this test
    connection = test_engine.connect()

    # Begin a transaction that we'll roll back at the end
    transaction = connection.begin()

    # Create a session bound to this connection
    session = TestingSessionLocal(bind=connection)

    # Begin a nested transaction (savepoint) for the test
    nested = connection.begin_nested()

    yield session

    # Rollback the nested transaction (test's changes)
    if nested.is_active:
        nested.rollback()

    # Rollback the outer transaction
    if transaction.is_active:
        transaction.rollback()

    # Close session and connection
    session.close()
    connection.close()


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session with proper cleanup."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    # Cancel all pending tasks to prevent hanging
    # See: https://github.com/pytest-dev/pytest-asyncio/issues/81
    try:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception:
        pass  # Ignore errors during cleanup
    loop.close()


@pytest.fixture
def mock_cache_entries(db_session):
    """
    Helper fixture to quickly populate cache entries for testing.
    """

    def _create_entries(entries: list[dict[str, Any]]):
        for entry in entries:
            db_session.execute(
                text("""
                    INSERT INTO cache_entries
                    (cache_key, namespace, value, expires_at)
                    VALUES (:key, :namespace, :value::jsonb, :expires_at)
                """),
                {
                    "key": entry.get("key"),
                    "namespace": entry.get("namespace", "test"),
                    "value": entry.get("value", "{}"),
                    "expires_at": entry.get("expires_at"),
                },
            )
        db_session.commit()

    return _create_entries


# Note: Cache service instances are isolated per test through database transactions

# Import fixtures from fixture modules to make them available globally
# These imports make fixtures available to all test files
from tests.fixtures.auth import *  # noqa: F401, F403, E402
from tests.fixtures.client import *  # noqa: F401, F403, E402
