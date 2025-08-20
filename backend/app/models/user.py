"""
User model for authentication
"""

from sqlalchemy import Boolean, Column, Integer, String

from app.models.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    """User model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<User(email='{self.email}', is_admin={self.is_admin})>"
