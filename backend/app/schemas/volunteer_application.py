"""Volunteer application schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class ApplicationCreate(BaseModel):
    gene_symbol: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr = Field(..., max_length=320)
    affiliation: str | None = Field(None, max_length=300)
    orcid: str | None = Field(None, pattern=r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
    motivation: str = Field(..., min_length=1, max_length=4000)
    website: str = Field("", max_length=500, description="Honeypot; real users leave it empty")


class ApplicationDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = Field(None, max_length=2000)
    role: Literal["viewer", "curator"] = "curator"


class ApplicationResponse(BaseModel):
    """Admin view only: includes the applicant's contact details."""

    id: int
    gene_symbol: str
    name: str
    email: str
    affiliation: str | None
    orcid: str | None
    motivation: str
    status: str
    decided_by: int | None
    decided_at: datetime | None
    decision_note: str | None
    user_id: int | None
    created_at: datetime


class ApplicationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    pending_count: int


class ApplicationList(BaseModel):
    data: list[ApplicationResponse]
    meta: ApplicationMeta
