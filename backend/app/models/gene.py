"""
Gene and related models
"""
from sqlalchemy import (
    Column, Integer, String, Text, Float, Date, 
    ForeignKey, UniqueConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Gene(Base, TimestampMixin):
    """Gene master table"""
    
    __tablename__ = "genes"
    
    id = Column(Integer, primary_key=True, index=True)
    hgnc_id = Column(String(50), unique=True, index=True)
    approved_symbol = Column(String(100), nullable=False, index=True)
    aliases = Column(ARRAY(Text))
    
    # Relationships
    evidence = relationship("GeneEvidence", back_populates="gene", cascade="all, delete-orphan")
    curation = relationship("GeneCuration", back_populates="gene", uselist=False)
    
    def __repr__(self):
        return f"<Gene(symbol='{self.approved_symbol}', hgnc_id='{self.hgnc_id}')>"


class GeneEvidence(Base, TimestampMixin):
    """Evidence for genes from various sources"""
    
    __tablename__ = "gene_evidence"
    __table_args__ = (
        UniqueConstraint('gene_id', 'source_name', 'source_detail', 
                        name='gene_evidence_source_idx'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    gene_id = Column(Integer, ForeignKey("genes.id", ondelete="CASCADE"), nullable=False)
    source_name = Column(String(100), nullable=False, index=True)
    source_detail = Column(String(255))
    evidence_data = Column(JSONB, nullable=False)
    evidence_date = Column(Date)
    
    # Relationships
    gene = relationship("Gene", back_populates="evidence")
    
    def __repr__(self):
        return f"<GeneEvidence(gene_id={self.gene_id}, source='{self.source_name}')>"


class GeneCuration(Base, TimestampMixin):
    """Final curated gene list with aggregated evidence"""
    
    __tablename__ = "gene_curations"
    
    id = Column(Integer, primary_key=True, index=True)
    gene_id = Column(Integer, ForeignKey("genes.id"), unique=True, nullable=False)
    
    # Evidence counts
    evidence_count = Column(Integer, default=0)
    source_count = Column(Integer, default=0)
    
    # Core kidney genetics fields
    panelapp_panels = Column(ARRAY(Text))
    literature_refs = Column(ARRAY(Text))
    diagnostic_panels = Column(ARRAY(Text))
    hpo_terms = Column(ARRAY(Text))
    pubtator_pmids = Column(ARRAY(Text))
    
    # Annotations as JSONB
    omim_data = Column(JSONB)
    clinvar_data = Column(JSONB)
    constraint_scores = Column(JSONB)
    expression_data = Column(JSONB)
    
    # Summary scores
    evidence_score = Column(Float, index=True)
    classification = Column(String(50))
    
    # Relationships
    gene = relationship("Gene", back_populates="curation")
    
    def __repr__(self):
        return f"<GeneCuration(gene_id={self.gene_id}, score={self.evidence_score})>"


class PipelineRun(Base, TimestampMixin):
    """Track pipeline execution history"""
    
    __tablename__ = "pipeline_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(50), default="running")
    started_at = Column(JSONB)
    completed_at = Column(JSONB)
    stats = Column(JSONB)
    error_log = Column(Text)
    
    def __repr__(self):
        return f"<PipelineRun(id={self.id}, status='{self.status}')>"