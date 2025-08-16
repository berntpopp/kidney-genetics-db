"""
Pydantic schemas for gene normalization staging
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GeneNormalizationStagingResponse(BaseModel):
    """Response schema for gene normalization staging records"""
    
    id: int
    original_text: str
    source_name: str
    original_data: Dict[str, Any] = Field(default_factory=dict)
    normalization_log: Dict[str, Any]
    status: str
    priority_score: int
    requires_expert_review: bool
    created_at: datetime
    updated_at: datetime
    
    # Optional review fields
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    # Optional manual correction fields
    manual_approved_symbol: Optional[str] = None
    manual_hgnc_id: Optional[str] = None
    manual_aliases: Optional[List[str]] = None
    
    class Config:
        from_attributes = True


class GeneNormalizationLogResponse(BaseModel):
    """Response schema for gene normalization logs"""
    
    id: int
    original_text: str
    source_name: str
    success: bool
    approved_symbol: Optional[str] = None
    hgnc_id: Optional[str] = None
    normalization_log: Dict[str, Any]
    api_calls_made: int = 0
    processing_time_ms: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class StagingApprovalRequest(BaseModel):
    """Request schema for approving staging records"""
    
    approved_symbol: str = Field(..., description="Manually corrected gene symbol")
    hgnc_id: str = Field(..., description="HGNC ID for the gene")
    aliases: Optional[List[str]] = Field(default_factory=list, description="Gene aliases")
    reviewer: str = Field(default="system", description="Name of reviewer")
    notes: Optional[str] = Field(None, description="Review notes")


class StagingRejectionRequest(BaseModel):
    """Request schema for rejecting staging records"""
    
    reviewer: str = Field(default="system", description="Name of reviewer")
    notes: Optional[str] = Field(None, description="Rejection reason")


class StagingStatsResponse(BaseModel):
    """Response schema for staging statistics"""
    
    total_pending: int
    total_approved: int
    total_rejected: int
    by_source: Dict[str, int]


class NormalizationStatsResponse(BaseModel):
    """Response schema for normalization statistics"""
    
    total_attempts: int
    successful_attempts: int
    success_rate: float
    by_source: Dict[str, Dict[str, Any]]


class TestNormalizationRequest(BaseModel):
    """Request schema for testing gene normalization"""
    
    gene_text: str = Field(..., description="Gene text to normalize")
    source_name: str = Field(default="Manual Test", description="Source name")


class TestNormalizationResponse(BaseModel):
    """Response schema for testing gene normalization"""
    
    success: bool
    gene_text: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None