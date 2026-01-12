"""
Data Release schemas for request/response validation
"""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# CalVer validation pattern
CALVER_PATTERN = re.compile(r"^\d{4}\.\d{1,2}$")  # YYYY.M or YYYY.MM


class ReleaseBase(BaseModel):
    """Base release schema"""

    version: str = Field(..., description="CalVer version (e.g., 2025.10)")
    release_notes: str | None = Field(None, description="Optional release notes")

    @field_validator("version")
    @classmethod
    def validate_calver_format(cls, v: str) -> str:
        """Validate CalVer format YYYY.MM"""
        if not CALVER_PATTERN.match(v):
            raise ValueError(f"Version must be CalVer format YYYY.MM, got: {v}")
        return v


class ReleaseCreate(ReleaseBase):
    """Schema for creating a new release"""

    pass


class ReleaseUpdate(BaseModel):
    """Schema for updating a draft release"""

    version: str | None = Field(None, description="CalVer version (e.g., 2025.10)")
    release_notes: str | None = Field(None, description="Optional release notes")

    @field_validator("version")
    @classmethod
    def validate_calver_format(cls, v: str | None) -> str | None:
        """Validate CalVer format YYYY.MM"""
        if v is not None and not CALVER_PATTERN.match(v):
            raise ValueError(f"Version must be CalVer format YYYY.MM, got: {v}")
        return v


class ReleaseResponse(ReleaseBase):
    """Schema for release response"""

    id: int
    status: str
    release_date: datetime | None = None
    published_at: datetime | None = None
    published_by_id: int | None = None
    gene_count: int | None = None
    total_evidence_count: int | None = None
    export_file_path: str | None = None
    export_checksum: str | None = None
    doi: str | None = None
    citation_text: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Allows conversion from SQLAlchemy models


class ReleaseList(BaseModel):
    """Schema for paginated release list"""

    data: list[ReleaseResponse]
    meta: dict[str, int]


class ReleaseGeneResponse(BaseModel):
    """Schema for gene from a release"""

    approved_symbol: str
    hgnc_id: str
    aliases: list[str] | None = None
    valid_from: datetime | None = None
    valid_to: datetime | str | None = None  # Can be 'infinity'


class ReleaseGenesResponse(BaseModel):
    """Schema for genes from a release"""

    version: str
    release_date: datetime | None
    total: int
    limit: int
    offset: int
    genes: list[dict]  # Using dict for flexibility with temporal data
