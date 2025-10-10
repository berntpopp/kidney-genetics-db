"""
Version information endpoint - Public access, no auth required

This endpoint provides version information for all system components:
- Backend API version (from pyproject.toml)
- Database schema version (from schema_versions table)
- Frontend version (added by frontend when querying)
- Environment information
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.logging import get_logger
from app.core.version import get_all_versions

router = APIRouter()
logger = get_logger(__name__)


@router.get("/version")
async def get_version(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get version information for all components.

    Public endpoint - no authentication required.

    Returns:
        Dict containing version information for backend, database, and environment:
        {
            "backend": {
                "version": "0.1.0",
                "name": "kidney-genetics-db",
                "type": "FastAPI"
            },
            "database": {
                "version": "0.1.0",
                "alembic_revision": "df7756c38ecd",
                "description": "Initial version tracking system",
                "applied_at": "2025-10-10T13:20:00+00:00"
            },
            "environment": "development",
            "timestamp": "2025-10-10T14:30:00Z"
        }
    """
    await logger.info("Version information requested")

    versions = get_all_versions(db)

    await logger.debug(
        "Version info returned",
        backend_version=versions["backend"]["version"],
        database_version=versions["database"].get("version", "unknown"),
        environment=versions.get("environment", "unknown"),
    )

    return versions
