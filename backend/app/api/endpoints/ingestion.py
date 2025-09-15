"""
Hybrid source file upload API.

Simplified replacement for the complex static ingestion system.
Handles file uploads for DiagnosticPanels source.
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_curator
from app.core.exceptions import DataSourceError, ValidationError
from app.core.logging import get_logger
from app.core.responses import ResponseBuilder
from app.models.gene import GeneEvidence
from app.models.user import User
from app.pipeline.sources.unified import get_unified_source

logger = get_logger(__name__)

router = APIRouter()

# Define which sources support file uploads
UPLOAD_SOURCES = {"DiagnosticPanels", "Literature"}


@router.post("/{source_name}/upload")
async def upload_evidence_file(
    source_name: str,
    file: UploadFile = File(...),
    provider_name: str | None = Form(None),
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
    await logger.info(
        "Processing upload",
        source_name=source_name,
        filename=file.filename,
        file_size=file_size,
        provider_name=provider_name,
        uploaded_by=current_user.username,
        user_role=current_user.role,
    )

    try:
        # Get source processor
        await logger.info(
            "Getting source processor",
            source_name=source_name
        )
        source = get_unified_source(source_name, db_session=db)

        await logger.info(
            "Source processor obtained",
            source_class=source.__class__.__name__
        )

        # Process through source pipeline
        await logger.info(
            "Fetching raw data from file",
            file_extension=file_extension,
            provider_name=provider_name
        )
        raw_data = await source.fetch_raw_data(file_content, file_extension, provider_name)

        await logger.info(
            "Raw data fetched",
            row_count=len(raw_data) if hasattr(raw_data, '__len__') else 'unknown'
        )

        # Process data
        await logger.info("Processing raw data")
        processed_data = await source.process_data(raw_data)

        await logger.info(
            "Data processed",
            gene_count=len(processed_data) if processed_data else 0
        )

        # Set provider context for evidence creation
        source._current_provider = provider_name

        await logger.info(
            "Starting hybrid gene creation/evidence merging",
            provider=provider_name
        )

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
            total_batches=total_batches
        )

        genes_created = 0
        genes_updated = 0

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(gene_symbols))
            batch_symbols = gene_symbols[start_idx:end_idx]

            tracker.update(operation=f"Creating genes batch {batch_num + 1}/{total_batches}")

            await logger.debug(
                "Processing batch",
                batch_num=batch_num + 1,
                batch_size=len(batch_symbols)
            )

            # Normalize gene symbols and create missing genes
            normalization_results = await normalize_genes_batch_async(
                db, batch_symbols, source_name
            )

            await logger.debug(
                "Batch normalized",
                batch_num=batch_num + 1,
                normalized_count=len(normalization_results)
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
                batch_created=sum(1 for s in batch_symbols if normalization_results.get(s, {}).get("created")),
                batch_updated=sum(1 for s in batch_symbols if normalization_results.get(s, {}).get("status") == "normalized" and not normalization_results.get(s, {}).get("created"))
            )

        await logger.info(
            "Gene normalization complete",
            genes_created=genes_created,
            genes_updated=genes_updated
        )

        # Step 2: Store evidence using custom merge logic
        tracker.update(operation="Storing evidence with aggregation")

        await logger.info(
            "Starting evidence storage",
            gene_count=len(processed_data),
            provider=provider_name
        )

        evidence_stats = await source.store_evidence(db, processed_data, provider_name)

        await logger.info(
            "Evidence storage complete",
            stats=evidence_stats
        )

        db.commit()

        await logger.info("Database committed")

        # Convert to expected format
        stats = {
            "created": evidence_stats.get("created", 0) + genes_created,
            "merged": evidence_stats.get("merged", 0),
            "failed": evidence_stats.get("failed", 0),
            "filtered": evidence_stats.get("filtered", 0),
        }

        await logger.info(
            "Upload processing complete",
            final_stats=stats
        )

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
