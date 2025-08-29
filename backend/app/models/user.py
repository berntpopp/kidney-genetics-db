"""
User model for authentication
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User model with comprehensive authentication fields"""

    __tablename__ = "users"

    # Primary fields
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)

    # Role and permissions
    role = Column(String(20), default="viewer", nullable=False, index=True)  # admin, curator, viewer
    permissions = Column(JSON, nullable=True)  # Computed from role

    # Account status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False)  # Legacy field, kept for compatibility

    # Login tracking
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    # Token fields
    refresh_token = Column(Text, nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    email_verification_token = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<User(username='{self.username}', email='{self.email}', role='{self.role}')>"

    def get_permissions(self) -> list[str]:
        """Get user permissions based on role"""
        role_permissions = {
            "admin": [
                "users:read", "users:write", "users:delete",
                "genes:read", "genes:write", "genes:delete",
                "annotations:read", "annotations:write", "annotations:delete",
                "ingestion:run", "cache:manage", "logs:read", "system:manage"
            ],
            "curator": [
                "genes:read", "genes:write",
                "annotations:read", "annotations:write",
                "ingestion:run"
            ],
            "viewer": [
                "genes:read", "annotations:read"
            ]
        }
        return role_permissions.get(self.role, [])
