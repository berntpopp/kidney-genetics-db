"""System settings model for runtime configuration management"""

import enum
import re

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import relationship, validates

from app.models.base import Base, TimestampMixin


class SettingType(str, enum.Enum):
    """Setting value type enum"""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"


class SettingCategory(str, enum.Enum):
    """Setting category enum"""

    CACHE = "cache"
    SECURITY = "security"
    PIPELINE = "pipeline"
    API = "api"
    DATABASE = "database"
    BACKUP = "backup"
    LOGGING = "logging"
    FEATURES = "features"


class SystemSetting(Base, TimestampMixin):
    """System setting model with comprehensive metadata"""

    __tablename__ = "system_settings"

    id = Column(BigInteger, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSONB, nullable=False)
    # CRITICAL: values_callable ensures PostgreSQL enum uses VALUES ("string") not NAMES (STRING)
    # Without this, SQLAlchemy creates enum as ('STRING', 'NUMBER', ...) instead of ('string', 'number', ...)
    # This caused LookupError during queries before fix - see issue #4 testing phase
    value_type = Column(
        ENUM(SettingType, values_callable=lambda x: [e.value for e in x], name="setting_type"),
        nullable=False,
    )
    category = Column(
        ENUM(
            SettingCategory, values_callable=lambda x: [e.value for e in x], name="setting_category"
        ),
        nullable=False,
        index=True,
    )
    description = Column(Text)
    default_value = Column(JSONB, nullable=False)
    requires_restart = Column(Boolean, default=False, nullable=False)
    validation_schema = Column(JSONB)
    is_sensitive = Column(Boolean, default=False, nullable=False)
    is_readonly = Column(Boolean, default=False, nullable=False)
    updated_by_id = Column(BigInteger, ForeignKey("users.id"))

    # Relationships
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    audit_logs = relationship(
        "SettingAuditLog", back_populates="setting", cascade="all, delete-orphan"
    )

    @validates("key")
    def validate_key(self, key: str, value: str) -> str:
        """Validate setting key format - lowercase alphanumeric + dots + underscores"""
        if not re.match(r"^[a-z][a-z0-9_.]*$", value):
            raise ValueError(
                f"Invalid setting key format: {value}. "
                f"Must start with lowercase letter and contain only "
                f"lowercase letters, numbers, dots, and underscores."
            )
        return value

    def __repr__(self) -> str:
        return f"<SystemSetting(key='{self.key}', category='{self.category}')>"


class SettingAuditLog(Base):
    """Audit log for setting changes (sensitive data masked)"""

    __tablename__ = "setting_audit_log"

    id = Column(BigInteger, primary_key=True)
    setting_id = Column(BigInteger, ForeignKey("system_settings.id", ondelete="CASCADE"))
    setting_key = Column(String(100), nullable=False)
    old_value = Column(JSONB)  # Masked if sensitive
    new_value = Column(JSONB, nullable=False)  # Masked if sensitive
    changed_by_id = Column(BigInteger, ForeignKey("users.id"))
    changed_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    change_reason = Column(Text)

    # Relationships
    setting = relationship("SystemSetting", back_populates="audit_logs")
    changed_by = relationship("User", foreign_keys=[changed_by_id])

    def __repr__(self) -> str:
        return (
            f"<SettingAuditLog(setting_key='{self.setting_key}', changed_at='{self.changed_at}')>"
        )
