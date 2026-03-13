"""Percentile management endpoints for gene annotations."""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.exceptions import ValidationError as DomainValidationError
from app.core.logging import get_logger
from app.models.user import User
from app.pipeline.tasks.percentile_updater import (
    update_percentiles_for_source,
    validate_percentiles,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post("/percentiles/refresh", dependencies=[Depends(require_admin)])
async def refresh_global_percentiles(
    background_tasks: BackgroundTasks,
    source: str = Query(..., description="Source to refresh (e.g., string_ppi)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Trigger global percentile recalculation for an annotation source.

    Admin only. Runs in background to avoid blocking.

    Args:
        source: Source name (string_ppi, gnomad, gtex)
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Admin user

    Returns:
        Status response
    """
    await logger.info(f"Percentile refresh requested for {source}", user_id=current_user.id)

    # Validate source
    valid_sources = ["string_ppi", "gnomad", "gtex"]
    if source not in valid_sources:
        raise DomainValidationError(
            field="source", reason=f"Invalid source. Must be one of: {valid_sources}"
        )

    # Schedule background task
    background_tasks.add_task(update_percentiles_for_source, db, source)

    return {
        "status": "scheduled",
        "source": source,
        "message": f"Global percentile recalculation scheduled for {source}",
    }


@router.get("/percentiles/validate/{source}")
async def validate_source_percentiles(
    source: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Validate percentile distribution for a source.

    Admin only. Checks if percentiles are correctly distributed.

    Args:
        source: Source name
        db: Database session

    Returns:
        Validation results
    """
    result = await validate_percentiles(db, source)
    return result
