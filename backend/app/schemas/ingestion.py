"""
Pydantic schemas for static content ingestion API
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScoringMetadata(BaseModel):
    """Scoring configuration for static sources"""
    type: str = Field(
        ..., 
        pattern="^(count|classification|fixed)$",
        description="Scoring type: count, classification, or fixed"
    )
    field: Optional[str] = Field(
        None,
        description="JSON field to use for scoring (for count/classification types)"
    )
    weight: Optional[float] = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Weight multiplier for count-based scoring"
    )
    weight_map: Optional[Dict[str, float]] = Field(
        None,
        description="Classification to score mapping (for classification type)"
    )
    score: Optional[float] = Field(
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
    description: Optional[str] = None
    source_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    scoring_metadata: ScoringMetadata = Field(
        default_factory=lambda: ScoringMetadata(type="count", weight=0.5)
    )


class StaticSourceUpdate(BaseModel):
    """Update static source configuration"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    source_metadata: Optional[Dict[str, Any]] = None
    scoring_metadata: Optional[ScoringMetadata] = None
    is_active: Optional[bool] = None


class StaticSourceResponse(BaseModel):
    """Static source response"""
    id: int
    source_type: str
    source_name: str
    display_name: str
    description: Optional[str]
    source_metadata: Dict[str, Any]
    scoring_metadata: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    
    # Statistics
    upload_count: Optional[int] = None
    total_genes: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    """Upload response"""
    status: str
    upload_id: Optional[int] = None
    stats: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = None


class UploadListItem(BaseModel):
    """Upload list item"""
    id: int
    evidence_name: str
    original_filename: Optional[str]
    upload_status: str
    gene_count: Optional[int]
    genes_normalized: Optional[int]
    genes_failed: Optional[int]
    genes_staged: Optional[int]
    created_at: datetime
    processed_at: Optional[datetime]
    uploaded_by: Optional[str]
    upload_metadata: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    """Audit log entry"""
    id: int
    source_id: int
    upload_id: Optional[int]
    action: str
    details: Dict[str, Any]
    performed_by: Optional[str]
    performed_at: datetime
    
    model_config = ConfigDict(from_attributes=True)