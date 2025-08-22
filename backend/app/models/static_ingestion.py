"""
Static content ingestion models
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class StaticSource(Base, TimestampMixin):
    """Static evidence source configuration"""

    __tablename__ = "static_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    source_metadata = Column(JSONB, default={})
    scoring_metadata = Column(JSONB, nullable=False, default={"type": "count", "weight": 0.5})
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(String(255))

    # Cached statistics for performance
    cached_upload_count = Column(Integer, default=0)
    cached_total_genes = Column(Integer, default=0)

    # Relationships
    uploads = relationship("StaticEvidenceUpload", back_populates="source", cascade="all, delete-orphan")
    audit_logs = relationship("StaticSourceAudit", back_populates="source", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StaticSource(name='{self.source_name}', type='{self.source_type}')>"


class StaticEvidenceUpload(Base, TimestampMixin):
    """Track evidence file uploads"""

    __tablename__ = "static_evidence_uploads"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("static_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    original_filename = Column(String(255))
    content_type = Column(String(50))
    upload_status = Column(String(50), default="pending", index=True)
    processing_log = Column(JSONB, default={})
    gene_count = Column(Integer)
    genes_normalized = Column(Integer)
    genes_failed = Column(Integer)
    genes_staged = Column(Integer)
    upload_metadata = Column(JSONB, default={})
    processed_at = Column(DateTime(timezone=True))
    uploaded_by = Column(String(255))

    # Relationships
    source = relationship("StaticSource", back_populates="uploads")

    def __repr__(self):
        return f"<StaticEvidenceUpload(source_id={self.source_id}, evidence='{self.evidence_name}')>"


class StaticSourceAudit(Base):
    """Audit trail for static source operations"""

    __tablename__ = "static_source_audit"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("static_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey("static_evidence_uploads.id", ondelete="CASCADE"))
    action = Column(String(50), nullable=False)
    details = Column(JSONB, default={})
    performed_by = Column(String(255))
    performed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source = relationship("StaticSource", back_populates="audit_logs")

    def __repr__(self):
        return f"<StaticSourceAudit(source_id={self.source_id}, action='{self.action}')>"

