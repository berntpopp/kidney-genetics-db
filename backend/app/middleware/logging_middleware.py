"""
Logging middleware for comprehensive request/response logging with correlation.

Replaces the existing error handling middleware with enhanced logging
capabilities, request correlation, and automatic context binding.
"""

import time
import traceback
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.core.logging.context import bind_context, clear_context, extract_context_from_request


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive logging middleware for request/response lifecycle tracking.

    Provides:
    - Unique request ID generation for correlation
    - Automatic context binding for all logs in request
    - Request/response timing and performance tracking
    - Enhanced error logging with full context
    - Replaces existing error handling middleware
    """

    def __init__(
        self,
        app,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_size: int = 10000,
        slow_request_threshold_ms: int = 1000,
        exclude_paths: list = None,
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        self.slow_request_threshold_ms = slow_request_threshold_ms
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        self.logger = get_logger("request_middleware")

    def _should_log_request(self, request: Request) -> bool:
        """Determine if request should be logged."""
        return request.url.path not in self.exclude_paths

    def _sanitize_headers(self, headers: dict) -> dict:
        """Remove sensitive headers from logging."""
        sensitive_headers = {
            "authorization", "cookie", "x-api-key", "x-auth-token",
            "x-access-token", "authentication"
        }
        return {
            key: "[REDACTED]" if key.lower() in sensitive_headers else value
            for key, value in headers.items()
        }

    async def _read_request_body(self, request: Request) -> str:
        """Safely read request body for logging."""
        if not self.log_request_body:
            return None

        try:
            body = await request.body()
            if len(body) > self.max_body_size:
                return f"[BODY TOO LARGE: {len(body)} bytes]"

            try:
                return body.decode("utf-8")[:self.max_body_size]
            except UnicodeDecodeError:
                return f"[BINARY BODY: {len(body)} bytes]"
        except Exception:
            return "[ERROR READING BODY]"

    def _extract_client_info(self, request: Request) -> dict:
        """Extract client information from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif hasattr(request, "client") and request.client:
            client_ip = request.client.host
        else:
            client_ip = "unknown"

        return {
            "ip_address": client_ip,
            "user_agent": request.headers.get("User-Agent", "unknown"),
            "referer": request.headers.get("Referer", ""),
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response with comprehensive logging."""
        if not self._should_log_request(request):
            return await call_next(request)

        # Clear any existing context and set up request context
        clear_context()

        # Extract and bind request context
        context = extract_context_from_request(request)
        bind_context(**context)

        # Record start time
        start_time = time.perf_counter()

        # Extract request information
        client_info = self._extract_client_info(request)
        sanitized_headers = self._sanitize_headers(dict(request.headers))
        request_body = await self._read_request_body(request)

        # Log request start
        await self.logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            query_params=dict(request.query_params),
            headers=sanitized_headers,
            client_info=client_info,
            request_body=request_body,
        )

        # Process request
        response = None
        try:
            response = await call_next(request)

        except Exception as e:
            # Calculate processing time for error case
            processing_time = (time.perf_counter() - start_time) * 1000

            # Log the error with full context
            await self.logger.error(
                "Request failed with unhandled exception",
                error=e,
                method=request.method,
                path=request.url.path,
                url=str(request.url),
                processing_time_ms=int(processing_time),
                error_type=e.__class__.__name__,
                error_message=str(e),
                traceback=traceback.format_exc(),
                client_info=client_info,
            )

            # Return standardized error response
            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "request_id": context.get("request_id", "unknown"),
                    "timestamp": time.time(),
                },
            )

        # Calculate processing time
        processing_time = (time.perf_counter() - start_time) * 1000

        # Extract response information
        response_data = {}
        if self.log_response_body and hasattr(response, "body"):
            try:
                body_bytes = getattr(response, "body", b"")
                if body_bytes and len(body_bytes) <= self.max_body_size:
                    try:
                        response_data["response_body"] = body_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        response_data["response_body"] = f"[BINARY RESPONSE: {len(body_bytes)} bytes]"
                else:
                    response_data["response_body"] = f"[RESPONSE TOO LARGE: {len(body_bytes)} bytes]"
            except Exception:
                response_data["response_body"] = "[ERROR READING RESPONSE]"

        # Determine log level based on status code and processing time
        status_code = response.status_code
        if status_code >= 500:
            log_level = "ERROR"
        elif status_code >= 400 or processing_time > self.slow_request_threshold_ms:
            log_level = "WARNING"
        else:
            log_level = "INFO"

        # Log request completion
        log_message = f"Request completed: {request.method} {request.url.path}"

        if log_level == "ERROR":
            await self.logger.error(
                log_message,
                status_code=status_code,
                processing_time_ms=int(processing_time),
                response_headers=dict(response.headers),
                **response_data,
            )
        elif log_level == "WARNING":
            await self.logger.warning(
                log_message,
                status_code=status_code,
                processing_time_ms=int(processing_time),
                response_headers=dict(response.headers),
                **response_data,
            )
        else:
            await self.logger.info(
                log_message,
                status_code=status_code,
                processing_time_ms=int(processing_time),
                response_headers=dict(response.headers),
                **response_data,
            )

        # Add performance and correlation headers
        response.headers["X-Request-ID"] = context.get("request_id", "unknown")
        response.headers["X-Processing-Time"] = f"{processing_time:.1f}ms"

        return response
