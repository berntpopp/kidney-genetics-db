"""
Request context management for unified logging.

Uses Python contextvars for request-scoped context that automatically
propagates through async operations within a request lifecycle.
"""

import contextvars
import uuid
from typing import Any

from fastapi import Request

# Context variables for request-scoped logging context
_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
_user_id_var: contextvars.ContextVar[int | None] = contextvars.ContextVar("user_id", default=None)
_username_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("username", default=None)
_ip_address_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "ip_address", default=None
)
_user_agent_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_agent", default=None
)
_endpoint_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("endpoint", default=None)
_method_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("method", default=None)


def bind_context(**kwargs: Any) -> None:
    """
    Bind values to the current logging context.

    This uses context variables to store request-scoped logging context
    that will be automatically included in all log entries within the request.

    Args:
        **kwargs: Key-value pairs to bind to the context
    """
    for key, value in kwargs.items():
        if key == "request_id":
            _request_id_var.set(value)
        elif key == "user_id":
            _user_id_var.set(value)
        elif key == "username":
            _username_var.set(value)
        elif key == "ip_address":
            _ip_address_var.set(value)
        elif key == "user_agent":
            _user_agent_var.set(value)
        elif key == "endpoint":
            _endpoint_var.set(value)
        elif key == "method":
            _method_var.set(value)


def clear_context() -> None:
    """Clear all logging context variables."""
    _request_id_var.set(None)
    _user_id_var.set(None)
    _username_var.set(None)
    _ip_address_var.set(None)
    _user_agent_var.set(None)
    _endpoint_var.set(None)
    _method_var.set(None)


def get_context() -> dict[str, Any]:
    """Get the current logging context."""
    context: dict[str, Any] = {}

    if request_id := _request_id_var.get(None):
        context["request_id"] = request_id
    if user_id := _user_id_var.get(None):
        context["user_id"] = user_id
    if username := _username_var.get(None):
        context["username"] = username
    if ip_address := _ip_address_var.get(None):
        context["ip_address"] = ip_address
    if user_agent := _user_agent_var.get(None):
        context["user_agent"] = user_agent
    if endpoint := _endpoint_var.get(None):
        context["endpoint"] = endpoint
    if method := _method_var.get(None):
        context["method"] = method

    return context


def extract_context_from_request(request: Request) -> dict[str, Any]:
    """
    Extract logging context from a FastAPI Request object.

    Args:
        request: FastAPI Request object

    Returns:
        Dictionary containing extracted context
    """
    context = {}

    # Generate request ID if not present
    request_id = getattr(request.state, "request_id", None)
    if not request_id:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

    context["request_id"] = request_id
    context["endpoint"] = request.url.path
    # WebSocket connections don't have a method attribute
    if hasattr(request, "method"):
        context["method"] = request.method

    # Extract IP address
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        context["ip_address"] = forwarded_for.split(",")[0].strip()
    elif hasattr(request, "client") and request.client:
        context["ip_address"] = request.client.host

    # Extract user agent
    context["user_agent"] = request.headers.get("User-Agent")

    # Extract user from request state (if available)
    if hasattr(request.state, "current_user"):
        user = request.state.current_user
        if user:
            context["user_id"] = getattr(user, "id", None)
            context["username"] = getattr(user, "username", None)

    return context
