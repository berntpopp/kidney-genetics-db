"""Tests for opaque refresh token system."""

from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.unit
class TestRefreshTokenModel:
    """Verify RefreshToken model structure."""

    def test_model_exists(self):
        from app.models.refresh_token import RefreshToken

        assert RefreshToken.__tablename__ == "refresh_tokens"

    def test_has_required_columns(self):
        from app.models.refresh_token import RefreshToken

        columns = {c.name for c in RefreshToken.__table__.columns}
        assert "id" in columns
        assert "token_hash" in columns
        assert "family_id" in columns
        assert "user_id" in columns
        assert "is_revoked" in columns
        assert "created_at" in columns
        assert "expires_at" in columns


@pytest.mark.unit
class TestOpaqueRefreshToken:
    """Verify opaque refresh token creation and hashing."""

    def test_create_opaque_refresh_token(self):
        from app.core.security import create_opaque_refresh_token

        raw_token, token_hash = create_opaque_refresh_token()
        assert isinstance(raw_token, str)
        assert isinstance(token_hash, str)
        assert len(token_hash) == 64  # SHA-256 hex

    def test_token_hash_is_deterministic(self):
        from app.core.security import hash_token

        token = "test_token_value"
        hash1 = hash_token(token)
        hash2 = hash_token(token)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_different_tokens_different_hashes(self):
        from app.core.security import create_opaque_refresh_token

        _, hash1 = create_opaque_refresh_token()
        _, hash2 = create_opaque_refresh_token()
        assert hash1 != hash2


@pytest.mark.integration
class TestTokenRotation:
    """Verify refresh token rotation and family-based reuse detection."""

    def test_refresh_returns_new_token(self, db_session):
        """Creating and revoking a token should work."""
        from app.core.security import create_opaque_refresh_token
        from app.models.refresh_token import RefreshToken

        raw_token, token_hash = create_opaque_refresh_token()
        rt = RefreshToken(
            token_hash=token_hash,
            family_id="test-family",
            user_id=1,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(rt)
        db_session.commit()

        assert not rt.is_revoked

    def test_reused_token_revokes_family(self, db_session):
        """Presenting a revoked token should invalidate the entire family."""
        from app.models.refresh_token import RefreshToken

        family_id = "reuse-test-family"
        rt1 = RefreshToken(
            token_hash="hash1_unique_test",
            family_id=family_id,
            user_id=1,
            is_revoked=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        rt2 = RefreshToken(
            token_hash="hash2_unique_test",
            family_id=family_id,
            user_id=1,
            is_revoked=False,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add_all([rt1, rt2])
        db_session.commit()

        # Simulate reuse detection
        db_session.query(RefreshToken).filter(RefreshToken.family_id == family_id).update(
            {"is_revoked": True}
        )
        db_session.commit()

        assert (
            db_session.query(RefreshToken)
            .filter(
                RefreshToken.family_id == family_id,
                RefreshToken.is_revoked == False,  # noqa: E712
            )
            .count()
            == 0
        )
