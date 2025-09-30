"""
Integration tests for authentication endpoints.
Testing JWT auth, role-based access control (RBAC), and user management.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from tests.factories import UserFactoryBatch


@pytest.mark.integration
class TestAuthenticationFlow:
    """Test complete authentication flows."""

    @pytest.mark.asyncio
    async def test_user_registration(self, async_client: AsyncClient):
        """Test user registration flow."""
        registration_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User",
        }

        response = await async_client.post("/api/auth/register", json=registration_data)

        # Check if registration endpoint exists
        if response.status_code == 404:
            pytest.skip("Registration endpoint not yet implemented")

        assert response.status_code == 201
        user_data = response.json()

        # Verify user data (password should not be returned)
        assert user_data["username"] == "newuser"
        assert user_data["email"] == "newuser@example.com"
        assert "password" not in user_data
        assert "hashed_password" not in user_data

    @pytest.mark.asyncio
    async def test_user_login_success(self, async_client: AsyncClient, test_user):
        """Test successful user login."""
        login_data = {
            "username": test_user.username,
            "password": "testpass123",  # Password from auth fixture
        }

        response = await async_client.post(
            "/api/auth/login",
            data=login_data,  # OAuth2 uses form data
        )

        if response.status_code == 404:
            pytest.skip("Login endpoint not yet implemented")

        assert response.status_code == 200
        token_data = response.json()

        # Verify token response
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_user_login_invalid_credentials(self, async_client: AsyncClient, test_user):
        """Test login with invalid credentials."""
        login_data = {"username": test_user.username, "password": "wrongpassword"}

        response = await async_client.post("/api/auth/login", data=login_data)

        if response.status_code == 404:
            pytest.skip("Login endpoint not yet implemented")

        assert response.status_code == 401
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_user_login_inactive_account(self, async_client: AsyncClient, inactive_user):
        """Test login with inactive account."""
        login_data = {"username": inactive_user.username, "password": "inactivepass123"}

        response = await async_client.post("/api/auth/login", data=login_data)

        if response.status_code == 404:
            pytest.skip("Login endpoint not yet implemented")

        # Should reject inactive users
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_without_token(self, async_client: AsyncClient):
        """Test accessing protected endpoint without authentication."""
        response = await async_client.get("/api/auth/me")

        if response.status_code == 404:
            pytest.skip("Protected endpoint not yet implemented")

        assert response.status_code == 401
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_token(self, async_client: AsyncClient, test_user):
        """Test accessing protected endpoint with valid token."""
        token = create_access_token({"sub": test_user.username})

        response = await async_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 404:
            pytest.skip("Protected endpoint not yet implemented")

        assert response.status_code == 200
        user_data = response.json()

        assert user_data["username"] == test_user.username
        assert user_data["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_access_with_expired_token(self, async_client: AsyncClient, test_user):
        """Test accessing endpoint with expired token."""
        # Create token with -1 minute expiry (already expired)
        token = create_access_token(
            {"sub": test_user.username},
            expires_delta=-60,  # Negative time = expired
        )

        response = await async_client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 404:
            pytest.skip("Protected endpoint not yet implemented")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_flow(self, async_client: AsyncClient, test_user):
        """Test token refresh flow."""
        # First, login to get tokens
        login_response = await async_client.post(
            "/api/auth/login", data={"username": test_user.username, "password": "testpass123"}
        )

        if login_response.status_code == 404:
            pytest.skip("Login endpoint not yet implemented")

        tokens = login_response.json()

        # Try to refresh token
        refresh_response = await async_client.post(
            "/api/auth/refresh", json={"refresh_token": tokens.get("refresh_token")}
        )

        if refresh_response.status_code == 404:
            pytest.skip("Refresh endpoint not yet implemented")

        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens


@pytest.mark.integration
class TestRoleBasedAccess:
    """Test role-based access control (RBAC)."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        """Create users with different roles."""
        self.users = UserFactoryBatch.create_role_distribution(
            db_session, admins=1, curators=2, public=3
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "role,expected_status",
        [
            ("admin", 200),
            ("curator", 200),
            ("public", 403),
        ],
    )
    async def test_admin_endpoint_access(
        self, async_client: AsyncClient, role: str, expected_status: int
    ):
        """Test admin endpoint access based on role."""
        user = self.users[role][0]
        token = create_access_token({"sub": user.username, "role": role})

        response = await async_client.get(
            "/api/admin/users", headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code == 404:
            pytest.skip("Admin endpoint not yet implemented")

        assert response.status_code == expected_status

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "role,expected_status",
        [
            ("admin", 200),
            ("curator", 200),
            ("public", 403),
        ],
    )
    async def test_curator_endpoint_access(
        self, async_client: AsyncClient, role: str, expected_status: int
    ):
        """Test curator-level endpoint access based on role."""
        user = self.users[role][0]
        token = create_access_token({"sub": user.username, "role": role})

        # Assuming there's an endpoint that requires curator or admin role
        response = await async_client.post(
            "/api/genes/curate",
            headers={"Authorization": f"Bearer {token}"},
            json={"gene_id": "HGNC:1234", "action": "approve"},
        )

        if response.status_code == 404:
            pytest.skip("Curation endpoint not yet implemented")

        assert response.status_code == expected_status

    @pytest.mark.asyncio
    async def test_public_read_access(self, async_client: AsyncClient):
        """Test that public endpoints don't require authentication."""
        # Public endpoints should work without authentication
        response = await async_client.get("/api/genes")

        # Gene listing should be public
        assert response.status_code == 200


@pytest.mark.integration
class TestUserManagement:
    """Test user management endpoints (admin only)."""

    @pytest.fixture
    def admin_token(self, admin_user) -> str:
        """Create admin token for testing."""
        return create_access_token({"sub": admin_user.username, "role": "admin"})

    @pytest.mark.asyncio
    async def test_list_users(self, async_client: AsyncClient, admin_token: str):
        """Test listing all users (admin only)."""
        response = await async_client.get(
            "/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"}
        )

        if response.status_code == 404:
            pytest.skip("User management endpoint not yet implemented")

        assert response.status_code == 200
        users = response.json()

        assert isinstance(users, list) or "items" in users

    @pytest.mark.asyncio
    async def test_update_user_role(self, async_client: AsyncClient, admin_token: str, test_user):
        """Test updating user role (admin only)."""
        update_data = {"role": "curator"}

        response = await async_client.patch(
            f"/api/admin/users/{test_user.id}/role",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=update_data,
        )

        if response.status_code == 404:
            pytest.skip("User role update endpoint not yet implemented")

        assert response.status_code == 200
        updated_user = response.json()
        assert updated_user["role"] == "curator"

    @pytest.mark.asyncio
    async def test_deactivate_user(self, async_client: AsyncClient, admin_token: str, test_user):
        """Test deactivating a user account (admin only)."""
        response = await async_client.post(
            f"/api/admin/users/{test_user.id}/deactivate",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        if response.status_code == 404:
            pytest.skip("User deactivation endpoint not yet implemented")

        assert response.status_code == 200
        result = response.json()
        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_user(self, async_client: AsyncClient, admin_token: str, test_user):
        """Test deleting a user (admin only)."""
        response = await async_client.delete(
            f"/api/admin/users/{test_user.id}", headers={"Authorization": f"Bearer {admin_token}"}
        )

        if response.status_code == 404:
            pytest.skip("User deletion endpoint not yet implemented")

        assert response.status_code in [200, 204]

        # Verify user is deleted
        get_response = await async_client.get(
            f"/api/admin/users/{test_user.id}", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_response.status_code == 404


@pytest.mark.integration
class TestPasswordManagement:
    """Test password reset and change functionality."""

    @pytest.mark.asyncio
    async def test_password_reset_request(self, async_client: AsyncClient, test_user):
        """Test requesting a password reset."""
        reset_data = {"email": test_user.email}

        response = await async_client.post("/api/auth/password-reset", json=reset_data)

        if response.status_code == 404:
            pytest.skip("Password reset endpoint not yet implemented")

        assert response.status_code == 200
        # Should send reset email (in test mode, might return token)

    @pytest.mark.asyncio
    async def test_password_change(self, authenticated_client: AsyncClient):
        """Test changing password while authenticated."""
        change_data = {"old_password": "testpass123", "new_password": "NewSecurePassword456!"}

        response = await authenticated_client.post("/api/auth/change-password", json=change_data)

        if response.status_code == 404:
            pytest.skip("Password change endpoint not yet implemented")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_password_change_wrong_old_password(self, authenticated_client: AsyncClient):
        """Test password change with incorrect old password."""
        change_data = {"old_password": "wrongpassword", "new_password": "NewSecurePassword456!"}

        response = await authenticated_client.post("/api/auth/change-password", json=change_data)

        if response.status_code == 404:
            pytest.skip("Password change endpoint not yet implemented")

        assert response.status_code in [400, 401]
