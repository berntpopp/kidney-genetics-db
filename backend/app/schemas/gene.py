"""
Pydantic schemas for genes
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

class GeneBase(BaseModel):
    """Base gene schema"""

    hgnc_id: str | None = None
    approved_symbol: str
    aliases: list[str] | None = []

class GeneCreate(GeneBase):
    """Schema for creating a gene"""

    pass

class GeneUpdate(BaseModel):
    """Schema for updating a gene"""

    hgnc_id: str | None = None
    approved_symbol: str | None = None
    aliases: list[str] | None = None

class GeneInDB(GeneBase):
    """Gene schema with database fields"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Gene(GeneInDB):
    """Gene schema for API responses"""

    evidence_count: int | None = 0
    evidence_score: float | None = None
    sources: list[str] | None = []
    score_breakdown: dict[str, float] | None = None  # Raw normalized scores per source

class GeneList(BaseModel):
    """Response for gene list endpoint"""

    items: list[Gene]
    total: int
    page: int = 1
    per_page: int = 100

class GeneEvidenceCreate(BaseModel):
    """Schema for creating gene evidence"""

    gene_id: int
    source_name: str
    source_detail: str | None = None
    evidence_data: dict[str, Any]
    evidence_date: datetime | None = None

class GeneCurationSummary(BaseModel):
    """Summary of gene curation"""

    gene_id: int
    gene_symbol: str
    evidence_count: int = 0
    source_count: int = 0
    evidence_score: float | None = None
    classification: str | None = None
    panelapp_panels: list[str] = []
    hpo_terms: list[str] = []

    class Config:
        from_attributes = True
