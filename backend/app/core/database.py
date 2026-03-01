"""
Database configuration and session management
OPTIMIZED: Includes robust connection management and pool monitoring
"""

import asyncio
import atexit
import threading
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DisconnectionError
from sqlalchemy.exc import TimeoutError as SQLTimeoutError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import Pool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Singleton thread pool for database operations
# CRITICAL: Prevents resource exhaustion by reusing single pool
_thread_pool_executor: ThreadPoolExecutor | None = None
_thread_pool_lock = threading.Lock()


def get_thread_pool_executor() -> ThreadPoolExecutor:
    """
    Get or create singleton thread pool for database operations.

    IMPORTANT: Prevents resource exhaustion by reusing single pool.
    Following best practices from issue #16 implementation.
    """
    global _thread_pool_executor

    if _thread_pool_executor is None:
        with _thread_pool_lock:
            if _thread_pool_executor is None:
                logger.sync_info("Creating singleton thread pool executor")
                _thread_pool_executor = ThreadPoolExecutor(
                    max_workers=10,
                    thread_name_prefix="db-executor-",
                )

    return _thread_pool_executor


# Register cleanup on shutdown
def _cleanup_executor() -> None:
    if _thread_pool_executor:
        _thread_pool_executor.shutdown(wait=True)


atexit.register(_cleanup_executor)

# Create database engine with robust connection management
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    # Connection pooling with robustness settings
    pool_size=10,
    max_overflow=15,
    pool_timeout=30,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Test connections before use
    pool_use_lifo=True,  # Use LIFO for better connection reuse
    pool_reset_on_return="rollback",  # Always rollback on return
    # Connection-level timeouts and settings
    connect_args={
        "options": "-c idle_in_transaction_session_timeout=30000",  # 30 second timeout
        "connect_timeout": 10,
    }
    if "postgresql" in settings.DATABASE_URL
    else {},
    # Enable pool logging for debugging
    echo_pool=settings.DATABASE_ECHO,
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
        # Commit if we get here without exception
        db.commit()
    except (DisconnectionError, SQLTimeoutError, asyncio.TimeoutError) as e:
        # Critical errors that may corrupt session state
        if db:
            try:
                db.invalidate()  # Don't return connection to pool
            except Exception:
                pass
        logger.sync_error("Database connection error - session invalidated", error=e)
        raise
    except Exception as e:
        if db:
            try:
                db.rollback()
            except Exception as rollback_err:
                # If rollback fails, invalidate the session
                try:
                    db.invalidate()
                except Exception:
                    pass
                logger.sync_warning(
                    "Rollback failed, session invalidated", rollback_error=str(rollback_err)
                )
        logger.sync_error(
            "Database error in context",
            error=e,
            error_type=type(e).__name__,
            has_active_transaction=db.in_transaction() if db else None,
        )
        raise
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.sync_error("Error closing database session", error=e)


@contextmanager
def transactional_context(timeout_seconds: int = 300) -> Generator[Session, None, None]:
    """
    Context manager for transactional database operations with timeout.
    ROBUST: Includes timeout protection and proper error handling.
    """
    db = None
    start_time = (
        asyncio.get_event_loop().time()
        if hasattr(asyncio, "_get_running_loop") and asyncio._get_running_loop()
        else 0
    )

    try:
        db = SessionLocal()

        # Set a statement timeout for long-running operations
        if "postgresql" in settings.DATABASE_URL:
            db.execute(text(f"SET statement_timeout = {timeout_seconds * 1000}"))

        yield db

        # Check if we've exceeded our timeout
        if start_time and (asyncio.get_event_loop().time() - start_time) > timeout_seconds:
            raise asyncio.TimeoutError(f"Transaction exceeded {timeout_seconds} seconds")

        db.commit()

    except (DisconnectionError, SQLTimeoutError, asyncio.TimeoutError) as e:
        # Critical errors - invalidate session
        if db:
            try:
                db.invalidate()
            except Exception:
                pass
        logger.sync_error(
            "Transaction failed with critical error", error=e, timeout_seconds=timeout_seconds
        )
        raise
    except Exception as e:
        if db:
            try:
                db.rollback()
            except Exception:
                try:
                    db.invalidate()
                except Exception:
                    pass
        logger.sync_error("Transaction failed", error=e)
        raise
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.sync_error("Error closing transactional session", error=e)


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
def increment_connect(dbapi_conn: Any, connection_record: Any) -> None:
    """Track new connections created"""
    connection_stats["connections_created"] += 1
    logger.sync_debug(
        "New database connection created", total_connections=connection_stats["connections_created"]
    )


@event.listens_for(Pool, "close")
def increment_close(dbapi_conn: Any, connection_record: Any) -> None:
    """Track connections closed"""
    connection_stats["connections_closed"] += 1


@event.listens_for(Pool, "checkout")
def increment_checkout(dbapi_conn: Any, connection_record: Any, connection_proxy: Any) -> None:
    """Track connections checked out from pool"""
    connection_stats["connections_checked_out"] += 1


@event.listens_for(Pool, "checkin")
def increment_checkin(dbapi_conn: Any, connection_record: Any) -> None:
    """Track connections returned to pool"""
    connection_stats["connections_checked_in"] += 1


@event.listens_for(Pool, "invalidate")
def increment_invalidate(
    dbapi_conn: Any, connection_record: Any, exception: BaseException | None
) -> None:
    """Track invalidated connections"""
    connection_stats["connections_invalidated"] += 1
    if exception:
        logger.sync_warning("Connection invalidated", exception=str(exception))


def get_pool_status() -> dict:
    """
    Get current database connection pool status.
    Useful for monitoring and debugging connection leaks.
    """
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow(),
        "stats": connection_stats.copy(),
        "pool_timeout": getattr(pool, "_timeout", None),
        "pool_recycle": getattr(pool, "_recycle", None),
    }


def check_database_health() -> dict[str, Any]:
    """
    Comprehensive database health check.
    ROBUST: Tests connectivity, pool status, and basic operations.
    """
    try:
        with get_db_context() as db:
            # Test basic connectivity
            result = db.execute(text("SELECT 1 as health_check"))
            health_result = result.scalar()

            if health_result != 1:
                raise ValueError("Unexpected health check result")

            # Get pool status
            pool_status = get_pool_status()

            return {
                "status": "healthy",
                "database_responsive": True,
                "pool_status": pool_status,
                "test_query_result": health_result,
            }

    except (DisconnectionError, SQLTimeoutError) as e:
        logger.sync_error("Database health check failed - connection issue", error=e)
        return {
            "status": "unhealthy",
            "database_responsive": False,
            "error": "Connection/timeout error",
            "error_details": str(e),
            "pool_status": get_pool_status(),
        }
    except Exception as e:
        logger.sync_error("Database health check failed", error=e)
        return {
            "status": "unhealthy",
            "database_responsive": False,
            "error": "General database error",
            "error_details": str(e),
            "pool_status": get_pool_status(),
        }


def cleanup_idle_sessions() -> dict[str, Any]:
    """
    Clean up idle database sessions that might be blocking.
    ROBUST: Helps prevent session accumulation and hanging transactions.
    """
    try:
        with get_db_context() as db:
            if "postgresql" in settings.DATABASE_URL:
                # Find idle transactions older than 5 minutes
                result = db.execute(
                    text("""
                    SELECT pid, state, query_start, state_change,
                           EXTRACT(EPOCH FROM (NOW() - query_start)) as seconds_old,
                           query
                    FROM pg_stat_activity
                    WHERE state = 'idle in transaction'
                    AND EXTRACT(EPOCH FROM (NOW() - state_change)) > 300
                    AND pid != pg_backend_pid()
                """)
                )

                idle_sessions = result.fetchall()
                terminated_count = 0

                # Terminate sessions that have been idle too long
                for session in idle_sessions:
                    try:
                        db.execute(text("SELECT pg_terminate_backend(:pid)"), {"pid": session.pid})
                        terminated_count += 1
                        logger.sync_warning(
                            "Terminated idle database session",
                            pid=session.pid,
                            seconds_old=session.seconds_old,
                        )
                    except Exception as e:
                        logger.sync_error("Failed to terminate session", pid=session.pid, error=e)

                return {
                    "cleanup_performed": True,
                    "idle_sessions_found": len(idle_sessions),
                    "sessions_terminated": terminated_count,
                }
            else:
                return {"cleanup_performed": False, "reason": "Non-PostgreSQL database"}

    except Exception as e:
        logger.sync_error("Failed to cleanup idle sessions", error=e)
        return {
            "cleanup_performed": False,
            "error": str(e),
        }
