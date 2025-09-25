"""
FastAPI dependencies for authentication and authorization
"""

from fastapi import Depends, HTTPException, status

from app.api.endpoints.auth import get_current_user, get_current_user_optional
from app.models.user import User

# Role-based dependencies


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Require admin role for endpoint access.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_curator(current_user: User = Depends(get_current_user)) -> User:
    """
    Require curator role or higher for endpoint access.
    """
    if current_user.role not in ["admin", "curator"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Curator access required")
    return current_user


def require_any_role(*roles: str):
    """
    Factory function to require any of the specified roles.
    """

    def check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(roles)}",
            )
        return current_user

    return check_role


# Permission-based dependencies


def require_permission(permission: str):
    """
    Factory function to require a specific permission.
    """

    def check_permission(current_user: User = Depends(get_current_user)) -> User:
        user_permissions = current_user.get_permissions()
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission required: {permission}"
            )
        return current_user

    return check_permission


def require_any_permission(*permissions: str):
    """
    Factory function to require any of the specified permissions.
    """

    def check_permissions(current_user: User = Depends(get_current_user)) -> User:
        user_permissions = current_user.get_permissions()
        if not any(perm in user_permissions for perm in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these permissions required: {', '.join(permissions)}",
            )
        return current_user

    return check_permissions


# Optional authentication dependency (for public endpoints that may benefit from auth)


def get_optional_user(
    current_user: User | None = Depends(get_current_user_optional),
) -> User | None:
    """
    Get current user if authenticated, None otherwise.
    Useful for endpoints that are public but can provide additional features for authenticated users.
    """
    return current_user


# Export commonly used dependencies for convenience
__all__ = [
    "require_admin",
    "require_curator",
    "require_any_role",
    "require_permission",
    "require_any_permission",
    "get_optional_user",
    "get_current_user",
    "get_current_user_optional",
]
