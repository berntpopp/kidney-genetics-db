"""
Test configuration and fixtures.

Using pytest-postgresql for proper database isolation in tests.
"""

import asyncio
from typing import Any

import pytest
from pytest_postgresql import factories
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base


def load_test_schema(**kwargs):
    """
    Load the test database schema.
    This function is called once to create the template database.
    """
    connection_string = (
        f"postgresql://{kwargs['user']}@{kwargs['host']}:{kwargs['port']}/{kwargs['dbname']}"
    )
    engine = create_engine(connection_string, poolclass=NullPool)

    # Create cache_entries table for cache testing
    with engine.connect() as conn:
        conn.execute(text("COMMIT"))
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                id SERIAL PRIMARY KEY,
                cache_key VARCHAR(255) NOT NULL UNIQUE,
                namespace VARCHAR(100) NOT NULL,
                value JSONB,
                data JSONB,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_cache_namespace ON cache_entries(namespace)
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at)
        """)
        )
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_cache_key_namespace ON cache_entries(cache_key, namespace)
        """)
        )
        conn.commit()

    # Create all other tables from models
    Base.metadata.create_all(engine)
    engine.dispose()


# Create PostgreSQL process fixture with schema loading
postgresql_proc = factories.postgresql_proc(
    port=None,  # Use random available port
    load=[load_test_schema],  # Load schema once for all tests
)

# Create PostgreSQL client fixture
postgresql = factories.postgresql(
    "postgresql_proc",
    dbname="test_kidney_genetics",
)


@pytest.fixture(scope="function")
def db_session(postgresql):
    """
    Create a test database session using pytest-postgresql.
    Each test gets its own database transaction that's rolled back after the test.
    """
    # Create connection string
    connection_string = (
        f"postgresql://{postgresql.info.user}@"
        f"{postgresql.info.host}:{postgresql.info.port}/"
        f"{postgresql.info.dbname}"
    )

    # Create engine and session
    engine = create_engine(connection_string, poolclass=NullPool)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()

    # Begin a transaction that we'll roll back at the end
    trans = session.begin()

    yield session

    # Rollback the transaction and close session
    trans.rollback()
    session.close()
    engine.dispose()


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
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
