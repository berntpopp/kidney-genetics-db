"""
Authentication endpoints for user login, registration, and token management
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_email_verification_token,
    generate_password_reset_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.auth import (
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
    RefreshTokenRequest,
    Token,
    UserRegister,
    UserResponse,
    UserUpdate,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# Dependency to get current user from token
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify token
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise credentials_exception

    # Get user from database
    username = payload.get("sub")
    if username is None or not isinstance(username, str):
        raise credentials_exception

    result = db.execute(select(User).where(User.username == username))
    user: User | None = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    # Check if account is locked (handle both naive and aware datetimes)
    if user.locked_until:
        now = datetime.now(timezone.utc)
        locked_until = user.locked_until
        # Make comparison work with naive datetimes from DB
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked until {user.locked_until}",
            )

    return user


# Optional dependency - returns None if no auth
async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User | None:
    """Get current user if authenticated, None otherwise"""
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


# PUBLIC ENDPOINTS


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Login with username/email and password.
    Returns access and refresh tokens.
    """
    # Try to find user by username or email
    result = db.execute(
        select(User).where(
            (User.username == form_data.username) | (User.email == form_data.username)
        )
    )
    user = result.scalar_one_or_none()

    # Check if user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Increment failed login attempts if user exists
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.ACCOUNT_LOCKOUT_MINUTES
                )
                await logger.warning(
                    "Account locked due to failed login attempts",
                    username=user.username,
                    attempts=user.failed_login_attempts,
                )
            db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is locked (handle both naive and aware datetimes)
    if user.locked_until:
        now = datetime.now(timezone.utc)
        locked_until = user.locked_until
        # Make comparison work with naive datetimes from DB
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked until {user.locked_until}",
            )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    # Check if email is verified (optional, can be disabled)
    # if not user.is_verified:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Please verify your email before logging in"
    #     )

    # Create tokens
    access_token = create_access_token(
        subject=user.username, role=user.role, permissions=user.get_permissions()
    )
    refresh_token = create_refresh_token(subject=user.username)

    # Update user login info
    user.last_login = datetime.now(timezone.utc)
    user.failed_login_attempts = 0
    user.locked_until = None
    user.refresh_token = refresh_token
    db.commit()

    await logger.info("User logged in successfully", username=user.username, role=user.role)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Refresh access token using refresh token.
    """
    # Verify refresh token
    payload = verify_token(request.refresh_token, token_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Get user
    username = payload.get("sub")
    result = db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or user.refresh_token != request.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    # Create new access token
    access_token = create_access_token(
        subject=user.username, role=user.role, permissions=user.get_permissions()
    )

    return {
        "access_token": access_token,
        "refresh_token": request.refresh_token,  # Keep same refresh token
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict[str, str]:
    """
    Logout current user (invalidate refresh token).
    """
    current_user.refresh_token = None
    db.commit()

    await logger.info("User logged out", username=current_user.username)

    return {"message": "Successfully logged out"}


@router.post("/forgot-password")
async def forgot_password(request: PasswordReset, db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Request password reset token.
    Always returns success to prevent email enumeration.
    """
    # Find user by email
    result = db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user and user.is_active:
        # Generate reset token
        reset_token = generate_password_reset_token()
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()

        # TODO: Send email with reset token
        # For now, log the token (remove in production!)
        await logger.info(
            "Password reset requested", email=request.email, token=reset_token[:8] + "..."
        )

    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    request: PasswordResetConfirm, db: Session = Depends(get_db)
) -> dict[str, str]:
    """
    Reset password using reset token.
    """
    # Find user by reset token
    result = db.execute(
        select(User).where(
            User.password_reset_token == request.token,
            User.password_reset_expires > datetime.now(timezone.utc),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        )

    # Validate new password
    is_valid, errors = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password validation failed: {', '.join(errors)}",
        )

    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    await logger.info("Password reset completed", username=user.username)

    return {"message": "Password has been reset successfully"}


# PROTECTED ENDPOINTS (Require authentication)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user information.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        permissions=current_user.get_permissions(),
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.post("/change-password")
async def change_password(
    request: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Change password for current user.
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password"
        )

    # Validate new password
    is_valid, errors = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password validation failed: {', '.join(errors)}",
        )

    # Update password
    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    await logger.info("Password changed", username=current_user.username)

    return {"message": "Password changed successfully"}


# ADMIN ENDPOINTS


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserRegister,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Register a new user (admin only).
    """
    # Check if current user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can register new users"
        )

    # Check if username already exists
    result = db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered"
        )

    # Check if email already exists
    result = db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Validate password
    is_valid, errors = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password validation failed: {', '.join(errors)}",
        )

    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
        is_verified=True,  # Admin-created users are pre-verified
        is_admin=(user_data.role == "admin"),
        email_verification_token=generate_email_verification_token(),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    await logger.info(
        "New user registered",
        username=new_user.username,
        role=new_user.role,
        registered_by=current_user.username,
    )

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        username=new_user.username,
        full_name=new_user.full_name,
        role=new_user.role,
        permissions=new_user.get_permissions(),
        is_active=new_user.is_active,
        is_verified=new_user.is_verified,
        last_login=new_user.last_login,
        created_at=new_user.created_at,
        updated_at=new_user.updated_at,
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[UserResponse]:
    """
    List all users (admin only).
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can list users"
        )

    result = db.execute(select(User))
    users = result.scalars().all()

    return [
        UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            permissions=user.get_permissions(),
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login=user.last_login,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        for user in users
    ]


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Update user information (admin only).
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update users"
        )

    # Get user to update
    result = db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Don't allow admin to remove their own admin role
    if user.id == current_user.id and user_update.role and user_update.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove your own admin role"
        )

    # Update fields if provided
    if user_update.email is not None:
        # Check if email already exists
        result = db.execute(select(User).where(User.email == user_update.email, User.id != user_id))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
            )
        user.email = user_update.email

    if user_update.full_name is not None:
        user.full_name = user_update.full_name

    if user_update.role is not None:
        user.role = user_update.role
        user.is_admin = user_update.role == "admin"

    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    if user_update.is_verified is not None:
        user.is_verified = user_update.is_verified

    db.commit()
    db.refresh(user)

    await logger.info("User updated", username=user.username, updated_by=current_user.username)

    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        permissions=user.get_permissions(),
        is_active=user.is_active,
        is_verified=user.is_verified,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict[str, str]:
    """
    Delete a user (admin only).
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete users"
        )

    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account"
        )

    # Get user to delete
    result = db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    username = user.username
    db.delete(user)
    db.commit()

    await logger.info("User deleted", username=username, deleted_by=current_user.username)

    return {"message": f"User {username} deleted successfully"}
