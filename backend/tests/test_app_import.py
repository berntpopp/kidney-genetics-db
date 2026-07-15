"""Regression tests for application import side effects."""

import os
import subprocess
import sys
from pathlib import Path


def test_importing_app_does_not_create_schema() -> None:
    """Application imports must leave schema changes to Alembic migrations."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "\n".join(
                [
                    "from unittest.mock import patch",
                    "from app.models import Base",
                    "with patch.object(Base.metadata, 'create_all') as create_all:",
                    "    import app.main",  # noqa: F401
                    "create_all.assert_not_called()",
                ]
            ),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        env={
            **os.environ,
            "ADMIN_PASSWORD": "test-admin-password",
            "AUTO_UPDATE_ENABLED": "false",
            "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
            "JWT_SECRET_KEY": "a-secure-test-jwt-secret-with-32-characters",
            "POSTGRES_PASSWORD": "test-postgres-password",
        },
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
