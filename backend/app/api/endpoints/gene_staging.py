"""
API endpoints for gene normalization staging management
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.crud.gene_staging import log_crud, staging_crud
from app.schemas.gene_staging import (
    GeneNormalizationLogResponse,
    GeneNormalizationStagingResponse,
    NormalizationStatsResponse,
    StagingApprovalRequest,
    StagingRejectionRequest,
    StagingStatsResponse,
)

router = APIRouter()

@router.get("/staging/pending", response_model=list[GeneNormalizationStagingResponse])
async def get_pending_reviews(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=200, description="Maximum number of records to return"),
    source_filter: str = Query(default=None, description="Filter by data source"),
) -> list[GeneNormalizationStagingResponse]:
    """
    Get genes pending manual review, ordered by priority
    """
    staging_records = staging_crud.get_pending_reviews(
        db=db, limit=limit, source_filter=source_filter
    )

    return [
        GeneNormalizationStagingResponse(
            id=record.id,
            original_text=record.original_text,
            source_name=record.source_name,
            original_data=record.original_data,
            normalization_log=record.normalization_log,
            status=record.status,
            priority_score=record.priority_score,
            requires_expert_review=record.requires_expert_review,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        for record in staging_records
    ]

@router.post("/staging/{staging_id}/approve")
async def approve_staging_record(
    *, db: Session = Depends(get_db), staging_id: int, approval_data: StagingApprovalRequest
) -> dict[str, Any]:
    """
    Approve a staging record with manual corrections
    """
    try:
        staging_record = staging_crud.approve_staging_record(
            db=db,
            staging_id=staging_id,
            approved_symbol=approval_data.approved_symbol,
            hgnc_id=approval_data.hgnc_id,
            aliases=approval_data.aliases,
            reviewer=approval_data.reviewer,
            notes=approval_data.notes,
        )

        return {
            "success": True,
            "message": f"Staging record {staging_id} approved",
            "approved_symbol": staging_record.manual_approved_symbol,
            "hgnc_id": staging_record.manual_hgnc_id,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error approving staging record: {e}") from e

@router.post("/staging/{staging_id}/reject")
async def reject_staging_record(
    *, db: Session = Depends(get_db), staging_id: int, rejection_data: StagingRejectionRequest
) -> dict[str, Any]:
    """
    Reject a staging record (not a valid gene)
    """
    try:
        staging_record = staging_crud.reject_staging_record(
            db=db,
            staging_id=staging_id,
            reviewer=rejection_data.reviewer,
            notes=rejection_data.notes,
        )

        return {
            "success": True,
            "message": f"Staging record {staging_id} rejected",
            "notes": staging_record.review_notes,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rejecting staging record: {e}") from e

@router.get("/staging/stats", response_model=StagingStatsResponse)
async def get_staging_stats(*, db: Session = Depends(get_db)) -> StagingStatsResponse:
    """
    Get statistics about staging records
    """
    stats = staging_crud.get_staging_stats(db)

    return StagingStatsResponse(
        total_pending=stats["total_pending"],
        total_approved=stats["total_approved"],
        total_rejected=stats["total_rejected"],
        by_source=stats["by_source"],
    )

@router.get("/normalization/stats", response_model=NormalizationStatsResponse)
async def get_normalization_stats(*, db: Session = Depends(get_db)) -> NormalizationStatsResponse:
    """
    Get statistics about gene normalization success rates
    """
    stats = log_crud.get_normalization_stats(db)

    return NormalizationStatsResponse(
        total_attempts=stats["total_attempts"],
        successful_attempts=stats["successful_attempts"],
        success_rate=stats["success_rate"],
        by_source=stats["by_source"],
    )

@router.get("/normalization/logs", response_model=list[GeneNormalizationLogResponse])
async def get_normalization_logs(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(default=100, le=500, description="Maximum number of logs to return"),
    source_filter: str = Query(default=None, description="Filter by data source"),
    success_filter: bool = Query(default=None, description="Filter by success status"),
) -> list[GeneNormalizationLogResponse]:
    """
    Get gene normalization logs for debugging and analysis
    """
    from sqlalchemy import and_, desc

    from app.models.gene_staging import GeneNormalizationLog

    query = db.query(GeneNormalizationLog)

    # Apply filters
    filters = []
    if source_filter:
        filters.append(GeneNormalizationLog.source_name == source_filter)
    if success_filter is not None:
        filters.append(GeneNormalizationLog.success == success_filter)

    if filters:
        query = query.filter(and_(*filters))

    logs = query.order_by(desc(GeneNormalizationLog.created_at)).limit(limit).all()

    return [
        GeneNormalizationLogResponse(
            id=log.id,
            original_text=log.original_text,
            source_name=log.source_name,
            success=log.success,
            approved_symbol=log.approved_symbol,
            hgnc_id=log.hgnc_id,
            normalization_log=log.normalization_log,
            api_calls_made=log.api_calls_made,
            processing_time_ms=log.processing_time_ms,
            created_at=log.created_at,
        )
        for log in logs
    ]

@router.post("/normalization/test")
def test_normalization(
    *,
    db: Session = Depends(get_db),
    gene_text: str = Query(description="Gene text to test normalization"),
    source_name: str = Query(default="Manual Test", description="Source name for testing"),
) -> dict[str, Any]:
    """
    Test gene normalization for a given gene text (for debugging)
    """
    from app.core.gene_normalization import normalize_gene_for_database

    try:
        result = normalize_gene_for_database(
            db=db, gene_text=gene_text, source_name=source_name, original_data={"test": True}
        )

        return {"success": True, "gene_text": gene_text, "result": result}

    except Exception as e:
        return {"success": False, "gene_text": gene_text, "error": str(e)}
