"""
Pydantic schemas for genes
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class GeneBase(BaseModel):
    """Base gene schema"""
    hgnc_id: Optional[str] = None
    approved_symbol: str
    aliases: Optional[List[str]] = []


class GeneCreate(GeneBase):
    """Schema for creating a gene"""
    pass


class GeneUpdate(BaseModel):
    """Schema for updating a gene"""
    hgnc_id: Optional[str] = None
    approved_symbol: Optional[str] = None
    aliases: Optional[List[str]] = None


class GeneInDB(GeneBase):
    """Gene schema with database fields"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Gene(GeneInDB):
    """Gene schema for API responses"""
    evidence_count: Optional[int] = 0
    evidence_score: Optional[float] = None
    sources: Optional[List[str]] = []


class GeneList(BaseModel):
    """Response for gene list endpoint"""
    items: List[Gene]
    total: int
    page: int = 1
    per_page: int = 100


class GeneEvidenceCreate(BaseModel):
    """Schema for creating gene evidence"""
    gene_id: int
    source_name: str
    source_detail: Optional[str] = None
    evidence_data: Dict[str, Any]
    evidence_date: Optional[datetime] = None


class GeneCurationSummary(BaseModel):
    """Summary of gene curation"""
    gene_id: int
    gene_symbol: str
    evidence_count: int = 0
    source_count: int = 0
    evidence_score: Optional[float] = None
    classification: Optional[str] = None
    panelapp_panels: List[str] = []
    hpo_terms: List[str] = []
    
    class Config:
        from_attributes = True