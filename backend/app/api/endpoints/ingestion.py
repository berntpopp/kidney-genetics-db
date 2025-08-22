"""
Static content ingestion API endpoints
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.static_ingestion import StaticContentProcessor
from app.models.static_ingestion import (
    StaticEvidenceUpload,
    StaticSource,
    StaticSourceAudit,
)
from app.schemas.ingestion import (
    AuditLogResponse,
    StaticSourceCreate,
    StaticSourceResponse,
    StaticSourceUpdate,
    UploadListItem,
    UploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


@router.post("/sources", response_model=StaticSourceResponse)
async def create_source(
    source: StaticSourceCreate,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # TODO: Add when auth is implemented
):
    """Create a new static source with scoring configuration"""

    # Check for duplicate
    existing = db.query(StaticSource).filter(
        StaticSource.source_name == source.source_name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source '{source.source_name}' already exists"
        )

    # Create source with scoring metadata
    db_source = StaticSource(
        source_type=source.source_type,
        source_name=source.source_name,
        display_name=source.display_name,
        description=source.description,
        source_metadata=source.source_metadata or {},
        scoring_metadata=source.scoring_metadata.model_dump(),
        created_by=None  # TODO: current_user.email if current_user else None
    )
    db.add(db_source)
    db.flush()

    # Audit
    audit = StaticSourceAudit(
        source_id=db_source.id,
        action="created",
        details={
            "source": source.model_dump(),
            "scoring": source.scoring_metadata.model_dump()
        },
        performed_by=None  # TODO: current_user.email if current_user else None
    )
    db.add(audit)
    db.commit()

    # Add statistics
    db_source.upload_count = 0
    db_source.total_genes = 0

    return db_source


@router.get("/sources", response_model=list[StaticSourceResponse])
async def list_sources(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all static sources"""
    query = db.query(StaticSource)

    if active_only:
        query = query.filter(StaticSource.is_active)

    sources = query.all()

    # Compute statistics dynamically
    for source in sources:
        source.upload_count = db.query(func.count(StaticEvidenceUpload.id)).filter(
            StaticEvidenceUpload.source_id == source.id,
            StaticEvidenceUpload.upload_status == 'completed'
        ).scalar() or 0
        source.total_genes = db.query(func.sum(StaticEvidenceUpload.genes_normalized)).filter(
            StaticEvidenceUpload.source_id == source.id,
            StaticEvidenceUpload.upload_status == 'completed'
        ).scalar() or 0

    return sources


@router.get("/sources/{source_id}", response_model=StaticSourceResponse)
async def get_source(
    source_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific static source"""
    source = db.query(StaticSource).filter(
        StaticSource.id == source_id
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    # Compute statistics dynamically
    source.upload_count = db.query(func.count(StaticEvidenceUpload.id)).filter(
        StaticEvidenceUpload.source_id == source.id,
        StaticEvidenceUpload.upload_status == 'completed'
    ).scalar() or 0
    source.total_genes = db.query(func.sum(StaticEvidenceUpload.genes_normalized)).filter(
        StaticEvidenceUpload.source_id == source.id,
        StaticEvidenceUpload.upload_status == 'completed'
    ).scalar() or 0

    return source


@router.put("/sources/{source_id}", response_model=StaticSourceResponse)
async def update_source(
    source_id: int,
    update: StaticSourceUpdate,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # TODO: Add when auth is implemented
):
    """Update source including scoring configuration"""

    source = db.query(StaticSource).filter(
        StaticSource.id == source_id
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    # Track changes for audit
    changes = {}

    if update.display_name is not None:
        changes["display_name"] = {"old": source.display_name, "new": update.display_name}
        source.display_name = update.display_name

    if update.description is not None:
        changes["description"] = {"old": source.description, "new": update.description}
        source.description = update.description

    if update.source_metadata is not None:
        changes["source_metadata"] = {"old": source.source_metadata, "new": update.source_metadata}
        source.source_metadata = update.source_metadata

    if update.scoring_metadata is not None:
        changes["scoring_metadata"] = {
            "old": source.scoring_metadata,
            "new": update.scoring_metadata.model_dump()
        }
        source.scoring_metadata = update.scoring_metadata.model_dump()

        # Note: Score recalculation happens via view definitions

    if update.is_active is not None:
        changes["is_active"] = {"old": source.is_active, "new": update.is_active}
        source.is_active = update.is_active

    source.updated_at = datetime.utcnow()

    # Audit
    audit = StaticSourceAudit(
        source_id=source_id,
        action="updated",
        details={"changes": changes},
        performed_by=None  # TODO: current_user.email if current_user else None
    )
    db.add(audit)
    db.commit()

    return source


@router.post("/sources/{source_id}/upload", response_model=UploadResponse)
async def upload_evidence(
    source_id: int,
    file: UploadFile = File(...),
    evidence_name: str | None = Form(None),
    replace_existing: bool = Form(False),
    dry_run: bool = Form(False),
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # TODO: Add when auth is implemented
):
    """
    Upload evidence file (JSON, CSV, TSV, Excel).
    Handles scraper outputs and manual uploads.
    """

    # Validate source
    source = db.query(StaticSource).filter(
        StaticSource.id == source_id,
        StaticSource.is_active
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found or inactive"
        )

    # Size validation
    file_size = 0
    temp_content = await file.read()
    file_size = len(temp_content)
    await file.seek(0)  # Reset for processing

    if file_size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50MB limit"
        )

    # Default evidence name
    if not evidence_name:
        evidence_name = file.filename.rsplit('.', 1)[0] if file.filename else "upload"

    # Check existing
    if not replace_existing:
        existing = db.query(StaticEvidenceUpload).filter(
            StaticEvidenceUpload.source_id == source_id,
            StaticEvidenceUpload.evidence_name == evidence_name,
            StaticEvidenceUpload.upload_status != 'superseded'
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Evidence '{evidence_name}' already exists. Set replace_existing=true to update."
            )
    elif not dry_run:
        # CRITICAL: Delete old gene_evidence associated with these uploads
        from app.models import GeneEvidence
        db.query(GeneEvidence).filter(
            GeneEvidence.source_name == f"static_{source_id}",
            GeneEvidence.source_detail == evidence_name
        ).delete(synchronize_session=False)

        # Mark existing upload records as superseded
        db.query(StaticEvidenceUpload).filter(
            StaticEvidenceUpload.source_id == source_id,
            StaticEvidenceUpload.evidence_name == evidence_name,
            StaticEvidenceUpload.upload_status != 'superseded'
        ).update({"upload_status": "superseded"})
        db.commit()

    # Process with batch normalization
    processor = StaticContentProcessor(db)
    result = await processor.process_upload(
        file=file,
        source_id=source_id,
        evidence_name=evidence_name,
        dry_run=dry_run
    )

    # Audit and update cached statistics
    if not dry_run and result["status"] == "success":
        audit = StaticSourceAudit(
            source_id=source_id,
            upload_id=result.get("upload_id"),
            action="uploaded",
            details={
                "evidence_name": evidence_name,
                "filename": file.filename,
                "stats": result.get("stats"),
                "provider_metadata": result.get("provider_metadata")
            },
            performed_by=None  # TODO: current_user.email if current_user else None
        )
        db.add(audit)

        # Statistics are computed dynamically in queries

        db.commit()

    return result


@router.get("/sources/{source_id}/uploads", response_model=list[UploadListItem])
async def list_uploads(
    source_id: int,
    db: Session = Depends(get_db)
):
    """List all uploads for a source"""
    uploads = db.query(StaticEvidenceUpload).filter(
        StaticEvidenceUpload.source_id == source_id
    ).order_by(StaticEvidenceUpload.created_at.desc()).all()

    return uploads


@router.get("/sources/{source_id}/audit", response_model=list[AuditLogResponse])
async def get_audit_log(
    source_id: int,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get audit log for a source"""
    logs = db.query(StaticSourceAudit).filter(
        StaticSourceAudit.source_id == source_id
    ).order_by(StaticSourceAudit.performed_at.desc()).limit(limit).all()

    return logs


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    # current_user = Depends(get_current_user)  # TODO: Add when auth is implemented
):
    """Soft delete a source (mark as inactive)"""

    source = db.query(StaticSource).filter(
        StaticSource.id == source_id
    ).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    # CRITICAL: Delete all gene_evidence associated with this source
    # This prevents orphaned evidence that would incorrectly contribute to scores
    from app.models import GeneEvidence
    deleted_count = db.query(GeneEvidence).filter(
        GeneEvidence.source_name == f"static_{source_id}"
    ).delete(synchronize_session=False)

    logger.info(f"Deleting {deleted_count} gene_evidence records for source {source_id}")

    source.is_active = False
    source.updated_at = datetime.utcnow()

    # Audit with evidence deletion details
    audit = StaticSourceAudit(
        source_id=source_id,
        action="deactivated",
        details={
            "evidence_deleted": deleted_count,
            "source_name": source.source_name
        },
        performed_by=None  # TODO: current_user.email if current_user else None
    )
    db.add(audit)
    db.commit()

    return {"status": "success", "message": f"Source {source_id} deactivated, {deleted_count} evidence records deleted"}

