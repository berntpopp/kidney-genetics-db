"""
Backup job model for database backup tracking
"""

import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class BackupStatus(str, enum.Enum):
    """Backup job status enum"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RESTORED = "restored"


class BackupTrigger(str, enum.Enum):
    """Backup trigger source enum"""

    MANUAL_API = "manual_api"
    SCHEDULED_CRON = "scheduled_cron"
    PRE_RESTORE_SAFETY = "pre_restore_safety"


class BackupJob(Base, TimestampMixin):
    """Backup job model with comprehensive tracking fields"""

    __tablename__ = "backup_jobs"

    # Primary fields
    id = Column(BigInteger, primary_key=True, index=True)

    # Backup metadata
    filename = Column(String(500), unique=True, nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)

    # Backup options
    format = Column(String(20), default="custom", nullable=True)
    compression_level = Column(SmallInteger, default=6, nullable=True)
    include_logs = Column(Boolean, default=False, nullable=True)
    include_cache = Column(Boolean, default=False, nullable=True)
    parallel_jobs = Column(SmallInteger, default=1, nullable=True)

    # Status tracking
    # CRITICAL: values_callable ensures PostgreSQL enum uses VALUES ("pending") not NAMES (PENDING)
    # Without this, SQLAlchemy creates enum as ('PENDING', ...) instead of ('pending', ...)
    # which causes 503 errors when querying the backup service.
    status = Column(
        ENUM(
            BackupStatus,
            values_callable=lambda x: [e.value for e in x],
            name="backup_status",
            create_type=False,
        ),
        default=BackupStatus.PENDING,
        nullable=True,
    )
    trigger_source = Column(
        ENUM(
            BackupTrigger,
            values_callable=lambda x: [e.value for e in x],
            name="backup_trigger",
            create_type=False,
        ),
        default=BackupTrigger.MANUAL_API,
        nullable=True,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # User attribution
    created_by_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)

    # Statistics
    database_size_bytes = Column(BigInteger, nullable=True)
    tables_count = Column(Integer, nullable=True)

    # Timestamps inherited from TimestampMixin: created_at, updated_at
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Notes
    description = Column(Text, nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self) -> str:
        return f"<BackupJob(id={self.id}, filename='{self.filename}', status='{self.status}')>"
