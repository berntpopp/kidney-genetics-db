"""Schema version tracking model for database migrations."""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import Base


class SchemaVersion(Base):
    """Database schema version tracking for migration history."""

    __tablename__ = "schema_versions"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(20), unique=True, nullable=False)  # Semantic version (e.g., 0.1.0)
    alembic_revision = Column(String(50), nullable=False)  # Alembic migration revision ID
    description = Column(Text, nullable=True)  # Human-readable description of changes
    applied_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )  # Timestamp when version was applied

    def __repr__(self) -> str:
        return f"<SchemaVersion(version='{self.version}', revision='{self.alembic_revision}')>"
