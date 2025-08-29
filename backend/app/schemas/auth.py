"""
Authentication schemas for request/response validation
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = Field(description="Token expiration time in seconds")


class TokenData(BaseModel):
    """JWT token payload data"""
    username: str | None = None
    sub: str
    role: str = "viewer"
    permissions: list[str] = []
    exp: int
    type: str = "access"


class UserLogin(BaseModel):
    """User login request"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class UserRegister(BaseModel):
    """User registration request (admin only)"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8)
    full_name: str | None = Field(None, max_length=255)
    role: str = Field("viewer", pattern="^(admin|curator|viewer)$")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if v.lower() in ["admin", "root", "administrator", "system"]:
            raise ValueError("Reserved username")
        return v


class UserResponse(BaseModel):
    """User response (public data)"""
    id: int
    email: str
    username: str
    full_name: str | None = None
    role: str
    permissions: list[str]
    is_active: bool
    is_verified: bool
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update request (admin only)"""
    email: EmailStr | None = None
    full_name: str | None = Field(None, max_length=255)
    role: str | None = Field(None, pattern="^(admin|curator|viewer)$")
    is_active: bool | None = None
    is_verified: bool | None = None


class PasswordReset(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8)


class PasswordChange(BaseModel):
    """Password change request (for logged-in users)"""
    current_password: str
    new_password: str = Field(..., min_length=8)


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str
