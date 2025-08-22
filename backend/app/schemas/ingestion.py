"""
Pydantic schemas for static content ingestion API
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScoringMetadata(BaseModel):
    """Scoring configuration for static sources"""
    type: str = Field(
        ...,
        pattern="^(count|classification|fixed)$",
        description="Scoring type: count, classification, or fixed"
    )
    field: str | None = Field(
        None,
        description="JSON field to use for scoring (for count/classification types)"
    )
    weight: float | None = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Weight multiplier for count-based scoring"
    )
    weight_map: dict[str, float] | None = Field(
        None,
        description="Classification to score mapping (for classification type)"
    )
    score: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Fixed score (for fixed type)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "count",
                    "field": "panels",
                    "weight": 0.7
                },
                {
                    "type": "classification",
                    "field": "confidence",
                    "weight_map": {
                        "high": 1.0,
                        "medium": 0.6,
                        "low": 0.3
                    }
                },
                {
                    "type": "fixed",
                    "score": 0.5
                }
            ]
        }
    )


class StaticSourceCreate(BaseModel):
    """Create a new static source"""
    source_type: str = Field(..., pattern="^(diagnostic_panel|manual_curation|literature_review|custom)$")
    source_name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    source_metadata: dict[str, Any] | None = Field(default_factory=dict)
    scoring_metadata: ScoringMetadata = Field(
        default_factory=lambda: ScoringMetadata(type="count", field="panels", weight=0.5)
    )


class StaticSourceUpdate(BaseModel):
    """Update static source configuration"""
    display_name: str | None = None
    description: str | None = None
    source_metadata: dict[str, Any] | None = None
    scoring_metadata: ScoringMetadata | None = None
    is_active: bool | None = None


class StaticSourceResponse(BaseModel):
    """Static source response"""
    id: int
    source_type: str
    source_name: str
    display_name: str
    description: str | None
    source_metadata: dict[str, Any]
    scoring_metadata: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None

    # Statistics
    upload_count: int | None = None
    total_genes: int | None = None

    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    """Upload response"""
    status: str
    upload_id: int | None = None
    stats: dict[str, Any] | None = None
    message: str | None = None
    provider_metadata: dict[str, Any] | None = None


class UploadListItem(BaseModel):
    """Upload list item"""
    id: int
    evidence_name: str
    original_filename: str | None
    upload_status: str
    gene_count: int | None
    genes_normalized: int | None
    genes_failed: int | None
    genes_staged: int | None
    created_at: datetime
    processed_at: datetime | None
    uploaded_by: str | None
    upload_metadata: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    """Audit log entry"""
    id: int
    source_id: int
    upload_id: int | None
    action: str
    details: dict[str, Any]
    performed_by: str | None
    performed_at: datetime

    model_config = ConfigDict(from_attributes=True)

