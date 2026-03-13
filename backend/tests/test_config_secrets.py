"""Tests for SecretStr configuration fields."""

import pytest
from pydantic import SecretStr


@pytest.mark.unit
class TestSecretStrConfig:
    """Verify sensitive fields use SecretStr."""

    def test_jwt_secret_key_is_secret_str(self):
        from app.core.config import Settings

        field_info = Settings.model_fields["JWT_SECRET_KEY"]
        assert field_info.annotation is SecretStr

    def test_admin_password_is_secret_str(self):
        from app.core.config import Settings

        field_info = Settings.model_fields["ADMIN_PASSWORD"]
        assert field_info.annotation is SecretStr

    def test_database_url_is_secret_str(self):
        from app.core.config import Settings

        field_info = Settings.model_fields["DATABASE_URL"]
        assert field_info.annotation is SecretStr

    def test_postgres_password_is_secret_str(self):
        from app.core.config import Settings

        field_info = Settings.model_fields["POSTGRES_PASSWORD"]
        assert field_info.annotation is SecretStr

    def test_openai_api_key_is_secret_str_or_none(self):
        from app.core.config import Settings

        field_info = Settings.model_fields["OPENAI_API_KEY"]
        # Should be SecretStr | None
        assert SecretStr in (
            getattr(field_info.annotation, "__args__", ())
            if hasattr(field_info.annotation, "__args__")
            else (field_info.annotation,)
        )

    def test_repr_hides_secrets(self):
        from app.core.config import Settings

        known_password = "test_secret_value_12345"
        s = Settings(
            DATABASE_URL="postgresql://u:p@localhost/db",
            JWT_SECRET_KEY="a" * 32,
            ADMIN_PASSWORD=known_password,
            POSTGRES_PASSWORD="pg_secret_xyz",
        )
        repr_str = repr(s)
        assert known_password not in repr_str
        assert "pg_secret_xyz" not in repr_str

    def test_jwt_secret_key_min_length_validator(self):
        from app.core.config import Settings

        with pytest.raises(Exception):
            Settings(
                JWT_SECRET_KEY="short",
                DATABASE_URL="postgresql://x:x@localhost/x",
                ADMIN_PASSWORD="dummy-password",
                POSTGRES_PASSWORD="dummy-password",
            )

    def test_jwt_secret_key_rejects_placeholder(self):
        from app.core.config import Settings

        with pytest.raises(Exception):
            Settings(
                JWT_SECRET_KEY="CHANGE_THIS_TO_A_SECURE_SECRET_KEY",
                DATABASE_URL="postgresql://x:x@localhost/x",
                ADMIN_PASSWORD="dummy-password",
                POSTGRES_PASSWORD="dummy-password",
            )


@pytest.mark.unit
class TestSecretStrCallSites:
    """Verify call sites use .get_secret_value()."""

    def test_settings_jwt_key_returns_string(self):
        from app.core.config import settings

        # .get_secret_value() must return a plain str for jwt.encode()
        val = settings.JWT_SECRET_KEY.get_secret_value()
        assert isinstance(val, str)
        assert len(val) >= 32

    def test_settings_database_url_returns_string(self):
        from app.core.config import settings

        val = settings.DATABASE_URL.get_secret_value()
        assert val.startswith("postgresql://")

    def test_settings_admin_password_returns_string(self):
        from app.core.config import settings

        val = settings.ADMIN_PASSWORD.get_secret_value()
        assert isinstance(val, str)
        assert len(val) > 0
