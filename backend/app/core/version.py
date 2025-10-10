"""
Application version management utilities.

Provides centralized access to component versions for API responses,
logging, and monitoring.
"""

import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)


def get_package_version() -> str:
    """
    Get backend package version from pyproject.toml.

    Returns:
        Version string (e.g., "0.1.0")
    """
    try:
        import tomllib  # Built-in module in Python 3.11+

        # Path to pyproject.toml
        pyproject_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "pyproject.toml"
        )

        with open(pyproject_path, "rb") as f:  # tomllib requires binary mode
            data = tomllib.load(f)
            version = data["project"]["version"]
            logger.sync_debug("Backend version loaded from pyproject.toml", version=version)
            return version

    except Exception as e:
        logger.sync_error("Failed to read backend version from pyproject.toml", error=str(e))
        return "unknown"


def get_database_version(db: Session) -> dict[str, Any] | None:
    """
    Get latest database schema version from schema_versions table.

    Args:
        db: Database session

    Returns:
        Dict with version info or None if no versions found:
        {
            "version": "0.1.0",
            "alembic_revision": "abc123def456",
            "description": "Initial schema",
            "applied_at": "2025-01-10T10:00:00+00:00"
        }
    """
    try:
        result = db.execute(
            text("""
                SELECT version, alembic_revision, description, applied_at
                FROM schema_versions
                ORDER BY applied_at DESC
                LIMIT 1
            """)
        ).fetchone()

        if result:
            return {
                "version": result.version,
                "alembic_revision": result.alembic_revision,
                "description": result.description,
                "applied_at": result.applied_at.isoformat() if result.applied_at else None,
            }

        logger.sync_warning("No schema versions found in database")
        return None

    except Exception as e:
        logger.sync_error("Failed to get database version", error=str(e))
        return None


def get_all_versions(db: Session) -> dict[str, Any]:
    """
    Get versions for all components.

    Args:
        db: Database session

    Returns:
        Dict with all component versions and environment info:
        {
            "backend": {
                "version": "0.1.0",
                "name": "kidney-genetics-db",
                "type": "FastAPI"
            },
            "database": {
                "version": "0.1.0",
                "alembic_revision": "abc123",
                "description": "...",
                "applied_at": "..."
            },
            "environment": "production",
            "timestamp": "2025-01-10T12:00:00+00:00"
        }
    """
    from datetime import datetime

    backend_version = get_package_version()
    db_version = get_database_version(db)

    versions = {
        "backend": {"version": backend_version, "name": "kidney-genetics-db", "type": "FastAPI"},
        "database": db_version or {"version": "unknown"},
        "environment": os.getenv("ENV", "development"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    logger.sync_debug(
        "All versions retrieved",
        backend_version=backend_version,
        database_version=db_version.get("version") if db_version else "unknown",
    )

    return versions
