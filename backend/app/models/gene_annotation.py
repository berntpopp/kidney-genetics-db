"""
Gene annotation models for storing external database annotations.

This module defines models for storing gene annotations from various sources
like HGNC, gnomAD, ClinVar, etc. Uses a flexible JSONB schema for extensibility.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

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

    id = Column(Integer, primary_key=True, index=True)
    gene_id = Column(
        Integer, ForeignKey("genes.id", ondelete="CASCADE"), nullable=False, index=True
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
    Registry of annotation sources and their configuration.

    Tracks available annotation sources, update schedules, and metadata.
    """

    __tablename__ = "annotation_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100))
    description = Column(Text)
    base_url = Column(String(255))
    update_frequency = Column(String(50))  # 'daily', 'weekly', 'monthly'
    last_update = Column(DateTime)
    next_update = Column(DateTime)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher = more important
    config = Column(JSONB)  # Source-specific configuration

    def __repr__(self) -> str:
        return f"<AnnotationSource(name='{self.source_name}', active={self.is_active})>"

    def is_update_due(self) -> bool:
        """Check if this source needs updating."""
        if not self.next_update:
            return True
        return datetime.utcnow() >= self.next_update


class AnnotationHistory(Base):
    """
    Audit trail for annotation changes.

    Tracks all modifications to gene annotations for reproducibility
    and debugging.
    """

    __tablename__ = "annotation_history"

    id = Column(Integer, primary_key=True, index=True)
    gene_id = Column(Integer, ForeignKey("genes.id"), index=True)
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
