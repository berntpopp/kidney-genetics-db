"""
Unified Logger - Main logging interface for the Kidney Genetics Database.

Provides a single interface for all logging needs that routes to multiple
destinations (console + database) while maintaining performance and
providing rich context information.
"""

import asyncio
import logging
from typing import Any

from fastapi import BackgroundTasks

from .context import get_context
from .database_logger import get_database_logger


class UnifiedLogger:
    """
    Unified logging interface that routes to multiple destinations.

    This class provides a single interface for all logging needs, automatically
    routing log entries to both console logging (immediate) and database logging
    (async) while including automatic context injection and structured logging.

    Drop-in replacement for standard Python logging with enhanced features.
    """

    def __init__(self, name: str):
        """
        Initialize the unified logger.

        Args:
            name: Logger name (typically __name__ from calling module)
        """
        self.name = name
        self._console_logger = logging.getLogger(name)
        self._database_logger = get_database_logger()
        self._bound_context: dict[str, Any] = {}

    def _get_current_context(self) -> dict[str, Any]:
        """Extract current context from context variables and bound context."""
        context = get_context()

        # Add bound context (takes precedence over context variables)
        context.update(self._bound_context)

        return context

    def _format_console_message(
        self, level: str, message: str, extra_data: dict[str, Any] | None = None
    ) -> str:
        """Format message for console logging with context."""
        context = self._get_current_context()

        # Start with the base message
        parts = [message]

        # Add request_id if available (most important for correlation)
        if request_id := context.get("request_id"):
            parts.append(f"request_id={request_id}")

        # Add user context if available
        if user_id := context.get("user_id"):
            parts.append(f"user_id={user_id}")
        elif username := context.get("username"):
            parts.append(f"username={username}")

        # Add extra data
        if extra_data:
            for key, value in extra_data.items():
                if key not in context:  # Avoid duplicates
                    parts.append(f"{key}={value}")

        return " | ".join(parts)

    async def _log_to_database(
        self,
        level: str,
        message: str,
        error: str | Exception | None = None,
        extra_data: dict[str, Any] | None = None,
        background_tasks: BackgroundTasks | None = None,
    ) -> None:
        """Log to database using the database logger."""
        # Get current context and merge with extra data
        context = self._get_current_context()
        combined_extra = {**context, **(extra_data or {})}

        try:
            await self._database_logger.log(
                level=level,
                message=message,
                source=self.name,
                request_id=context.get("request_id"),
                extra_data=combined_extra,
                error=error,
            )
        except Exception as e:
            # Fallback to console logging if database logging fails
            self._console_logger.error(f"Database logging failed: {e}. Original message: {message}")

    def _log_to_console(
        self, level: str, message: str, extra_data: dict[str, Any] | None = None
    ) -> None:
        """Log to console using standard Python logging."""
        formatted_message = self._format_console_message(level, message, extra_data)
        log_method = getattr(self._console_logger, level.lower())
        log_method(formatted_message)

    def bind(self, **kwargs: Any) -> "UnifiedLogger":
        """
        Create a new logger with additional bound context.

        This follows the structlog pattern of immutable context binding.

        Args:
            **kwargs: Key-value pairs to bind to the logger context

        Returns:
            New UnifiedLogger instance with the additional context
        """
        new_logger = UnifiedLogger(self.name)
        new_logger._bound_context = {**self._bound_context, **kwargs}
        return new_logger

    def unbind(self, *keys: str) -> "UnifiedLogger":
        """
        Create a new logger with specified keys removed from context.

        Args:
            *keys: Keys to remove from the logger context

        Returns:
            New UnifiedLogger instance with the keys removed
        """
        new_logger = UnifiedLogger(self.name)
        new_logger._bound_context = {k: v for k, v in self._bound_context.items() if k not in keys}
        return new_logger

    def new(self, **kwargs: Any) -> "UnifiedLogger":
        """
        Create a new logger with fresh context.

        This clears all bound context and starts with the provided context.

        Args:
            **kwargs: Key-value pairs for the new logger context

        Returns:
            New UnifiedLogger instance with only the provided context
        """
        new_logger = UnifiedLogger(self.name)
        new_logger._bound_context = kwargs.copy()
        return new_logger

    # ASYNC METHODS - For use in FastAPI endpoints and async contexts

    async def log(
        self,
        level: str,
        message: str,
        *,
        error: str | Exception | None = None,
        background_tasks: BackgroundTasks | None = None,
        extra: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Log a message at the specified level (async version).

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            error: Exception object for error logs
            background_tasks: FastAPI BackgroundTasks for async processing
            extra: Additional structured data
            **kwargs: Additional key-value pairs for structured logging
        """
        # Combine extra data and kwargs
        extra_data = {**(extra or {}), **kwargs}

        # Log to console synchronously
        self._log_to_console(level, message, extra_data)

        # Log to database asynchronously
        if background_tasks:
            # Use background task for async processing
            background_tasks.add_task(
                self._log_to_database, level, message, error, extra_data, None
            )
        else:
            # Direct async call
            try:
                await self._log_to_database(level, message, error, extra_data, None)
            except Exception as e:
                # Don't let database logging failures break the application
                self._console_logger.error(f"Async database logging failed: {e}")

    async def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message (async)."""
        await self.log("DEBUG", message, **kwargs)

    async def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message (async)."""
        await self.log("INFO", message, **kwargs)

    async def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message (async)."""
        await self.log("WARNING", message, **kwargs)

    async def error(
        self, message: str, error: str | Exception | None = None, **kwargs: Any
    ) -> None:
        """Log an error message (async)."""
        await self.log("ERROR", message, error=error, **kwargs)

    async def critical(
        self, message: str, error: str | Exception | None = None, **kwargs: Any
    ) -> None:
        """Log a critical message (async)."""
        await self.log("CRITICAL", message, error=error, **kwargs)

    # SYNC METHODS - For backward compatibility and non-async contexts

    def sync_log(
        self,
        level: str,
        message: str,
        *,
        error: str | Exception | None = None,
        extra: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Synchronous logging method for non-async contexts.

        This logs to console immediately and schedules database logging
        to run in the background without blocking.
        """
        # Combine extra data and kwargs
        extra_data = {**(extra or {}), **kwargs}

        # Log to console synchronously
        self._log_to_console(level, message, extra_data)

        # Schedule database logging in background
        try:
            # Check if we have an event loop running
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._log_to_database(level, message, error, extra_data, None))
            # Store task reference to prevent it from being garbage collected
            task.add_done_callback(lambda t: None)  # Simple done callback
        except RuntimeError:
            # No event loop running, log only to console
            # This can happen during application startup/shutdown
            pass

    def sync_debug(self, message: str, **kwargs: Any) -> None:
        """Synchronous debug logging."""
        self.sync_log("DEBUG", message, **kwargs)

    def sync_info(self, message: str, **kwargs: Any) -> None:
        """Synchronous info logging."""
        self.sync_log("INFO", message, **kwargs)

    def sync_warning(self, message: str, **kwargs: Any) -> None:
        """Synchronous warning logging."""
        self.sync_log("WARNING", message, **kwargs)

    def sync_error(
        self, message: str, error: str | Exception | None = None, **kwargs: Any
    ) -> None:
        """Synchronous error logging."""
        self.sync_log("ERROR", message, error=error, **kwargs)

    def sync_critical(
        self, message: str, error: str | Exception | None = None, **kwargs: Any
    ) -> None:
        """Synchronous critical logging."""
        self.sync_log("CRITICAL", message, error=error, **kwargs)


# Global logger cache for performance
_logger_cache: dict[str, UnifiedLogger] = {}


def get_logger(name: str) -> UnifiedLogger:
    """
    Get a unified logger instance.

    This is a drop-in replacement for logging.getLogger() that provides
    unified logging to multiple destinations with automatic context injection.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        UnifiedLogger instance
    """
    if name not in _logger_cache:
        _logger_cache[name] = UnifiedLogger(name)
    return _logger_cache[name]
