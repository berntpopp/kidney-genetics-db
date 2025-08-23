"""
Middleware for standardized error handling across the Kidney Genetics Database API.
"""

import logging
import traceback
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import (
    AuthenticationError,
    CacheError,
    DatabaseError,
    DataSourceError,
    ExternalServiceError,
    GeneNotFoundError,
    KidneyGeneticsException,
    PermissionDeniedError,
    PipelineError,
    RateLimitExceededError,
    ResourceConflictError,
    ValidationError,
    log_exception,
)
from app.core.responses import ResponseBuilder

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle exceptions and return standardized error responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """Process request and handle any exceptions with standardized responses.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint

        Returns:
            Response from endpoint or standardized error response
        """
        try:
            response = await call_next(request)
            return response

        except KidneyGeneticsException as e:
            return await self._handle_domain_exception(e, request)

        except Exception as e:
            return await self._handle_unexpected_exception(e, request)

    async def _handle_domain_exception(
        self, exception: KidneyGeneticsException, request: Request
    ) -> JSONResponse:
        """Handle domain-specific exceptions with appropriate responses."""

        # Log at appropriate level based on exception type
        if isinstance(exception, GeneNotFoundError | ValidationError):
            logger.warning(f"{type(exception).__name__}: {exception}")
        elif isinstance(exception, AuthenticationError | PermissionDeniedError):
            logger.warning(f"Security exception: {type(exception).__name__}: {exception}")
        else:
            logger.error(f"Domain exception: {type(exception).__name__}: {exception}", exc_info=True)

        # Map exceptions to standardized responses
        if isinstance(exception, GeneNotFoundError):
            return ResponseBuilder.build_not_found_error("Gene", exception.gene_identifier, request)
        elif isinstance(exception, ValidationError):
            return ResponseBuilder.build_validation_error(exception.field, exception.reason, request)
        elif isinstance(exception, AuthenticationError):
            return ResponseBuilder.build_error_response(
                status_code=401,
                error_code="AUTHENTICATION_FAILED",
                title="Authentication Failed",
                detail=exception.reason,
                request=request
            )
        elif isinstance(exception, PermissionDeniedError):
            return ResponseBuilder.build_error_response(
                status_code=403,
                error_code="PERMISSION_DENIED",
                title="Permission Denied",
                detail=str(exception),
                request=request
            )
        elif isinstance(exception, ResourceConflictError):
            return ResponseBuilder.build_error_response(
                status_code=409,
                error_code="RESOURCE_CONFLICT",
                title="Resource Conflict",
                detail=str(exception),
                request=request
            )
        elif isinstance(exception, RateLimitExceededError):
            response = ResponseBuilder.build_error_response(
                status_code=429,
                error_code="RATE_LIMIT_EXCEEDED",
                title="Rate Limit Exceeded",
                detail=str(exception),
                request=request
            )
            if exception.retry_after:
                response.headers["Retry-After"] = str(exception.retry_after)
            return response
        elif isinstance(exception, DataSourceError | ExternalServiceError | PipelineError):
            return ResponseBuilder.build_error_response(
                status_code=502,
                error_code="EXTERNAL_SERVICE_ERROR",
                title="External Service Error",
                detail=str(exception),
                request=request
            )
        elif isinstance(exception, DatabaseError | CacheError):
            return ResponseBuilder.build_error_response(
                status_code=503,
                error_code="SERVICE_UNAVAILABLE",
                title="Service Temporarily Unavailable",
                detail="Database service temporarily unavailable. Please try again later.",
                request=request
            )
        else:
            # Generic domain exception
            error_id = log_exception(exception, {"request_path": str(request.url)})
            return ResponseBuilder.build_internal_error(error_id, request)

    async def _handle_unexpected_exception(
        self, exception: Exception, request: Request
    ) -> JSONResponse:
        """Handle unexpected exceptions with error tracking."""

        # Log the exception with full details
        error_id = log_exception(
            exception,
            {
                "request_path": str(request.url),
                "request_method": request.method,
                "traceback": traceback.format_exc(),
            }
        )

        logger.error(
            f"Unexpected exception [{error_id}]: {type(exception).__name__}",
            extra={
                "error_id": error_id,
                "exception_type": type(exception).__name__,
                "request_path": str(request.url),
                "request_method": request.method,
            },
            exc_info=True
        )

        return ResponseBuilder.build_internal_error(error_id, request)


def register_error_handlers(app: FastAPI):
    """Register exception handlers with FastAPI application.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with standardized format."""
        return ResponseBuilder.build_error_response(
            status_code=exc.status_code,
            error_code="HTTP_ERROR",
            title="HTTP Error",
            detail=exc.detail,
            request=request
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors with standardized format."""
        errors = exc.errors()
        if errors:
            # Use first error for main message
            first_error = errors[0]
            field = ".".join(str(loc) for loc in first_error["loc"] if loc != "body")
            reason = first_error["msg"]

            return ResponseBuilder.build_validation_error(field, reason, request)
        else:
            return ResponseBuilder.build_validation_error(request=request)

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle database errors."""
        error_id = log_exception(exc, {"request_path": str(request.url)})

        return ResponseBuilder.build_error_response(
            status_code=503,
            error_code="DATABASE_ERROR",
            title="Database Service Unavailable",
            detail="Database service temporarily unavailable. Please try again later.",
            error_id=error_id,
            request=request
        )

    @app.exception_handler(ResponseValidationError)
    async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
        """Handle response validation errors (500 - internal server error)."""
        error_id = log_exception(exc, {
            "request_path": str(request.url),
            "validation_errors": exc.errors()
        })

        logger.error(f"Response validation error [{error_id}]: {exc.errors()}")

        return ResponseBuilder.build_error_response(
            status_code=500,
            error_code="RESPONSE_VALIDATION_ERROR",
            title="Internal Server Error",
            detail="Server response validation failed. This is a server-side error.",
            error_id=error_id,
            request=request
        )

    # Add the middleware for catching unexpected exceptions
    app.add_middleware(ErrorHandlingMiddleware)

    logger.info("Error handling middleware and exception handlers registered")
