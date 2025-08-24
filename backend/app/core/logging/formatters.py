"""
Logging formatters for console and structured output.

Provides consistent formatting for both console logging (human-readable)
and structured logging (JSON for database storage).
"""

import json
import logging

from .context import get_context


class ContextualFormatter(logging.Formatter):
    """
    Formatter that includes request context in log messages.

    Automatically adds request ID, user context, and other contextual
    information to log records for better observability.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Get current context
        context = get_context()

        # Add context to record if not already present
        if context and not hasattr(record, 'request_id'):
            for key, value in context.items():
                setattr(record, key, value)

        return super().format(record)


class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs structured JSON logs.

    Used for database storage and structured log analysis.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Start with basic log data
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "source": record.name,
        }

        # Add context
        context = get_context()
        if context:
            log_data.update(context)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra attributes
        extra_data = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'getMessage',
                'message', 'asctime'
            }:
                extra_data[key] = value

        if extra_data:
            log_data["extra"] = extra_data

        return json.dumps(log_data, default=str, ensure_ascii=False)


def get_console_formatter() -> ContextualFormatter:
    """Get the standard console formatter with context support."""
    return ContextualFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        + " | request_id=%(request_id)s" if get_context().get("request_id") else ""
    )


def get_json_formatter() -> JSONFormatter:
    """Get the JSON formatter for structured logging."""
    return JSONFormatter()
