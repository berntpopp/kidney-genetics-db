"""
Hybrid source file upload API.

Simplified replacement for the complex static ingestion system.
Handles file uploads for DiagnosticPanels source.
"""

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import DataSourceError, ValidationError
from app.core.responses import ResponseBuilder
from app.models.gene import GeneEvidence
from app.pipeline.sources.unified import get_unified_source

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sources", tags=["Hybrid Sources"])

# Define which sources support file uploads
UPLOAD_SOURCES = {"DiagnosticPanels"}


@router.post("/{source_name}/upload")
async def upload_evidence_file(
    source_name: str,
    file: UploadFile = File(...),
    provider_name: str | None = Form(None),
    db: Session = Depends(get_db),
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
    logger.info(
        f"Processing upload for {source_name}: {file.filename} ({file_size} bytes) from {provider_name}"
    )

    try:
        # Get source processor
        source = get_unified_source(source_name, db_session=db)

        # Process through source pipeline
        # Process through source pipeline
        raw_data = await source.fetch_raw_data(file_content, file_extension, provider_name)

        # Process data
        processed_data = await source.process_data(raw_data)

        # Store with merge semantics
        stats = await source.store_evidence(db, processed_data, provider_name)

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

        return ResponseBuilder.build_success_response(
            data=upload_result,
            meta={"upload_id": f"upload_{int(time.time())}", "processing_time_ms": None},
        )

    except ValueError as e:
        import traceback

        logger.error(f"Validation error processing {source_name} upload: {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        raise ValidationError(field="file_content", reason=str(e)) from e
    except Exception as e:
        import traceback

        logger.error(f"Failed to process upload for {source_name}: {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
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

    return ResponseBuilder.build_success_response(
        data=status_data, meta={"source_name": source_name}
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

    return ResponseBuilder.build_success_response(
        data={"sources": sources}, meta={"total": len(sources)}
    )
