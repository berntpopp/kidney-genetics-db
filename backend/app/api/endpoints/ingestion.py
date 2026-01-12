"""
Hybrid source file upload API.

Simplified replacement for the complex static ingestion system.
Handles file uploads for DiagnosticPanels source.
"""

import time
from typing import Any, cast

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_curator
from app.core.exceptions import DataSourceError, ValidationError
from app.core.logging import get_logger
from app.core.responses import ResponseBuilder
from app.models.gene import GeneEvidence
from app.models.static_sources import StaticEvidenceUpload, StaticSourceAudit
from app.models.user import User
from app.pipeline.sources.unified import get_unified_source
from app.services.hybrid_source_manager import get_source_manager

logger = get_logger(__name__)

router = APIRouter()

# Define which sources support file uploads
UPLOAD_SOURCES = {"DiagnosticPanels", "Literature"}


@router.post("/{source_name}/upload")
async def upload_evidence_file(
    source_name: str,
    file: UploadFile = File(...),
    provider_name: str | None = Form(None),
    mode: str = Form("merge"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_curator),
) -> dict[str, Any]:
    """
    Upload evidence file for hybrid sources.

    This endpoint accepts file uploads for DiagnosticPanels source,
    processing them through the unified source pipeline and properly merging
    evidence to avoid duplicates.

    Args:
        source_name: Name of the source (DiagnosticPanels)
        file: The file to upload (JSON, CSV, TSV, or Excel)
        provider_name: Optional provider/source identifier
        db: Database session

    Returns:
        Upload status and statistics
    """
    # Validate source
    if source_name not in UPLOAD_SOURCES:
        raise DataSourceError(
            source_name,
            "upload",
            f"Source does not support file uploads. Available: {', '.join(UPLOAD_SOURCES)}",
        )

    # Validate mode
    if mode not in ["merge", "replace"]:
        raise ValidationError(field="mode", reason="Mode must be 'merge' or 'replace'")

    # Validate file size (50MB limit)
    file_size = 0
    content_chunks = []
    chunk_size = 1024 * 1024  # 1MB chunks

    while chunk := await file.read(chunk_size):
        content_chunks.append(chunk)
        file_size += len(chunk)
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise ValidationError(field="file", reason="File size exceeds 50MB limit")

    file_content = b"".join(content_chunks)

    # Calculate SHA256 hash of file content
    import hashlib

    file_hash = hashlib.sha256(file_content).hexdigest()

    await logger.info(
        "File hash calculated", file_hash=file_hash, filename=file.filename, mode=mode
    )

    # Determine file type
    if not file.filename:
        raise ValidationError(field="filename", reason="Filename is required")

    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ["json", "csv", "tsv", "xlsx", "xls"]:
        raise ValidationError(
            field="file_type",
            reason=f"Unsupported file type: {file_extension}. Supported: json, csv, tsv, xlsx, xls",
        )

    # Use filename (without extension) as provider if not specified
    if not provider_name:
        provider_name = file.filename.rsplit(".", 1)[0]

    # Log the upload attempt
    await logger.info(
        "Processing upload",
        source_name=source_name,
        filename=file.filename,
        file_size=file_size,
        provider_name=provider_name,
        uploaded_by=current_user.id,
        user_role=current_user.role,
        mode=mode,
    )

    try:
        # REPLACE mode: Delete existing data first (with transaction safety)
        if mode == "replace" and provider_name:
            from app.services.hybrid_source_manager import get_source_manager

            await logger.info(
                "REPLACE mode: deleting existing data",
                provider=provider_name,
                source=source_name,
            )

            try:
                # Start savepoint for rollback capability
                savepoint = db.begin_nested()

                try:
                    manager = get_source_manager(source_name, db)
                    delete_stats = await manager.delete_by_identifier(
                        provider_name, current_user.username
                    )

                    await logger.info("REPLACE mode: existing data deleted", stats=delete_stats)

                except Exception as delete_error:
                    savepoint.rollback()
                    await logger.error(
                        "REPLACE mode: delete failed, rolling back", error=delete_error
                    )
                    raise DataSourceError(
                        source_name,
                        "replace_delete",
                        f"Failed to delete existing data: {str(delete_error)}",
                    ) from delete_error

            except Exception:
                # Rollback entire transaction on failure
                db.rollback()
                raise

        # Get source processor
        await logger.info("Getting source processor", source_name=source_name)
        source = get_unified_source(source_name, db_session=db)

        await logger.info("Source processor obtained", source_class=source.__class__.__name__)

        # Process through source pipeline
        await logger.info(
            "Fetching raw data from file",
            file_extension=file_extension,
            provider_name=provider_name,
        )
        # For file-based sources, use their specific parsing methods
        from app.pipeline.sources.unified.diagnostic_panels import DiagnosticPanelsSource
        from app.pipeline.sources.unified.literature import LiteratureSource

        if isinstance(source, DiagnosticPanelsSource):
            raw_data = await source.parse_uploaded_file(file_content, file_extension, provider_name)
        elif isinstance(source, LiteratureSource):
            # For Literature, extract publication_id from filename (e.g., literature_pmid_26862157.json)
            publication_id = provider_name
            raw_data = await source.parse_uploaded_file(file_content, file_extension, publication_id)
        else:
            # For other sources, fall back to standard fetch (shouldn't happen for file uploads)
            raise DataSourceError(
                source_name,
                "file_processing",
                f"Source '{source_name}' does not support file uploads",
            )

        await logger.info(
            "Raw data fetched",
            row_count=len(raw_data) if hasattr(raw_data, "__len__") else "unknown",
        )

        # Process data
        await logger.info("Processing raw data")
        processed_data = await source.process_data(raw_data)

        await logger.info("Data processed", gene_count=len(processed_data) if processed_data else 0)

        await logger.info("Starting hybrid gene creation/evidence merging", provider=provider_name)

        # Use hybrid source approach with gene creation + evidence merging
        from app.core.gene_normalizer import normalize_genes_batch_async
        from app.core.progress_tracker import ProgressTracker

        tracker = ProgressTracker(db=db, source_name=source_name)

        # Step 1: Normalize and create missing genes
        gene_symbols = list(processed_data.keys())
        batch_size = 50
        total_batches = (len(gene_symbols) + batch_size - 1) // batch_size

        await logger.info(
            "Starting gene normalization",
            total_symbols=len(gene_symbols),
            batch_size=batch_size,
            total_batches=total_batches,
        )

        genes_created = 0
        genes_updated = 0

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(gene_symbols))
            batch_symbols = gene_symbols[start_idx:end_idx]

            tracker.update(operation=f"Creating genes batch {batch_num + 1}/{total_batches}")

            await logger.debug(
                "Processing batch", batch_num=batch_num + 1, batch_size=len(batch_symbols)
            )

            # Normalize gene symbols and create missing genes
            normalization_results = await normalize_genes_batch_async(
                db, batch_symbols, source_name
            )

            await logger.debug(
                "Batch normalized",
                batch_num=batch_num + 1,
                normalized_count=len(normalization_results),
            )

            # Create missing genes
            for symbol in batch_symbols:
                norm_result = normalization_results.get(symbol, {})
                if norm_result.get("status") == "normalized":
                    gene = await source._get_or_create_gene(
                        db, norm_result, symbol, {"genes_created": 0, "genes_updated": 0}
                    )
                    if gene:
                        genes_created += 1 if norm_result.get("created") else 0
                        genes_updated += 1 if not norm_result.get("created") else 0

            db.commit()

            await logger.debug(
                "Batch committed",
                batch_num=batch_num + 1,
                batch_created=sum(
                    1 for s in batch_symbols if normalization_results.get(s, {}).get("created")
                ),
                batch_updated=sum(
                    1
                    for s in batch_symbols
                    if normalization_results.get(s, {}).get("status") == "normalized"
                    and not normalization_results.get(s, {}).get("created")
                ),
            )

        await logger.info(
            "Gene normalization complete", genes_created=genes_created, genes_updated=genes_updated
        )

        # Step 2: Store evidence using custom merge logic
        tracker.update(operation="Storing evidence with aggregation")

        await logger.info(
            "Starting evidence storage", gene_count=len(processed_data), provider=provider_name
        )

        # Store evidence - DiagnosticPanelsSource and LiteratureSource have store_evidence method
        if not isinstance(source, DiagnosticPanelsSource | LiteratureSource):
            raise DataSourceError(source_name, "store", "Source does not support evidence storage")

        evidence_stats = await source.store_evidence(
            db,
            processed_data,
            provider_name,
            file_hash=file_hash,
            original_filename=file.filename,
            uploaded_by=current_user.id,
            mode=mode,
        )

        await logger.info("Evidence storage complete", stats=evidence_stats)

        db.commit()

        await logger.info("Database committed")

        # Convert to expected format
        stats = {
            "created": evidence_stats.get("created", 0) + genes_created,
            "merged": evidence_stats.get("merged", 0),
            "failed": evidence_stats.get("failed", 0),
            "filtered": evidence_stats.get("filtered", 0),
        }

        await logger.info("Upload processing complete", final_stats=stats)

        # Return comprehensive response
        upload_result = {
            "status": "success",
            "source": source_name,
            "provider": provider_name,
            "filename": file.filename,
            "file_size": file_size,
            "genes_processed": len(processed_data),
            "storage_stats": stats,
            "message": f"Successfully processed {len(processed_data)} genes. Created: {stats.get('created', 0)}, Merged: {stats.get('merged', 0)}",
        }

        return cast(
            dict[str, Any],
            ResponseBuilder.build_success_response(
                data=upload_result,
                meta={"upload_id": f"upload_{int(time.time())}", "processing_time_ms": None},
            ),
        )

    except ValueError as e:
        import traceback

        await logger.error(
            "Validation error processing upload",
            error=e,
            source_name=source_name,
            traceback=traceback.format_exc(),
        )
        raise ValidationError(field="file_content", reason=str(e)) from e
    except Exception as e:
        import traceback

        await logger.error(
            "Failed to process upload",
            error=e,
            source_name=source_name,
            traceback=traceback.format_exc(),
        )
        raise DataSourceError(source_name, "file_processing", f"Processing failed: {str(e)}") from e


@router.get("/{source_name}/status")
async def get_source_status(source_name: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get status and statistics for a hybrid source.

    Args:
        source_name: Name of the source
        db: Database session

    Returns:
        Source status and statistics
    """
    if source_name not in UPLOAD_SOURCES:
        raise DataSourceError(
            source_name, "status", f"Source not found. Available: {', '.join(UPLOAD_SOURCES)}"
        )

    # Get evidence statistics
    stmt = select(
        func.count(GeneEvidence.id).label("evidence_records"),
        func.count(func.distinct(GeneEvidence.gene_id)).label("unique_genes"),
    ).where(GeneEvidence.source_name == source_name)

    result = db.execute(stmt).first()

    # Get additional statistics for diagnostic panels
    additional_stats = {}
    if source_name == "DiagnosticPanels" and result.evidence_records > 0:
        # Get provider count
        stmt = (
            select(GeneEvidence.evidence_data)
            .where(GeneEvidence.source_name == source_name)
            .limit(100)
        )

        evidence_samples = db.execute(stmt).scalars().all()

        providers = set()
        panels = set()
        for evidence_data in evidence_samples:
            if evidence_data:
                providers.update(evidence_data.get("providers", []))
                panels.update(evidence_data.get("panels", []))

        additional_stats = {
            "sample_providers": sorted(providers)[:5],  # Show first 5
            "sample_panels": sorted(panels)[:5],  # Show first 5
            "provider_count_estimate": len(providers),
            "panel_count_estimate": len(panels),
        }

    status_data = {
        "source": source_name,
        "evidence_records": result.evidence_records or 0,
        "unique_genes": result.unique_genes or 0,
        "supports_upload": True,
        "supported_formats": ["json", "csv", "tsv", "xlsx", "xls"],
        **additional_stats,
    }

    return cast(
        dict[str, Any],
        ResponseBuilder.build_success_response(
            data=status_data, meta={"source_name": source_name}
        ),
    )


@router.get("/")
async def list_hybrid_sources() -> dict[str, Any]:
    """
    List all available hybrid sources.

    Returns:
        List of hybrid sources and their capabilities
    """
    sources = []

    for source_name in UPLOAD_SOURCES:
        source_info = {
            "name": source_name,
            "supports_upload": True,
            "supported_formats": ["json", "csv", "tsv", "xlsx", "xls"],
            "description": "",
        }

        if source_name == "DiagnosticPanels":
            source_info["description"] = "Commercial diagnostic panel data from various providers"

        sources.append(source_info)

    return cast(
        dict[str, Any],
        ResponseBuilder.build_success_response(
            data={"sources": sources}, meta={"total": len(sources)}
        ),
    )


@router.delete("/{source_name}/identifiers/{identifier}")
async def delete_by_identifier(
    source_name: str,
    identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_curator),
) -> dict[str, Any]:
    """
    Delete evidence by provider/publication identifier.

    Args:
        source_name: Name of the source (DiagnosticPanels or Literature)
        identifier: Provider name (DiagnosticPanels) or PMID (Literature)
        db: Database session
        current_user: Authenticated user

    Returns:
        Deletion statistics and audit record
    """
    if source_name not in UPLOAD_SOURCES:
        raise DataSourceError(
            source_name, "delete", f"Source not found. Available: {', '.join(UPLOAD_SOURCES)}"
        )

    await logger.info(
        "Deleting evidence by identifier",
        source=source_name,
        identifier=identifier,
        user=current_user.username,
    )

    try:
        manager = get_source_manager(source_name, db)
        stats = await manager.delete_by_identifier(identifier, current_user.username)

        db.commit()

        await logger.info(
            "Deletion complete", source=source_name, identifier=identifier, stats=stats
        )

        return cast(
            dict[str, Any],
            ResponseBuilder.build_success_response(
                data={
                    "source": source_name,
                    "identifier": identifier,
                    "deletion_stats": stats,
                    "message": f"Successfully deleted {stats.get('deleted_evidence', 0)} evidence records",
                },
                meta={"deleted_by": current_user.username},
            ),
        )

    except Exception as e:
        db.rollback()
        await logger.error(
            "Failed to delete by identifier",
            source=source_name,
            identifier=identifier,
            error=e,
        )
        raise DataSourceError(source_name, "delete", f"Deletion failed: {str(e)}") from e


@router.delete("/{source_name}/uploads/{upload_id}")
async def soft_delete_upload(
    source_name: str,
    upload_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_curator),
) -> dict[str, Any]:
    """
    Soft delete an upload record (marks as deleted, doesn't remove data).

    Args:
        source_name: Name of the source
        upload_id: ID of the upload to delete
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated upload record
    """
    if source_name not in UPLOAD_SOURCES:
        raise DataSourceError(
            source_name, "delete", f"Source not found. Available: {', '.join(UPLOAD_SOURCES)}"
        )

    # Find upload record
    stmt = select(StaticEvidenceUpload).where(StaticEvidenceUpload.id == upload_id)
    upload = db.execute(stmt).scalar_one_or_none()

    if not upload:
        raise ValidationError(field="upload_id", reason=f"Upload {upload_id} not found")

    await logger.info(
        "Soft deleting upload record",
        upload_id=upload_id,
        source=source_name,
        user=current_user.username,
    )

    # Soft delete by updating status
    upload.upload_status = "deleted"
    upload.updated_at = func.now()

    # Create audit record
    from app.models.static_sources import StaticSource

    static_source = db.query(StaticSource).filter(StaticSource.source_name == source_name).first()

    if static_source:
        from datetime import datetime

        # Get user ID for audit
        user_result = db.execute(
            select(User.id).where(User.username == current_user.username)
        ).scalar_one_or_none()

        audit = StaticSourceAudit(
            source_id=static_source.id,
            action="soft_delete_upload",
            changes={"upload_id": upload_id, "evidence_name": upload.evidence_name},
            user_id=user_result,
            performed_at=datetime.utcnow(),
        )
        db.add(audit)

    db.commit()

    await logger.info("Upload soft deleted", upload_id=upload_id, source=source_name)

    return cast(
        dict[str, Any],
        ResponseBuilder.build_success_response(
            data={
                "upload_id": upload_id,
                "source": source_name,
                "status": "deleted",
                "message": f"Upload {upload_id} marked as deleted",
            },
            meta={"deleted_by": current_user.username},
        ),
    )


@router.get("/{source_name}/uploads")
async def list_uploads(
    source_name: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    List upload history for a source.

    Args:
        source_name: Name of the source
        limit: Maximum number of records to return
        offset: Number of records to skip
        db: Database session

    Returns:
        List of upload records
    """
    if source_name not in UPLOAD_SOURCES:
        raise DataSourceError(
            source_name, "list", f"Source not found. Available: {', '.join(UPLOAD_SOURCES)}"
        )

    # Get source ID
    from app.models.static_sources import StaticSource

    static_source = db.query(StaticSource).filter(StaticSource.source_name == source_name).first()

    if not static_source:
        raise DataSourceError(source_name, "list", "Source configuration not found")

    # Query uploads
    stmt = (
        select(StaticEvidenceUpload)
        .where(StaticEvidenceUpload.source_id == static_source.id)
        .order_by(StaticEvidenceUpload.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    uploads = db.execute(stmt).scalars().all()

    # Count total
    count_stmt = select(func.count(StaticEvidenceUpload.id)).where(
        StaticEvidenceUpload.source_id == static_source.id
    )
    total = db.execute(count_stmt).scalar()

    # Convert to dict
    upload_list = []
    for upload in uploads:
        upload_list.append(
            {
                "id": upload.id,
                "evidence_name": upload.evidence_name,
                "file_hash": upload.file_hash,
                "original_filename": upload.original_filename,
                "upload_status": upload.upload_status,
                "uploaded_by": upload.uploaded_by,
                "uploaded_at": upload.created_at.isoformat() if upload.created_at else None,
                "processed_at": upload.processed_at.isoformat() if upload.processed_at else None,
                "gene_count": upload.gene_count,
                "genes_normalized": upload.genes_normalized,
                "genes_failed": upload.genes_failed,
                "upload_metadata": upload.upload_metadata,
            }
        )

    return cast(
        dict[str, Any],
        ResponseBuilder.build_success_response(
            data={"uploads": upload_list},
            meta={"total": total, "limit": limit, "offset": offset, "source_name": source_name},
        ),
    )


@router.get("/{source_name}/audit")
async def get_audit_trail(
    source_name: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get audit trail for a source.

    Args:
        source_name: Name of the source
        limit: Maximum number of records to return
        offset: Number of records to skip
        db: Database session

    Returns:
        List of audit records
    """
    if source_name not in UPLOAD_SOURCES:
        raise DataSourceError(
            source_name, "audit", f"Source not found. Available: {', '.join(UPLOAD_SOURCES)}"
        )

    # Get source ID
    from app.models.static_sources import StaticSource

    static_source = db.query(StaticSource).filter(StaticSource.source_name == source_name).first()

    if not static_source:
        raise DataSourceError(source_name, "audit", "Source configuration not found")

    # Query audit records
    stmt = (
        select(StaticSourceAudit)
        .where(StaticSourceAudit.source_id == static_source.id)
        .order_by(StaticSourceAudit.performed_at.desc())
        .limit(limit)
        .offset(offset)
    )

    audits = db.execute(stmt).scalars().all()

    # Count total
    count_stmt = select(func.count(StaticSourceAudit.id)).where(
        StaticSourceAudit.source_id == static_source.id
    )
    total = db.execute(count_stmt).scalar()

    # Convert to dict
    audit_list = []
    for audit in audits:
        # Get username from user_id
        username = None
        if audit.user_id:
            user = db.execute(
                select(User.username).where(User.id == audit.user_id)
            ).scalar_one_or_none()
            username = user if user else f"user_{audit.user_id}"

        audit_list.append(
            {
                "id": audit.id,
                "action": audit.action,
                "performed_by": username,
                "performed_at": audit.performed_at.isoformat() if audit.performed_at else None,
                "details": audit.changes,
            }
        )

    return cast(
        dict[str, Any],
        ResponseBuilder.build_success_response(
            data={"audit_records": audit_list},
            meta={"total": total, "limit": limit, "offset": offset, "source_name": source_name},
        ),
    )


@router.get("/{source_name}/identifiers")
async def list_identifiers(source_name: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    List all providers (DiagnosticPanels) or PMIDs (Literature) for a source.

    Args:
        source_name: Name of the source
        db: Database session

    Returns:
        List of identifiers with gene counts
    """
    if source_name not in UPLOAD_SOURCES:
        raise DataSourceError(
            source_name, "list", f"Source not found. Available: {', '.join(UPLOAD_SOURCES)}"
        )

    await logger.info("Listing identifiers", source=source_name)

    # Use views for efficient identifier listing
    if source_name == "DiagnosticPanels":
        view_query = """
            SELECT provider_name as identifier, gene_count, last_updated
            FROM v_diagnostic_panel_providers
            ORDER BY gene_count DESC
        """
    elif source_name == "Literature":
        view_query = """
            SELECT pmid as identifier, gene_count, last_updated
            FROM v_literature_publications
            ORDER BY gene_count DESC
        """
    else:
        raise DataSourceError(source_name, "list", "Unsupported source")

    from sqlalchemy import text

    result = db.execute(text(view_query))
    rows = result.fetchall()

    # Convert to list of dicts
    identifiers = []
    for row in rows:
        identifiers.append(
            {
                "identifier": row.identifier,
                "gene_count": row.gene_count,
                "last_updated": row.last_updated.isoformat() if row.last_updated else None,
            }
        )

    return cast(
        dict[str, Any],
        ResponseBuilder.build_success_response(
            data={"identifiers": identifiers},
            meta={"total": len(identifiers), "source_name": source_name},
        ),
    )
