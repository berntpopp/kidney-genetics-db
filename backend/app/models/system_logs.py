"""
Database model for system logs table
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSON

from app.models.base import Base


class SystemLog(Base):
    """System logs table for structured logging"""

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)  # No timezone in DB
    level = Column(String(20), nullable=False)  # VARCHAR(20) in DB
    message = Column(Text, nullable=False)
    source = Column(String(100), nullable=True)  # Nullable in DB
    request_id = Column(String(100), nullable=True)  # VARCHAR(100) in DB
    endpoint = Column(String(200), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    extra_data = Column(JSON, nullable=True)  # JSON not JSONB in DB
    error_type = Column(String(100), nullable=True)
    error_traceback = Column(Text, nullable=True)

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_system_logs_timestamp_desc', timestamp.desc()),
        Index('idx_system_logs_timestamp_level', timestamp.desc(), level),
        Index('idx_system_logs_level', level),
        Index('idx_system_logs_source', source),
        Index('idx_system_logs_request_id', request_id),
        Index('idx_system_logs_error_type', error_type),
    )