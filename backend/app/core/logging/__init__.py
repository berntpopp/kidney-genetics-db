"""
Unified Logging System for Kidney Genetics Database

This module provides a modern, structured logging system with:
- Dual output: Console (sync) + Database (async)
- Request correlation and context binding
- Drop-in replacement for standard Python logging
- Enterprise-grade observability

Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Operation completed", operation_id="123", duration_ms=456)
"""

from .context import bind_context, clear_context, get_context
from .database_logger import DatabaseLogger

# Import Phase 7 performance features (no database dependencies)
from .performance import (
    PerformanceMonitor,
    api_endpoint,
    batch_operation,
    database_query,
    timed_operation,
)
from .unified_logger import UnifiedLogger, get_logger

# Main interface - drop-in replacement for logging.getLogger()
__all__ = [
    # Core functionality
    "get_logger",
    "UnifiedLogger",
    "bind_context",
    "clear_context",
    "get_context",
    "DatabaseLogger",
    "configure_logging",
    # Performance monitoring
    "timed_operation",
    "database_query",
    "api_endpoint",
    "batch_operation",
    "PerformanceMonitor",
]


def configure_logging(
    log_level: str = "INFO",
    database_enabled: bool = True,
    console_enabled: bool = True,
) -> None:
    """
    Configure the unified logging system.

    This replaces multiple logging.basicConfig() calls throughout the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        database_enabled: Enable database logging
        console_enabled: Enable console logging
    """
    import logging

    # Set up console logging with unified format
    if console_enabled:
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True
        )

    # Configure application loggers
    logging.getLogger("app").setLevel(getattr(logging, log_level.upper()))
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    # Initialize database logger if enabled
    if database_enabled:
        from .database_logger import initialize_database_logger
        initialize_database_logger()
