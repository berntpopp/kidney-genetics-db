"""
Database configuration and session management
OPTIMIZED: Includes robust connection management and pool monitoring
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import Pool

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with guaranteed cleanup.
    ROBUST: Ensures proper rollback and connection closure even on exceptions.
    """
    db = None
    try:
        db = SessionLocal()
        yield db
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Database error in context: {e}")
        raise
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")


# Connection pool monitoring for debugging and optimization
connection_stats = {
    "connections_created": 0,
    "connections_closed": 0,
    "connections_overflow": 0,
    "connections_invalidated": 0,
    "connections_checked_out": 0,
    "connections_checked_in": 0,
}


@event.listens_for(Pool, "connect")
def increment_connect(dbapi_conn, connection_record):
    """Track new connections created"""
    connection_stats["connections_created"] += 1
    logger.debug(
        f"New database connection created. Total: {connection_stats['connections_created']}"
    )


@event.listens_for(Pool, "close")
def increment_close(dbapi_conn, connection_record):
    """Track connections closed"""
    connection_stats["connections_closed"] += 1


@event.listens_for(Pool, "checkout")
def increment_checkout(dbapi_conn, connection_record, connection_proxy):
    """Track connections checked out from pool"""
    connection_stats["connections_checked_out"] += 1


@event.listens_for(Pool, "checkin")
def increment_checkin(dbapi_conn, connection_record):
    """Track connections returned to pool"""
    connection_stats["connections_checked_in"] += 1


@event.listens_for(Pool, "invalidate")
def increment_invalidate(dbapi_conn, connection_record, exception):
    """Track invalidated connections"""
    connection_stats["connections_invalidated"] += 1
    if exception:
        logger.warning(f"Connection invalidated due to: {exception}")


def get_pool_status() -> dict:
    """
    Get current database connection pool status.
    Useful for monitoring and debugging connection leaks.
    """
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedout(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow(),
        "stats": connection_stats.copy(),
    }
