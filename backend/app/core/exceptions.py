"""
Domain-specific exceptions for the Kidney Genetics Database API.

Provides structured exception hierarchy that maps to standardized HTTP responses
through middleware, ensuring consistent error handling across the application.
"""

import traceback
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class KidneyGeneticsException(Exception):
    """Base exception for all Kidney Genetics Database API errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        self.message = message
        self.context = context or {}
        super().__init__(message)


class GeneNotFoundError(KidneyGeneticsException):
    """Gene not found in database."""

    def __init__(self, gene_identifier: str | int, context: dict[str, Any] | None = None):
        message = f"Gene '{gene_identifier}' not found"
        super().__init__(message, context)
        self.gene_identifier = str(gene_identifier)


class DataSourceError(KidneyGeneticsException):
    """Data source related errors."""

    def __init__(
        self,
        source_name: str,
        operation: str,
        detail: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        if detail:
            message = f"Data source '{source_name}' error during {operation}: {detail}"
        else:
            message = f"Data source '{source_name}' error during {operation}"
        super().__init__(message, context)
        self.source_name = source_name
        self.operation = operation
        self.detail = detail


class ValidationError(KidneyGeneticsException):
    """Data validation error."""

    def __init__(
        self,
        field: str | None = None,
        reason: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        if field and reason:
            message = f"Validation failed for '{field}': {reason}"
        elif field:
            message = f"Validation failed for '{field}'"
        elif reason:
            message = f"Validation failed: {reason}"
        else:
            message = "Validation failed"
        super().__init__(message, context)
        self.field = field
        self.reason = reason


class ExternalServiceError(KidneyGeneticsException):
    """External service failure (HGNC, HPO, PubTator, etc.)."""

    def __init__(
        self,
        service_name: str,
        operation: str | None = None,
        detail: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        if operation and detail:
            message = f"External service '{service_name}' error during {operation}: {detail}"
        elif operation:
            message = f"External service '{service_name}' error during {operation}"
        elif detail:
            message = f"External service '{service_name}' error: {detail}"
        else:
            message = f"External service '{service_name}' is unavailable"
        super().__init__(message, context)
        self.service_name = service_name
        self.operation = operation
        self.detail = detail


class DatabaseError(KidneyGeneticsException):
    """Database operation error."""

    def __init__(
        self, operation: str, detail: str | None = None, context: dict[str, Any] | None = None
    ):
        if detail:
            message = f"Database error during {operation}: {detail}"
        else:
            message = f"Database error during {operation}"
        super().__init__(message, context)
        self.operation = operation
        self.detail = detail


class PipelineError(KidneyGeneticsException):
    """Data pipeline processing error."""

    def __init__(
        self, pipeline_stage: str, detail: str | None = None, context: dict[str, Any] | None = None
    ):
        if detail:
            message = f"Pipeline error in {pipeline_stage}: {detail}"
        else:
            message = f"Pipeline error in {pipeline_stage}"
        super().__init__(message, context)
        self.pipeline_stage = pipeline_stage
        self.detail = detail


class CacheError(KidneyGeneticsException):
    """Cache operation error."""

    def __init__(
        self,
        operation: str,
        cache_key: str | None = None,
        detail: str | None = None,
        context: dict[str, Any] | None = None,
    ):
        if cache_key and detail:
            message = f"Cache error during {operation} for key '{cache_key}': {detail}"
        elif cache_key:
            message = f"Cache error during {operation} for key '{cache_key}'"
        elif detail:
            message = f"Cache error during {operation}: {detail}"
        else:
            message = f"Cache error during {operation}"
        super().__init__(message, context)
        self.operation = operation
        self.cache_key = cache_key
        self.detail = detail


class AuthenticationError(KidneyGeneticsException):
    """Authentication failure."""

    def __init__(self, reason: str = "Invalid credentials", context: dict[str, Any] | None = None):
        super().__init__(reason, context)
        self.reason = reason


class PermissionDeniedError(KidneyGeneticsException):
    """Permission denied for requested operation."""

    def __init__(
        self, required_permission: str, operation: str, context: dict[str, Any] | None = None
    ):
        message = f"Permission denied for {operation}. Requires {required_permission}"
        super().__init__(message, context)
        self.required_permission = required_permission
        self.operation = operation


class ResourceConflictError(KidneyGeneticsException):
    """Resource conflict (e.g., duplicate creation)."""

    def __init__(
        self, resource_type: str, conflict_reason: str, context: dict[str, Any] | None = None
    ):
        message = f"{resource_type} conflict: {conflict_reason}"
        super().__init__(message, context)
        self.resource_type = resource_type
        self.conflict_reason = conflict_reason


class RateLimitExceededError(KidneyGeneticsException):
    """Rate limit exceeded for external service calls."""

    def __init__(
        self,
        service_name: str,
        retry_after: int | None = None,
        context: dict[str, Any] | None = None,
    ):
        message = f"Rate limit exceeded for {service_name}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message, context)
        self.service_name = service_name
        self.retry_after = retry_after


def log_exception(exception: Exception, context: dict[str, Any] | None = None) -> str:
    """Log an exception with context and return an error ID for tracking.

    Args:
        exception: The exception to log
        context: Additional context for debugging

    Returns:
        Unique error ID for tracking
    """
    from app.core.responses import ResponseBuilder

    error_id = ResponseBuilder.generate_error_id()

    # Enhanced logging with structured data
    logger.sync_error(
        "Exception occurred",
        error_id=error_id,
        exception_type=type(exception).__name__,
        exception_message=str(exception),
        context=context or {},
        traceback=traceback.format_exc(),
    )

    return error_id


async def async_log_exception(exception: Exception, context: dict[str, Any] | None = None) -> str:
    """Async version of log_exception for use in async contexts."""
    return log_exception(
        exception, context
    )  # Logging is inherently sync, so we just call the sync version
