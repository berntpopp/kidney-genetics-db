"""
Database models for gene normalization staging
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class GeneNormalizationStaging(Base):
    """
    Staging table for genes that couldn't be automatically normalized
    and require manual review before entering the main database
    """

    __tablename__ = "gene_normalization_staging"

    id = Column(BigInteger, primary_key=True, index=True)

    # Original gene information
    original_text = Column(String, nullable=False, index=True)
    source_name = Column(String, nullable=False, index=True)
    original_data = Column(JSONB, nullable=True)  # Full context from data source

    # Normalization attempt details
    normalization_log = Column(JSONB, nullable=False)  # Detailed log of normalization attempts

    # Review status
    status = Column(String, nullable=False, default="pending_review", index=True)
    # Possible values: pending_review, in_review, approved, rejected, duplicate

    # Manual review fields
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    # Manual correction fields
    manual_approved_symbol = Column(String, nullable=True)
    manual_hgnc_id = Column(String, nullable=True)
    manual_aliases = Column(JSONB, nullable=True)  # List of alias symbols

    # Resolution tracking
    resolved_gene_id = Column(BigInteger, nullable=True)  # FK to genes table when resolved
    resolution_method = Column(String, nullable=True)
    # Values: automatic_retry, manual_correction, merged_with_existing, rejected_invalid

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Priority scoring (higher = more important to review)
    priority_score = Column(Integer, default=0, nullable=False, index=True)

    # Flags
    requires_expert_review = Column(Boolean, default=False, nullable=False)
    is_duplicate_submission = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<GeneNormalizationStaging(id={self.id}, original_text='{self.original_text}', source='{self.source_name}', status='{self.status}')>"


class GeneNormalizationLog(Base):
    """
    Complete log of all gene normalization attempts for audit trail
    """

    __tablename__ = "gene_normalization_log"

    id = Column(BigInteger, primary_key=True, index=True)

    # Gene information
    original_text = Column(String, nullable=False, index=True)
    source_name = Column(String, nullable=False, index=True)

    # Normalization result
    success = Column(Boolean, nullable=False, index=True)
    approved_symbol = Column(String, nullable=True, index=True)
    hgnc_id = Column(String, nullable=True, index=True)

    # Detailed logs
    normalization_log = Column(JSONB, nullable=False)

    # Outcome tracking
    final_gene_id = Column(BigInteger, nullable=True)  # FK to genes table if successful
    staging_id = Column(BigInteger, nullable=True)  # FK to staging table if manual review needed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Performance tracking
    api_calls_made = Column(Integer, default=0, nullable=False)
    processing_time_ms = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<GeneNormalizationLog(id={self.id}, original_text='{self.original_text}', success={self.success})>"
