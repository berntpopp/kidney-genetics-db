"""
Hybrid source file upload API.

Simplified replacement for the complex static ingestion system.
Handles file uploads for DiagnosticPanels and Literature sources.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.gene import GeneEvidence
from app.pipeline.sources.unified import get_unified_source

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sources", tags=["Hybrid Sources"])

# Define which sources support file uploads
UPLOAD_SOURCES = {"DiagnosticPanels", "Literature"}


@router.post("/{source_name}/upload")
async def upload_evidence_file(
    source_name: str,
    file: UploadFile = File(...),
    provider_name: str | None = Form(None),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Upload evidence file for hybrid sources.
    
    This endpoint accepts file uploads for DiagnosticPanels and Literature sources,
    processing them through the unified source pipeline and properly merging
    evidence to avoid duplicates.
    
    Args:
        source_name: Name of the source (DiagnosticPanels or Literature)
        file: The file to upload (JSON, CSV, TSV, or Excel)
        provider_name: Optional provider/source identifier
        db: Database session
    
    Returns:
        Upload status and statistics
    """
    # Validate source
    if source_name not in UPLOAD_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source '{source_name}' does not support file uploads. Available: {', '.join(UPLOAD_SOURCES)}"
        )

    # Validate file size (50MB limit)
    file_size = 0
    content_chunks = []
    chunk_size = 1024 * 1024  # 1MB chunks

    while chunk := await file.read(chunk_size):
        content_chunks.append(chunk)
        file_size += len(chunk)
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 50MB limit"
            )

    file_content = b''.join(content_chunks)

    # Determine file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in ['json', 'csv', 'tsv', 'xlsx', 'xls']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file_extension}. Supported: json, csv, tsv, xlsx, xls"
        )

    # Use filename (without extension) as provider if not specified
    if not provider_name:
        provider_name = file.filename.rsplit('.', 1)[0]

    # Log the upload attempt
    logger.info(f"Processing upload for {source_name}: {file.filename} ({file_size} bytes) from {provider_name}")

    try:
        # Get source processor
        source = get_unified_source(source_name, db_session=db)

        # Process through source pipeline
        # Note: fetch_raw_data expects different params for different sources
        if source_name == "DiagnosticPanels":
            raw_data = await source.fetch_raw_data(file_content, file_extension, provider_name)
        else:  # Literature
            raw_data = await source.fetch_raw_data(file_content, file_extension, provider_name)

        # Process data
        processed_data = await source.process_data(raw_data)

        # Store with merge semantics
        stats = await source.store_evidence(db, processed_data, provider_name)

        # Return comprehensive response
        return {
            "status": "success",
            "source": source_name,
            "provider": provider_name,
            "filename": file.filename,
            "file_size": file_size,
            "genes_processed": len(processed_data),
            "storage_stats": stats,
            "message": f"Successfully processed {len(processed_data)} genes. Created: {stats.get('created', 0)}, Merged: {stats.get('merged', 0)}"
        }

    except ValueError as e:
        import traceback
        logger.error(f"Validation error processing {source_name} upload: {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        logger.error(f"Failed to process upload for {source_name}: {e}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )


@router.get("/{source_name}/status")
async def get_source_status(
    source_name: str,
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Get status and statistics for a hybrid source.
    
    Args:
        source_name: Name of the source
        db: Database session
        
    Returns:
        Source status and statistics
    """
    if source_name not in UPLOAD_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source '{source_name}' not found. Available: {', '.join(UPLOAD_SOURCES)}"
        )

    # Get evidence statistics
    stmt = select(
        func.count(GeneEvidence.id).label("evidence_records"),
        func.count(func.distinct(GeneEvidence.gene_id)).label("unique_genes")
    ).where(GeneEvidence.source_name == source_name)

    result = db.execute(stmt).first()

    # Get additional statistics for diagnostic panels
    additional_stats = {}
    if source_name == "DiagnosticPanels" and result.evidence_records > 0:
        # Get provider count
        stmt = select(GeneEvidence.evidence_data).where(
            GeneEvidence.source_name == source_name
        ).limit(100)

        evidence_samples = db.execute(stmt).scalars().all()

        providers = set()
        panels = set()
        for evidence_data in evidence_samples:
            if evidence_data:
                providers.update(evidence_data.get("providers", []))
                panels.update(evidence_data.get("panels", []))

        additional_stats = {
            "sample_providers": sorted(list(providers))[:5],  # Show first 5
            "sample_panels": sorted(list(panels))[:5],  # Show first 5
            "provider_count_estimate": len(providers),
            "panel_count_estimate": len(panels)
        }

    return {
        "source": source_name,
        "evidence_records": result.evidence_records or 0,
        "unique_genes": result.unique_genes or 0,
        "supports_upload": True,
        "supported_formats": ["json", "csv", "tsv", "xlsx", "xls"],
        **additional_stats
    }


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
            "description": ""
        }

        if source_name == "DiagnosticPanels":
            source_info["description"] = "Commercial diagnostic panel data from various providers"
        elif source_name == "Literature":
            source_info["description"] = "Literature references and publications"

        sources.append(source_info)

    return {
        "sources": sources,
        "total": len(sources)
    }
