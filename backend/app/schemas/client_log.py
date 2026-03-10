"""Schemas for client-side log reporting."""

from pydantic import BaseModel, Field


class ClientLogCreate(BaseModel):
    """Schema for incoming client-side log entries."""

    level: str = Field(
        ...,
        pattern="^(DEBUG|INFO|WARN|ERROR|CRITICAL)$",
        description="Log level",
    )
    message: str = Field(..., max_length=2000, description="Log message")
    error_type: str | None = Field(None, max_length=200, description="Error class name")
    error_message: str | None = Field(None, max_length=2000, description="Error message")
    stack_trace: str | None = Field(None, max_length=10000, description="Error stack trace")
    url: str | None = Field(None, max_length=2000, description="Page URL where error occurred")
    user_agent: str | None = Field(None, max_length=500, description="Browser user agent")
    context: dict | None = Field(None, description="Additional context (JSONB)")


class ClientLogResponse(BaseModel):
    """Response after accepting a client log."""

    status: str = "accepted"
