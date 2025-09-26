"""
Cache model for database-backed caching
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class CacheEntry(Base):
    """Database cache entry model."""

    __tablename__ = "cache_entries"

    # Fix: Database has INTEGER id, not UUID
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True
    )
    # Fix: Database has VARCHAR(255), but we can safely use Text in model
    cache_key: Mapped[str] = mapped_column(Text, nullable=False)
    namespace: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    access_count: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    data_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, server_default="{}", nullable=False)

    __table_args__ = (
        UniqueConstraint("cache_key", name="uq_cache_entries_cache_key"),
        Index("idx_cache_entries_namespace", "namespace"),
        Index(
            "idx_cache_entries_expires_at", "expires_at", postgresql_where="expires_at IS NOT NULL"
        ),
        Index("idx_cache_entries_last_accessed", "last_accessed"),
        Index("idx_cache_entries_namespace_key", "namespace", "cache_key"),
    )
