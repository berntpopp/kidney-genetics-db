"""
Background tasks for updating global percentiles.

This module provides tasks for recalculating percentiles
for annotation sources like STRING PPI.
"""

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.percentile_service import PercentileService
from app.pipeline.sources.annotations.string_ppi import StringPPIAnnotationSource

logger = get_logger(__name__)


async def update_percentiles_for_source(db: Session, source: str) -> dict:
    """
    Update global percentiles for a specific annotation source.

    This task runs in the background and does not block the API.
    It's designed to be called after batch annotation updates.

    Args:
        db: Database session
        source: Source name (e.g., 'string_ppi')

    Returns:
        Status dictionary with results
    """
    await logger.info(f"Starting percentile update for {source}")

    result = {"source": source, "status": "unknown", "message": "", "gene_count": 0}

    try:
        if source == "string_ppi":
            # Use dedicated method for STRING
            string_source = StringPPIAnnotationSource(db)
            await string_source.recalculate_global_percentiles()
            result["status"] = "success"
            result["message"] = "STRING PPI percentiles updated successfully"

        elif source in ["gnomad", "gtex"]:
            # Generic percentile calculation for other sources
            service = PercentileService(db)
            percentiles = await service.calculate_global_percentiles(
                source,
                "score",
                force=True,  # Force recalculation for background task
            )
            result["status"] = "success"
            result["gene_count"] = len(percentiles)
            result["message"] = f"Updated {len(percentiles)} percentiles for {source}"

        else:
            result["status"] = "error"
            result["message"] = f"Unknown source: {source}"
            await logger.warning(f"Unknown source requested for percentile update: {source}")

        await logger.info(
            f"Percentile update completed for {source}",
            status=result["status"],
            gene_count=result["gene_count"],
        )

    except Exception as e:
        error_msg = f"Failed to update percentiles for {source}: {str(e)}"
        await logger.error(error_msg, exc_info=True)
        result["status"] = "error"
        result["message"] = error_msg

    return result


async def update_all_percentiles(db: Session) -> dict:
    """
    Update percentiles for all supported sources.

    This is useful for maintenance or after bulk updates.

    Args:
        db: Database session

    Returns:
        Summary of all updates
    """
    sources = ["string_ppi"]  # Add more as needed

    summary = {"total_sources": len(sources), "successful": 0, "failed": 0, "results": []}

    for source in sources:
        try:
            result = await update_percentiles_for_source(db, source)
            summary["results"].append(result)

            if result["status"] == "success":
                summary["successful"] += 1
            else:
                summary["failed"] += 1

        except Exception as e:
            await logger.error(f"Unexpected error updating {source}: {e}")
            summary["failed"] += 1
            summary["results"].append({"source": source, "status": "error", "message": str(e)})

    await logger.info(
        "Bulk percentile update completed",
        successful=summary["successful"],
        failed=summary["failed"],
    )

    return summary


async def validate_percentiles(db: Session, source: str) -> dict:
    """
    Validate that percentiles are correctly distributed.

    Args:
        db: Database session
        source: Source to validate

    Returns:
        Validation results
    """
    service = PercentileService(db)
    return await service.validate_percentiles(source)
