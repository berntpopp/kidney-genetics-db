"""
Database models for static source management
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base


class StaticSource(Base):
    """Static data sources configuration"""

    __tablename__ = "static_sources"

    id = Column(BigInteger, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_name = Column(String(255), unique=True, nullable=False)  # This is unique in DB
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source_metadata = Column(JSONB, nullable=True)
    scoring_metadata = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True, nullable=True, index=True)  # nullable=True in DB
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # No timezone in DB
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )  # No timezone in DB

    # Relationships
    audit_logs = relationship(
        "StaticSourceAudit", back_populates="source", cascade="all, delete-orphan"
    )
    uploads = relationship(
        "StaticEvidenceUpload", back_populates="source", cascade="all, delete-orphan"
    )


class StaticSourceAudit(Base):
    """Audit log for static source operations"""

    __tablename__ = "static_source_audit"

    id = Column(BigInteger, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("static_sources.id"), nullable=False, index=True)
    upload_id = Column(Integer, nullable=True)
    action = Column(String(50), nullable=False)  # Matches 'action' column in DB
    details = Column(JSONB, nullable=True)
    performed_by = Column(String(255), nullable=True)
    performed_at = Column(DateTime, nullable=True)  # No timezone in DB

    # Relationships
    source = relationship("StaticSource", back_populates="audit_logs")


class StaticEvidenceUpload(Base):
    """Track uploaded evidence files"""

    __tablename__ = "static_evidence_uploads"

    id = Column(BigInteger, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("static_sources.id"), nullable=False, index=True)
    evidence_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash
    original_filename = Column(String(255), nullable=True)
    content_type = Column(String(50), nullable=True)
    upload_status = Column(String(50), nullable=True, index=True)
    processing_log = Column(JSONB, nullable=True)
    gene_count = Column(Integer, nullable=True)
    genes_normalized = Column(Integer, nullable=True)
    genes_failed = Column(Integer, nullable=True)
    genes_staged = Column(Integer, nullable=True)
    upload_metadata = Column(JSONB, nullable=True)
    processed_at = Column(DateTime, nullable=True)  # No timezone in DB
    uploaded_by = Column(String(255), nullable=True)  # nullable=True in DB
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)  # No timezone in DB
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )  # No timezone in DB

    # Relationships
    source = relationship("StaticSource", back_populates="uploads")
