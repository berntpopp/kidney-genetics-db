"""
Gene annotation models for storing external database annotations.

This module defines models for storing gene annotations from various sources
like HGNC, gnomAD, ClinVar, etc. Uses a flexible JSONB schema for extensibility.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class GeneAnnotation(Base, TimestampMixin):
    """
    Store gene annotations from various external sources.

    Uses JSONB for flexible, evolving annotation data while maintaining
    relational integrity with the genes table.
    """

    __tablename__ = "gene_annotations"
    __table_args__ = (
        UniqueConstraint("gene_id", "source", "version", name="unique_gene_source_version"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    gene_id = Column(
        BigInteger, ForeignKey("genes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source = Column(String(50), nullable=False, index=True)
    version = Column(String(20))
    annotations = Column(JSONB, nullable=False)
    source_metadata = Column(JSONB)

    # Relationships
    gene = relationship("Gene", back_populates="annotations")

    def __repr__(self) -> str:
        return (
            f"<GeneAnnotation(gene_id={self.gene_id}, "
            f"source='{self.source}', version='{self.version}')>"
        )

    def get_annotation_value(self, key: str, default: Any = None) -> Any:
        """
        Safely get a value from the annotations JSONB field.

        Args:
            key: Dot-separated path to the value (e.g., 'constraint.pli')
            default: Default value if key not found

        Returns:
            The value at the specified path or default
        """
        if not self.annotations:
            return default

        keys = key.split(".")
        value = self.annotations

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value


class AnnotationSource(Base, TimestampMixin):
    """
    Tracks available annotation sources.
    Extended with fields needed by the annotation pipeline.
    """

    __tablename__ = "annotation_sources"

    id = Column(BigInteger, primary_key=True, index=True)
    source_name = Column(Text, unique=True, nullable=False)
    display_name = Column(Text, nullable=False)
    version = Column(Text, nullable=False, default="1.0")
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    base_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    update_frequency = Column(Text, nullable=True)  # e.g., "daily", "weekly", "quarterly"
    last_update = Column(DateTime(timezone=True), nullable=True)
    next_update = Column(DateTime(timezone=True), nullable=True)
    config = Column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def is_update_due(self) -> bool:
        """Check if this source needs updating based on next_update time."""
        if not self.next_update:
            return True
        return datetime.now(timezone.utc) >= self.next_update


class AnnotationHistory(Base):
    """
    Audit trail for annotation changes.

    Tracks all modifications to gene annotations for reproducibility
    and debugging.
    """

    __tablename__ = "annotation_history"

    id = Column(BigInteger, primary_key=True, index=True)
    gene_id = Column(BigInteger, ForeignKey("genes.id"), index=True)
    source = Column(String(50), index=True)
    operation = Column(String(20))  # 'insert', 'update', 'delete'
    old_data = Column(JSONB)
    new_data = Column(JSONB)
    changed_by = Column(String(100))
    changed_at = Column(DateTime, default=datetime.utcnow)
    change_reason = Column(Text)

    def __repr__(self) -> str:
        return (
            f"<AnnotationHistory(gene_id={self.gene_id}, "
            f"source='{self.source}', operation='{self.operation}')>"
        )
