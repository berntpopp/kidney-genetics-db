"""
Unified response builders for consistent API responses across all endpoints.
"""

import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.jsonapi import build_jsonapi_response


class ResponseBuilder:
    """Build standardized API responses with consistent format."""

    @staticmethod
    def generate_error_id() -> str:
        """Generate unique error ID for tracking."""
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex[:8]
        return f"err_{timestamp}_{unique_id}"

    @staticmethod
    def build_success_response(
        data: Any,
        meta: dict[str, Any] | None = None,
        links: dict[str, str] | None = None,
        status_code: int = status.HTTP_200_OK,
    ) -> dict[str, Any]:
        """Build standardized success response.

        Args:
            data: Main response data
            meta: Response metadata (pagination, timing, etc.)
            links: Navigation links (for pagination)
            status_code: HTTP status code

        Returns:
            Standardized response dictionary
        """
        response = {
            "data": data,
            "meta": {"timestamp": datetime.utcnow().isoformat() + "Z", **(meta or {})},
        }

        if links:
            response["links"] = links

        return response

    @staticmethod
    def build_paginated_response(
        data: Any,
        total: int,
        page_number: int,
        page_size: int,
        base_url: str,
        additional_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build paginated response with navigation links.

        Args:
            data: Page data
            total: Total number of items
            page_number: Current page number (1-based)
            page_size: Items per page
            base_url: Base URL for building navigation links
            additional_meta: Additional metadata to include

        Returns:
            Paginated response with links
        """
        total_pages = (total + page_size - 1) // page_size

        # Build navigation links
        links = {
            "self": f"{base_url}?page[number]={page_number}&page[size]={page_size}",
            "first": f"{base_url}?page[number]=1&page[size]={page_size}",
            "last": f"{base_url}?page[number]={total_pages}&page[size]={page_size}",
        }

        if page_number > 1:
            links["prev"] = f"{base_url}?page[number]={page_number - 1}&page[size]={page_size}"

        if page_number < total_pages:
            links["next"] = f"{base_url}?page[number]={page_number + 1}&page[size]={page_size}"

        # Build metadata
        meta = {
            "pagination": {
                "page": page_number,
                "size": page_size,
                "total": total,
                "pages": total_pages,
            },
            **(additional_meta or {}),
        }

        return ResponseBuilder.build_success_response(data=data, meta=meta, links=links)

    @staticmethod
    def build_error_response(
        status_code: int,
        error_code: str,
        title: str,
        detail: str,
        source: dict[str, str] | None = None,
        error_id: str | None = None,
        request: Request | None = None,
        context: dict[str, Any] | None = None,
    ) -> JSONResponse:
        """Build standardized error response.

        Args:
            status_code: HTTP status code
            error_code: Machine-readable error code
            title: Human-readable error title
            detail: Specific error message
            source: Error source information (pointer, parameter)
            error_id: Unique error identifier
            request: FastAPI request for context
            context: Additional error context for debugging

        Returns:
            JSONResponse with standardized error format
        """
        if not error_id:
            error_id = ResponseBuilder.generate_error_id()

        error_meta: dict[str, Any] = {
            "error_id": error_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        error_obj: dict[str, Any] = {
            "status": str(status_code),
            "code": error_code,
            "title": title,
            "detail": detail,
            "meta": error_meta,
        }

        if source:
            error_obj["source"] = source

        if request:
            error_meta["path"] = str(request.url.path)
            # WebSocket connections don't have a method attribute
            if hasattr(request, "method"):
                error_meta["method"] = request.method

        # Add debug context in development (when context is provided)
        if context:
            error_meta["debug_context"] = context

        error_body: dict[str, Any] = {"error": error_obj}

        return JSONResponse(status_code=status_code, content=error_body)

    @staticmethod
    def build_not_found_error(
        resource_type: str,
        identifier: str | int,
        request: Request | None = None,
    ) -> JSONResponse:
        """Build standardized 404 Not Found error."""
        return ResponseBuilder.build_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            title="Resource Not Found",
            detail=f"{resource_type} '{identifier}' not found",
            source={"parameter": "identifier"},
            request=request,
            context={"resource_type": resource_type, "identifier": str(identifier)},
        )

    @staticmethod
    def build_validation_error(
        field: str | None = None,
        reason: str | None = None,
        request: Request | None = None,
    ) -> JSONResponse:
        """Build standardized 400 Bad Request validation error."""
        if field and reason:
            detail = f"Validation failed for '{field}': {reason}"
            source = {"pointer": f"/data/attributes/{field}"}
        elif field:
            detail = f"Validation failed for '{field}'"
            source = {"pointer": f"/data/attributes/{field}"}
        elif reason:
            detail = f"Validation failed: {reason}"
            source = None
        else:
            detail = "Validation failed"
            source = None

        return ResponseBuilder.build_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            title="Validation Error",
            detail=detail,
            source=source,
            request=request,
            context={"field": field, "reason": reason},
        )

    @staticmethod
    def build_internal_error(
        error_id: str | None = None,
        request: Request | None = None,
    ) -> JSONResponse:
        """Build standardized 500 Internal Server Error."""
        if not error_id:
            error_id = ResponseBuilder.generate_error_id()

        return ResponseBuilder.build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_ERROR",
            title="Internal Server Error",
            detail=f"An unexpected error occurred. Please contact support with error ID: {error_id}",
            error_id=error_id,
            request=request,
        )

    @staticmethod
    def build_jsonapi_compatible_response(
        data: Any,
        total: int,
        page_number: int,
        page_size: int,
        base_url: str,
        additional_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build JSON:API compatible response for backward compatibility.

        This preserves existing JSON:API format for endpoints that need it.
        """
        result = build_jsonapi_response(
            data=data,
            total=total,
            page_number=page_number,
            page_size=page_size,
            base_url=base_url,
        )
        # Merge additional_meta into the response meta if provided
        if additional_meta:
            result["meta"].update(additional_meta)
        return result
