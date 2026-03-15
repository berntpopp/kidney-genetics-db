"""
Database models for static source management
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class StaticSource(Base):
    """Static data sources configuration"""

    __tablename__ = "static_sources"

    id = Column(BigInteger, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_name = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source_metadata = Column(JSONB, nullable=True)
    scoring_metadata = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

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
    source_id = Column(
        BigInteger,
        ForeignKey("static_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(String(50), nullable=False)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changes = Column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    performed_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now())

    # Relationships
    source = relationship("StaticSource", back_populates="audit_logs")


class StaticEvidenceUpload(Base):
    """Track uploaded evidence files"""

    __tablename__ = "static_evidence_uploads"

    id = Column(BigInteger, primary_key=True, index=True)
    source_id = Column(
        BigInteger,
        ForeignKey("static_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    evidence_name = Column(String(255), nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)
    original_filename = Column(String(255), nullable=True)
    content_type = Column(String(50), nullable=True)
    upload_status = Column(String(50), nullable=True, index=True)
    processing_log = Column(JSONB, nullable=True)
    gene_count = Column(Integer, nullable=True)
    genes_normalized = Column(Integer, nullable=True)
    genes_failed = Column(Integer, nullable=True)
    genes_staged = Column(Integer, nullable=True)
    upload_metadata = Column(JSONB, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_by = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    source = relationship("StaticSource", back_populates="uploads")
