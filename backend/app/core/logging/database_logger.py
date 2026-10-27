"""
Database logger for persistent log storage.

Handles async database writes for log entries with structured data
storage in PostgreSQL using JSONB for rich context information.
"""

import asyncio
import json
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Import SessionLocal lazily to avoid circular import
# from app.core.database import SessionLocal

# Global database logger instance
_db_logger: Optional["DatabaseLogger"] = None


_LOG_WRITER = ThreadPoolExecutor(max_workers=1, thread_name_prefix="db-log")


class DatabaseLogger:
    """
    Async database logger for structured log persistence.

    Stores log entries in PostgreSQL with rich context data,
    request correlation, and performance metrics.
    """

    def __init__(self) -> None:
        self.enabled = True

    async def log(
        self,
        level: str,
        message: str,
        source: str,
        request: Request | None = None,
        request_id: str | None = None,
        extra_data: dict[str, Any] | None = None,
        error: Exception | None = None,
        processing_time_ms: int | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Log an entry to the database.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            source: Source module/component
            request: FastAPI request object (optional)
            request_id: Request correlation ID
            extra_data: Additional structured data
            error: Exception object for error logs
            processing_time_ms: Request processing time
            status_code: HTTP status code
        """
        if not self.enabled:
            return

        try:
            # Use async task to avoid blocking
            asyncio.create_task(
                self._write_log_entry(
                    level,
                    message,
                    source,
                    request,
                    request_id,
                    extra_data,
                    error,
                    processing_time_ms,
                    status_code,
                )
            )
        except Exception as e:
            # Fallback to console logging if database write fails
            import logging

            fallback_logger = logging.getLogger("database_logger")
            fallback_logger.error(f"Failed to write log to database: {e}")

    async def _write_log_entry(
        self,
        level: str,
        message: str,
        source: str,
        request: Request | None,
        request_id: str | None,
        extra_data: dict[str, Any] | None,
        error: Exception | None,
        processing_time_ms: int | None,
        status_code: int | None,
    ) -> None:
        """Internal method to write log entry to database."""
        try:
            # Import SessionLocal here to avoid circular import
            from app.core.database import SessionLocal

            # Extract request data if available
            endpoint = None
            method = None
            ip_address = None
            user_agent = None
            user_id = None

            if request:
                endpoint = request.url.path
                # WebSocket connections don't have a method attribute
                if hasattr(request, "method"):
                    method = request.method

                # Extract IP address
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    ip_address = forwarded_for.split(",")[0].strip()
                elif hasattr(request, "client") and request.client:
                    ip_address = request.client.host

                user_agent = request.headers.get("User-Agent")

                # Extract user if available
                if hasattr(request.state, "current_user") and request.state.current_user:
                    user_id = getattr(request.state.current_user, "id", None)

            # UnifiedLogger passes no Request, only the bound request context and log kwargs.
            # Other loggers reuse status_code/path for upstream APIs and files, so only the
            # request middleware may fill status and duration.
            extra = extra_data or {}
            endpoint = endpoint or extra.get("endpoint")
            method = method or extra.get("method")
            if source == "request_middleware":
                if status_code is None and isinstance(extra.get("status_code"), int):
                    status_code = extra["status_code"]
                if processing_time_ms is None and isinstance(
                    extra.get("processing_time_ms"), int | float
                ):
                    processing_time_ms = extra["processing_time_ms"]

            # Prepare error data
            error_type: str | None = None
            error_traceback: str | None = None
            if error:
                error_type = type(error).__name__
                tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
                error_traceback = "".join(tb_lines)

            # Prepare extra data as JSONB - serialize to JSON string for PostgreSQL
            jsonb_data = json.dumps(extra_data or {})

            # Insert log entry
            insert_query = text("""
                INSERT INTO system_logs (
                    timestamp, level, message, logger, request_id, path, method,
                    status_code, duration_ms, user_id, ip_address, user_agent,
                    context, error_type, error_message, stack_trace
                ) VALUES (
                    :timestamp, :level, :message, :logger, :request_id, :path, :method,
                    :status_code, :duration_ms, :user_id, :ip_address, :user_agent,
                    :context, :error_type, :error_message, :stack_trace
                )
            """)

            params = {
                "timestamp": datetime.now(timezone.utc),
                "level": level,
                "message": message,
                "logger": source,
                "request_id": request_id,
                "path": endpoint,
                "method": method,
                "status_code": status_code,
                "duration_ms": processing_time_ms,
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "context": jsonb_data,
                "error_type": error_type,
                "error_message": str(error) if error else None,
                "stack_trace": error_traceback,
            }

            def insert() -> None:
                with SessionLocal() as db:
                    db.execute(insert_query, params)
                    db.commit()

            # A sync INSERT per log line on the event loop took 2-4 s each under load (#363);
            # one dedicated thread keeps it off the loop and holds at most one connection
            await asyncio.get_running_loop().run_in_executor(_LOG_WRITER, insert)

        except SQLAlchemyError as e:
            # Database-specific error handling
            import logging

            fallback_logger = logging.getLogger("database_logger")
            fallback_logger.error(f"SQLAlchemy error writing log: {e}")

        except Exception as e:
            # General error handling
            import logging

            fallback_logger = logging.getLogger("database_logger")
            fallback_logger.error(f"Unexpected error writing log: {e}")

    # Convenience methods for different log levels
    async def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        await self.log("DEBUG", message, **kwargs)

    async def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        await self.log("INFO", message, **kwargs)

    async def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        await self.log("WARNING", message, **kwargs)

    async def error(self, message: str, error: Exception | None = None, **kwargs: Any) -> None:
        """Log an error message."""
        await self.log("ERROR", message, error=error, **kwargs)

    async def critical(self, message: str, error: Exception | None = None, **kwargs: Any) -> None:
        """Log a critical message."""
        await self.log("CRITICAL", message, error=error, **kwargs)


def get_database_logger() -> DatabaseLogger:
    """Get the global database logger instance."""
    global _db_logger
    if _db_logger is None:
        _db_logger = DatabaseLogger()
    return _db_logger


def initialize_database_logger() -> DatabaseLogger:
    """Initialize the global database logger."""
    global _db_logger
    _db_logger = DatabaseLogger()
    return _db_logger


# Global instance
db_logger = get_database_logger()
