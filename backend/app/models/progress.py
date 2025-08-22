"""
SQLAlchemy models for data source progress tracking
"""

from enum import Enum as PyEnum

from sqlalchemy import JSON, Column, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class SourceStatus(PyEnum):
    """Enumeration for data source status"""

    idle = "idle"
    running = "running"
    completed = "completed"
    failed = "failed"
    paused = "paused"

class DataSourceProgress(Base):
    """Model for tracking data source update progress"""

    __tablename__ = "data_source_progress"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String, unique=True, nullable=False, index=True)
    status = Column(
        Enum(SourceStatus, native_enum=True, name="source_status"),
        nullable=False,
        default=SourceStatus.idle,
    )

    # Progress tracking
    current_page = Column(Integer, default=0)
    total_pages = Column(Integer, nullable=True)
    current_item = Column(Integer, default=0)
    total_items = Column(Integer, nullable=True)
    items_processed = Column(Integer, default=0)
    items_added = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)

    # Status information
    current_operation = Column(String, nullable=True)
    last_error = Column(Text, nullable=True)
    progress_metadata = Column("metadata", JSON, default={})

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_update_at = Column(DateTime(timezone=True), server_default=func.now())
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "source_name": self.source_name,
            "status": self.status.value if isinstance(self.status, SourceStatus) else self.status,
            "progress_percentage": round(self.progress_percentage, 2),
            "current_operation": self.current_operation,
            "items_processed": self.items_processed,
            "items_added": self.items_added,
            "items_updated": self.items_updated,
            "items_failed": self.items_failed,
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "current_item": self.current_item,
            "total_items": self.total_items,
            "last_error": self.last_error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_update_at": self.last_update_at.isoformat() if self.last_update_at else None,
            "estimated_completion": self.estimated_completion.isoformat()
            if self.estimated_completion
            else None,
            "metadata": self.progress_metadata or {},
        }
