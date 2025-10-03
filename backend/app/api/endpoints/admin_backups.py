"""
Administrative backup management API endpoints.

Provides endpoints for creating, restoring, and managing database backups.
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.backup_job import BackupJob, BackupStatus
from app.models.user import User
from app.services.backup_service import BackupService

router = APIRouter()


# Request/Response Models
class CreateBackupRequest(BaseModel):
    """Request model for creating a backup"""
    description: str = Field(default="", description="Optional description for the backup")
    include_logs: bool = Field(default=False, description="Include system log tables")
    include_cache: bool = Field(default=False, description="Include cache tables")
    compression_level: int = Field(default=6, ge=0, le=9, description="Compression level (0-9)")
    parallel_jobs: int = Field(default=2, ge=1, le=8, description="Number of parallel jobs")


class RestoreBackupRequest(BaseModel):
    """Request model for restoring a backup"""
    create_safety_backup: bool = Field(default=True, description="Create safety backup before restore")
    drop_existing: bool = Field(default=True, description="Drop existing database")
    run_analyze: bool = Field(default=True, description="Run ANALYZE after restore")


class BackupJobResponse(BaseModel):
    """Response model for backup job"""
    id: int
    filename: str
    file_size_mb: float
    status: str
    created_at: str
    completed_at: str | None
    duration_seconds: int | None
    description: str | None
    trigger_source: str
    checksum_sha256: str | None

    class Config:
        from_attributes = True


@router.post("/create")
async def create_backup(
    request: CreateBackupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> dict[str, Any]:
    """
    Create a database backup (admin only).

    Options:
    - include_logs: Include system log tables
    - include_cache: Include cache tables
    - compression_level: 0-9 (higher = better compression, slower)
    - parallel_jobs: Number of parallel dump jobs (faster on multi-core)
    """
    service = BackupService(db)

    backup_job = await service.create_backup(
        user_id=current_user.id,
        description=request.description,
        include_logs=request.include_logs,
        include_cache=request.include_cache,
        compression_level=request.compression_level,
        parallel_jobs=request.parallel_jobs
    )

    return {
        "id": backup_job.id,
        "filename": backup_job.filename,
        "status": backup_job.status.value,
        "created_at": backup_job.created_at.isoformat() if backup_job.created_at else None,
        "message": "Backup created successfully"
    }


@router.post("/restore/{backup_id}")
async def restore_backup(
    backup_id: int,
    request: RestoreBackupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> dict[str, Any]:
    """
    Restore database from backup (admin only).

    ⚠️ WARNING: This will replace the current database!

    Options:
    - create_safety_backup: Create backup before restore (RECOMMENDED)
    - drop_existing: Drop current database (required for clean restore)
    - run_analyze: Run ANALYZE after restore (RECOMMENDED for performance)
    """
    service = BackupService(db)

    result = await service.restore_backup(
        backup_id=backup_id,
        user_id=current_user.id,
        create_safety_backup=request.create_safety_backup,
        drop_existing=request.drop_existing,
        run_analyze=request.run_analyze
    )

    return result


@router.get("/stats")
async def get_backup_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> dict[str, Any]:
    """Get backup statistics"""
    service = BackupService(db)
    return await service.get_backup_stats()


@router.post("/cleanup")
async def cleanup_old_backups(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> dict[str, Any]:
    """Manually trigger cleanup of old backups"""
    service = BackupService(db)
    deleted_count = await service.cleanup_old_backups()

    return {
        "message": f"Deleted {deleted_count} expired backup(s)",
        "deleted_count": deleted_count
    }


@router.get("")
async def list_backups(
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    status: BackupStatus | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> dict[str, Any]:
    """List all backups with optional status filter"""
    service = BackupService(db)
    backups = await service.list_backups(limit=limit, status=status)

    return {
        "backups": [
            {
                "id": b.id,
                "filename": b.filename,
                "file_size_mb": round(b.file_size / (1024**2), 2) if b.file_size else 0,
                "status": b.status.value,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "completed_at": b.completed_at.isoformat() if b.completed_at else None,
                "duration_seconds": b.duration_seconds,
                "description": b.description,
                "trigger_source": b.trigger_source.value,
                "checksum_sha256": b.checksum_sha256
            }
            for b in backups
        ],
        "total": len(backups)
    }


@router.get("/{backup_id}/download")
async def download_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Download backup file"""
    backup_job = db.query(BackupJob).get(backup_id)
    if not backup_job:
        raise HTTPException(404, "Backup not found")

    file_path = Path(backup_job.file_path)
    if not file_path.exists():
        raise HTTPException(404, "Backup file not found")

    return FileResponse(
        path=file_path,
        filename=backup_job.filename,
        media_type="application/octet-stream"
    )


@router.get("/{backup_id}")
async def get_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> dict[str, Any]:
    """Get details of a specific backup"""
    backup_job = db.query(BackupJob).get(backup_id)
    if not backup_job:
        raise HTTPException(404, "Backup not found")

    return {
        "id": backup_job.id,
        "filename": backup_job.filename,
        "file_path": backup_job.file_path,
        "file_size": backup_job.file_size,
        "file_size_mb": round(backup_job.file_size / (1024**2), 2) if backup_job.file_size else 0,
        "checksum_sha256": backup_job.checksum_sha256,
        "format": backup_job.format,
        "compression_level": backup_job.compression_level,
        "include_logs": backup_job.include_logs,
        "include_cache": backup_job.include_cache,
        "parallel_jobs": backup_job.parallel_jobs,
        "status": backup_job.status.value,
        "trigger_source": backup_job.trigger_source.value,
        "started_at": backup_job.started_at.isoformat() if backup_job.started_at else None,
        "completed_at": backup_job.completed_at.isoformat() if backup_job.completed_at else None,
        "duration_seconds": backup_job.duration_seconds,
        "created_by_id": backup_job.created_by_id,
        "error_message": backup_job.error_message,
        "error_details": backup_job.error_details,
        "database_size_bytes": backup_job.database_size_bytes,
        "tables_count": backup_job.tables_count,
        "created_at": backup_job.created_at.isoformat() if backup_job.created_at else None,
        "expires_at": backup_job.expires_at.isoformat() if backup_job.expires_at else None,
        "description": backup_job.description
    }


@router.delete("/{backup_id}")
async def delete_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> dict[str, Any]:
    """Delete a backup"""
    service = BackupService(db)

    try:
        await service.delete_backup(backup_id)
        return {"message": f"Backup {backup_id} deleted successfully"}
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
