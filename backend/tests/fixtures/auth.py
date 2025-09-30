"""
Authentication fixtures for testing user-related functionality.
"""

import pytest
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User


@pytest.fixture
def test_user(db_session: Session) -> User:
    """
    Create a basic test user for authentication tests.
    """
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        role="public",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """
    Create an admin user for testing admin-only endpoints.
    """
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def curator_user(db_session: Session) -> User:
    """
    Create a curator user for testing curator-level access.
    """
    user = User(
        username="curator",
        email="curator@example.com",
        hashed_password=get_password_hash("curatorpass123"),
        role="curator",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inactive_user(db_session: Session) -> User:
    """
    Create an inactive user for testing access restrictions.
    """
    user = User(
        username="inactive",
        email="inactive@example.com",
        hashed_password=get_password_hash("inactivepass123"),
        role="public",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def multiple_users(db_session: Session) -> list[User]:
    """
    Create multiple users for testing pagination and filtering.
    """
    users = []
    for i in range(10):
        user = User(
            username=f"user{i}",
            email=f"user{i}@example.com",
            hashed_password=get_password_hash(f"password{i}"),
            role="public" if i % 3 != 0 else "curator",
            is_active=i % 4 != 0,  # Every 4th user is inactive
        )
        users.append(user)
        db_session.add(user)

    db_session.commit()

    # Refresh all users to get database-generated fields
    for user in users:
        db_session.refresh(user)

    return users
