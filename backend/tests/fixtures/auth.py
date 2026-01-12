"""
Authentication fixtures for testing user-related functionality.

These fixtures use a "get or create" pattern to work with existing development
databases that may already have users with standard usernames like 'admin'.
"""

import pytest
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User


def get_or_create_user(
    db_session: Session,
    username: str,
    email: str,
    password: str,
    role: str,
    is_active: bool = True,
) -> User:
    """
    Get an existing user by username or create a new one.

    This helper function allows tests to work with existing development databases
    that may already have users with standard usernames (e.g., 'admin').
    """
    existing_user = db_session.query(User).filter(User.username == username).first()
    if existing_user:
        # Update the existing user to match expected test state
        existing_user.email = email
        existing_user.hashed_password = get_password_hash(password)
        existing_user.role = role
        existing_user.is_active = is_active
        db_session.commit()
        db_session.refresh(existing_user)
        return existing_user

    # Create new user if not found
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user(db_session: Session) -> User:
    """
    Create a basic test user for authentication tests.
    """
    return get_or_create_user(
        db_session,
        username="testuser",
        email="test@example.com",
        password="testpass123",
        role="public",
        is_active=True,
    )


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """
    Create an admin user for testing admin-only endpoints.
    """
    return get_or_create_user(
        db_session,
        username="admin",
        email="admin@example.com",
        password="adminpass123",
        role="admin",
        is_active=True,
    )


@pytest.fixture
def curator_user(db_session: Session) -> User:
    """
    Create a curator user for testing curator-level access.
    """
    return get_or_create_user(
        db_session,
        username="curator",
        email="curator@example.com",
        password="curatorpass123",
        role="curator",
        is_active=True,
    )


@pytest.fixture
def inactive_user(db_session: Session) -> User:
    """
    Create an inactive user for testing access restrictions.
    """
    return get_or_create_user(
        db_session,
        username="inactive",
        email="inactive@example.com",
        password="inactivepass123",
        role="public",
        is_active=False,
    )


@pytest.fixture
def multiple_users(db_session: Session) -> list[User]:
    """
    Create multiple users for testing pagination and filtering.
    Uses unique test-prefixed usernames to avoid conflicts.
    """
    users = []
    for i in range(10):
        user = get_or_create_user(
            db_session,
            username=f"test_user_{i}",
            email=f"test_user_{i}@example.com",
            password=f"password{i}",
            role="public" if i % 3 != 0 else "curator",
            is_active=i % 4 != 0,  # Every 4th user is inactive
        )
        users.append(user)

    return users
