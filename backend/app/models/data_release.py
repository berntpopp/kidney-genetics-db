"""
Data Release model for CalVer versioned data snapshots
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class DataRelease(Base, TimestampMixin):
    """
    CalVer-versioned data releases for research reproducibility.

    Provides point-in-time snapshots of gene data with:
    - CalVer versioning (YYYY.MM format)
    - Export files with SHA256 checksums
    - DOI support for citability
    - Temporal database queries for historical data
    """

    __tablename__ = "data_releases"

    # Primary fields
    id = Column(BigInteger, primary_key=True, index=True)
    version = Column(String(20), unique=True, nullable=False, index=True)  # "2025.10"
    release_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="draft", nullable=False, index=True)  # draft, published

    # Metadata
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    # Statistics
    gene_count = Column(Integer, nullable=True)
    total_evidence_count = Column(Integer, nullable=True)

    # Export
    export_file_path = Column(String(500), nullable=True)
    export_checksum = Column(String(64), nullable=True)  # SHA256

    # Citation
    doi = Column(String(100), nullable=True)  # Optional Zenodo DOI
    citation_text = Column(Text, nullable=True)

    # Notes
    release_notes = Column(Text, nullable=True)

    # Relationships
    published_by = relationship("User", foreign_keys=[published_by_id])

    def __repr__(self) -> str:
        return f"<DataRelease(version='{self.version}', status='{self.status}')>"
