"""System logging models for database persistence."""

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class SystemLog(Base):
    """System log entry for audit and debugging."""

    __tablename__ = "system_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    level = Column(Text, nullable=False)
    logger = Column(Text, nullable=False)  # Changed from logger_name
    message = Column(Text, nullable=False)
    context = Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)  # Changed from extra_data

    # Request context
    request_id = Column(Text, nullable=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ip_address = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    path = Column(Text, nullable=True)  # Changed from endpoint
    method = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Float, nullable=True)  # Changed from processing_time_ms

    # Error information
    error_type = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)  # Changed from error_traceback
    stack_trace = Column(Text, nullable=True)  # New field

    # Relationships
    user = relationship("User", back_populates="logs")

    def __repr__(self) -> str:
        return f"<SystemLog {self.id}: {self.level} - {self.message[:50]}>"
