"""
Data Release API endpoints

Provides endpoints for managing CalVer versioned data releases.
Supports creating releases, publishing with temporal snapshots, and downloading exports.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.logging import get_logger
from app.models.data_release import DataRelease
from app.models.user import User
from app.schemas.releases import ReleaseList, ReleaseResponse, ReleaseUpdate
from app.services.release_service import ReleaseService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=ReleaseList)
async def list_releases(
    db: Session = Depends(get_db),
    status: str | None = Query(None, description="Filter by status (draft/published)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
) -> dict[str, Any]:
    """
    List all data releases.

    Returns releases ordered by version (newest first).
    Optionally filter by status.
    """
    await logger.info("Listing releases", status=status, limit=limit, offset=offset)

    query = db.query(DataRelease)

    if status:
        query = query.filter(DataRelease.status == status)

    total = query.count()
    releases = query.order_by(DataRelease.version.desc()).limit(limit).offset(offset).all()

    return {"data": releases, "meta": {"total": total, "limit": limit, "offset": offset}}


@router.get("/{version}", response_model=ReleaseResponse)
async def get_release(version: str, db: Session = Depends(get_db)) -> DataRelease:
    """
    Get release metadata by version.

    Args:
        version: CalVer version string (e.g., "2025.10")

    Returns:
        Release metadata including export path, checksum, and citation info

    Raises:
        404: Release not found
    """
    await logger.info("Getting release", version=version)

    release: DataRelease | None = db.query(DataRelease).filter_by(version=version).first()
    if not release:
        raise HTTPException(status_code=404, detail=f"Release {version} not found")

    return release


@router.get("/{version}/genes")
async def get_release_genes(
    version: str,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """
    Get genes from a specific release.

    Uses temporal database queries to retrieve genes as they existed
    at the time of the release.

    Args:
        version: Release version
        limit: Maximum genes to return
        offset: Pagination offset

    Returns:
        Paginated list of genes from the release

    Raises:
        404: Release not found
        400: Release not published
    """
    service = ReleaseService(db)

    try:
        result = await service.get_release_genes(version, limit, offset)
        return {
            "data": result,
            "meta": {
                "version": version,
                "total": result["total"],
                "limit": limit,
                "offset": offset,
            },
        }
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e)) from e
        else:
            raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{version}/export")
async def download_export(version: str, db: Session = Depends(get_db)) -> FileResponse:
    """
    Download JSON export file for a release.

    Args:
        version: Release version

    Returns:
        JSON file with release data

    Raises:
        404: Release not found or export file not available
    """
    await logger.info("Downloading export", version=version)

    release = db.query(DataRelease).filter_by(version=version).first()
    if not release:
        raise HTTPException(status_code=404, detail=f"Release {version} not found")

    if not release.export_file_path:
        raise HTTPException(
            status_code=404, detail=f"Export file not available for release {version}"
        )

    return FileResponse(
        path=release.export_file_path,
        media_type="application/json",
        filename=f"kidney-genetics-db_{version}.json",
        headers={"X-Checksum-SHA256": release.export_checksum},
    )


@router.post("/", response_model=ReleaseResponse, dependencies=[Depends(require_admin)])
async def create_release(
    version: str = Query(..., description="CalVer version (e.g., 2025.10)"),
    release_notes: str = Query("", description="Optional release notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DataRelease:
    """
    Create a draft release (admin only).

    Args:
        version: CalVer version string
        release_notes: Optional release notes
        current_user: Authenticated admin user

    Returns:
        Created draft release

    Raises:
        400: Version already exists
    """
    service = ReleaseService(db)

    try:
        release = await service.create_release(
            version=version, user_id=current_user.id, release_notes=release_notes
        )
        return release
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/{release_id}/publish", response_model=ReleaseResponse, dependencies=[Depends(require_admin)]
)
async def publish_release(
    release_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> DataRelease:
    """
    Publish a release (admin only).

    This operation:
    1. Closes all current gene temporal ranges
    2. Exports genes to JSON file
    3. Calculates SHA256 checksum
    4. Updates release record with metadata

    Args:
        release_id: ID of release to publish
        current_user: Authenticated admin user

    Returns:
        Published release with export metadata

    Raises:
        404: Release not found
        400: Release already published
    """
    service = ReleaseService(db)

    try:
        release = await service.publish_release(release_id=release_id, user_id=current_user.id)
        return release
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e)) from e
        else:
            raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch(
    "/{release_id}", response_model=ReleaseResponse, dependencies=[Depends(require_admin)]
)
async def update_release(
    release_id: int,
    update_data: ReleaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> DataRelease:
    """
    Update a draft release (admin only).

    Only draft releases can be updated. Published releases are immutable.

    Args:
        release_id: ID of release to update
        update_data: Fields to update (version and/or release_notes)
        current_user: Authenticated admin user

    Returns:
        Updated release

    Raises:
        404: Release not found
        400: Release already published or version exists
    """
    service = ReleaseService(db)

    try:
        release = await service.update_release(
            release_id=release_id,
            version=update_data.version,
            release_notes=update_data.release_notes,
        )
        return release
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e)) from e
        else:
            raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{release_id}", dependencies=[Depends(require_admin)])
async def delete_release(
    release_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> dict[str, str]:
    """
    Delete a draft release (admin only).

    Only draft releases can be deleted. Published releases are immutable
    for data integrity and citation purposes.

    Args:
        release_id: ID of release to delete
        current_user: Authenticated admin user

    Returns:
        Success message

    Raises:
        404: Release not found
        400: Release already published
    """
    service = ReleaseService(db)

    try:
        await service.delete_release(release_id=release_id)
        return {"message": f"Release {release_id} deleted successfully"}
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e)) from e
        else:
            raise HTTPException(status_code=400, detail=str(e)) from e
