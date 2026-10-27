"""
Application version management utilities.

Provides centralized access to component versions for API responses,
logging, and monitoring.
"""

import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
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
        pyproject_path = os.path.join(os.path.dirname(__file__), "..", "..", "pyproject.toml")

        with open(pyproject_path, "rb") as f:  # tomllib requires binary mode
            data = tomllib.load(f)
            version: str = data["project"]["version"]
            logger.sync_debug("Backend version loaded from pyproject.toml", version=version)
            return version

    except Exception as e:
        logger.sync_error("Failed to read backend version from pyproject.toml", error=str(e))
        return "unknown"


def get_database_version(db: Session) -> dict[str, Any] | None:
    """
    Get the applied schema revision from Alembic's own alembic_version table.

    schema_versions only ever got the initial row, so it always said 0001 (#431).

    Args:
        db: Database session

    Returns:
        {"version": "0012", "alembic_revision": "0012"}, or None if unavailable
    """
    try:
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if revision:
            return {"version": revision, "alembic_revision": revision}

        logger.sync_warning("No Alembic revision found in database")
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
                "version": "0012",
                "alembic_revision": "0012"
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
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    logger.sync_debug(
        "All versions retrieved",
        backend_version=backend_version,
        database_version=db_version.get("version") if db_version else "unknown",
    )

    return versions
