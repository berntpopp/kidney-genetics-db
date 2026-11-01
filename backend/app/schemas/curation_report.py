"""Curation report and notification preference schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class ReportCreate(BaseModel):
    gene_symbol: str = Field(..., min_length=1, max_length=100)
    association_id: int | None = None
    kind: Literal["problem", "suggestion"]
    message: str = Field(..., min_length=1, max_length=4000)
    reporter_name: str | None = Field(None, max_length=200)
    reporter_email: EmailStr | None = Field(None, max_length=320)
    website: str = Field("", max_length=500, description="Honeypot; real users leave it empty")


class ReportUpdate(BaseModel):
    status: Literal["open", "resolved", "dismissed"]


class ReportResponse(BaseModel):
    """Curator view only: includes the reporter's contact details."""

    id: int
    gene_symbol: str
    association_id: int | None
    kind: str
    message: str
    reporter_name: str | None
    reporter_email: str | None
    status: str
    handled_by: int | None
    handled_at: datetime | None
    created_at: datetime


class ReportMeta(BaseModel):
    total: int
    limit: int
    offset: int
    open_count: int


class ReportList(BaseModel):
    data: list[ReportResponse]
    meta: ReportMeta


class NotificationPref(BaseModel):
    event: str
    label: str
    enabled: bool
