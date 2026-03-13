"""POST/PUT/DELETE endpoints for gene annotations — write operations and pipeline management."""

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.exceptions import GeneNotFoundError
from app.core.exceptions import ValidationError as DomainValidationError
from app.core.logging import get_logger
from app.core.rate_limit import LIMIT_PIPELINE, limiter
from app.db.safe_sql import refresh_materialized_view as safe_refresh_matview
from app.models.gene import Gene
from app.models.gene_annotation import AnnotationSource, GeneAnnotation
from app.models.user import User
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource
from app.pipeline.sources.annotations.descartes import DescartesAnnotationSource
from app.pipeline.sources.annotations.ensembl import EnsemblAnnotationSource
from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource
from app.pipeline.sources.annotations.gtex import GTExAnnotationSource
from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource
from app.pipeline.sources.annotations.hpo import HPOAnnotationSource
from app.pipeline.sources.annotations.mpo_mgi import MPOMGIAnnotationSource
from app.pipeline.sources.annotations.string_ppi import StringPPIAnnotationSource
from app.pipeline.sources.annotations.uniprot import UniProtAnnotationSource

router = APIRouter()
logger = get_logger(__name__)

# Source class mapping for single-gene updates
SOURCE_CLASSES: dict[str, type] = {
    "hgnc": HGNCAnnotationSource,
    "gnomad": GnomADAnnotationSource,
    "gtex": GTExAnnotationSource,
    "hpo": HPOAnnotationSource,
    "clinvar": ClinVarAnnotationSource,
    "string_ppi": StringPPIAnnotationSource,
    "ensembl": EnsemblAnnotationSource,
    "uniprot": UniProtAnnotationSource,
    "mpo_mgi": MPOMGIAnnotationSource,
    "descartes": DescartesAnnotationSource,
}


@router.post("/genes/{gene_id}/annotations/update", dependencies=[Depends(require_admin)])
async def update_gene_annotations(
    gene_id: int,
    background_tasks: BackgroundTasks,
    sources: list[str] = Query(
        ["hgnc", "gnomad", "gtex", "hpo", "clinvar", "string_ppi", "ensembl", "uniprot"],
        description="Sources to update",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Trigger annotation update for a specific gene.

    Args:
        gene_id: Gene database ID
        sources: Sources to update
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Admin user

    Returns:
        Update status
    """
    await logger.info(
        "Admin action: Gene annotation update triggered",
        user_id=current_user.id,
        username=current_user.username,
        gene_id=gene_id,
        sources=sources,
    )

    # Get the gene
    gene = db.query(Gene).filter(Gene.id == gene_id).first()
    if not gene:
        raise GeneNotFoundError(gene_id)

    # Schedule annotation updates for requested sources
    for source_name in sources:
        source_class = SOURCE_CLASSES.get(source_name)
        if source_class:
            background_tasks.add_task(
                _update_single_source, gene, source_name, source_class, db
            )

    return {
        "status": "update_scheduled",
        "gene_id": gene_id,
        "sources": sources,
        "message": f"Annotation update scheduled for {len(sources)} sources",
    }


async def _update_single_source(
    gene: Gene, source_name: str, source_class: type, db: Session
) -> None:
    """Update a single annotation source for a gene."""
    from app.core.cache_service import get_cache_service

    try:
        source_instance = source_class(db)
        success = await source_instance.update_gene(gene)

        if success:
            # Invalidate cache for this gene
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")

            await logger.info(
                f"{source_name} annotation updated for gene",
                gene_symbol=gene.approved_symbol,
            )
        else:
            await logger.warning(
                f"Failed to update {source_name} annotation",
                gene_symbol=gene.approved_symbol,
            )
    except Exception as e:
        await logger.error(
            f"Error updating {source_name} annotation: {str(e)}",
            gene_symbol=gene.approved_symbol,
        )


@router.post("/refresh-view", dependencies=[Depends(require_admin)])
async def refresh_materialized_view(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, str]:
    """
    Refresh the gene_annotations_summary materialized view.

    Args:
        db: Database session

    Returns:
        Status message
    """
    await logger.info(
        "Admin action: Materialized view refresh triggered",
        user_id=current_user.id,
        username=current_user.username,
    )

    views_to_refresh = ["gene_scores", "gene_annotations_summary"]
    results = []

    for view_name in views_to_refresh:
        try:
            await run_in_threadpool(safe_refresh_matview, db, view_name, True)
            results.append(f"{view_name}: refreshed concurrently")
        except Exception:
            try:
                await run_in_threadpool(safe_refresh_matview, db, view_name, False)
                results.append(f"{view_name}: refreshed (non-concurrent)")
            except Exception as e2:
                raise HTTPException(
                    status_code=500, detail=f"Failed to refresh {view_name}: {str(e2)}"
                ) from e2

    return {"status": "success", "message": "; ".join(results)}


# Pipeline Management Endpoints


@router.post("/pipeline/update", dependencies=[Depends(require_admin)])
@limiter.limit(LIMIT_PIPELINE)
async def trigger_pipeline_update(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    strategy: str = Query(
        "incremental", description="Update strategy: full, incremental, forced, selective"
    ),
    sources: list[str] | None = Query(None, description="Specific sources to update"),
    gene_ids: list[int] | None = Query(None, description="Specific gene IDs to update"),
    force: bool = Query(False, description="Force update regardless of TTL"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Trigger annotation pipeline update.

    Args:
        strategy: Update strategy to use
        sources: Optional list of sources to update
        gene_ids: Optional list of gene IDs to update
        force: Force update regardless of schedule
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Update task information
    """
    await logger.info(
        "Admin action: Pipeline update triggered",
        user_id=current_user.id,
        username=current_user.username,
        strategy=strategy,
        sources=sources,
        force=force,
    )

    from app.pipeline.annotation_pipeline import UpdateStrategy

    # Validate strategy
    try:
        update_strategy = UpdateStrategy(strategy)
    except ValueError as e:
        raise DomainValidationError(
            field="strategy",
            reason=f"Invalid strategy. Must be one of: {[s.value for s in UpdateStrategy]}",
        ) from e

    # Generate task ID
    task_id = str(uuid.uuid4())

    # Schedule background update
    background_tasks.add_task(
        _run_pipeline_update, update_strategy, sources, gene_ids, force, task_id
    )

    return {
        "task_id": task_id,
        "status": "scheduled",
        "strategy": strategy,
        "sources": sources,
        "gene_count": len(gene_ids) if gene_ids else "all",
        "force": force,
        "message": "Pipeline update scheduled. Use task_id to track progress.",
    }


@router.post("/pipeline/update-failed", dependencies=[Depends(require_admin)])
@limiter.limit(LIMIT_PIPELINE)
async def update_failed_annotations(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    sources: list[str] | None = Query(None, description="Specific sources to retry"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Retry annotations for genes that failed in the last pipeline run.

    Args:
        sources: Optional list of sources to filter failed genes
        db: Database session

    Returns:
        Update result with count of genes being retried
    """
    from app.pipeline.annotation_pipeline import UpdateStrategy

    await logger.info(
        "Admin action: Failed annotations update requested",
        user_id=current_user.id,
        username=current_user.username,
        sources=sources,
    )
    await logger.info("Failed annotations update requested", sources=sources)

    # Query genes that have incomplete annotations
    from sqlalchemy import and_, exists

    from app.models.gene import GeneCuration

    # Find genes with evidence score but missing/incomplete annotations
    failed_query = (
        db.query(Gene)
        .join(GeneCuration, GeneCuration.gene_id == Gene.id)
        .filter(
            and_(
                GeneCuration.evidence_score > 0, ~exists().where(GeneAnnotation.gene_id == Gene.id)
            )
        )
    )

    failed_genes = failed_query.limit(50).all()  # Limit to 50 genes at a time

    if not failed_genes:
        await logger.info("No failed genes found to retry")
        return {"message": "No failed genes to retry", "count": 0, "status": "completed"}

    # Generate task ID
    task_id = str(uuid.uuid4())

    # Schedule background update
    background_tasks.add_task(
        _run_pipeline_update,
        UpdateStrategy.INCREMENTAL,
        sources,
        [g.id for g in failed_genes],
        False,  # force
        task_id,
    )

    await logger.info(
        "Failed annotations update scheduled", gene_count=len(failed_genes), task_id=task_id
    )

    return {
        "task_id": task_id,
        "status": "scheduled",
        "message": f"Scheduled retry for {len(failed_genes)} failed genes",
        "count": len(failed_genes),
        "gene_ids": [g.id for g in failed_genes][:10],  # First 10 for preview
    }


@router.post("/pipeline/update-new", dependencies=[Depends(require_admin)])
@limiter.limit(LIMIT_PIPELINE)
async def update_new_genes(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    days_back: int = Query(7, description="Number of days to look back for new genes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Process genes added recently without annotations.

    Args:
        days_back: Number of days to look back for new genes
        db: Database session

    Returns:
        Update result with count of new genes being processed
    """
    from app.pipeline.annotation_pipeline import UpdateStrategy

    await logger.info(
        "Admin action: New genes update requested",
        user_id=current_user.id,
        username=current_user.username,
        days_back=days_back,
    )
    await logger.info("New genes update requested", days_back=days_back)

    # Query genes without annotations, ordered by clinical importance
    from sqlalchemy import func

    from app.models.gene import GeneCuration

    new_genes = (
        db.query(Gene)
        .outerjoin(GeneAnnotation, Gene.id == GeneAnnotation.gene_id)
        .outerjoin(GeneCuration, Gene.id == GeneCuration.gene_id)
        .filter(GeneAnnotation.id.is_(None))
        .order_by(func.coalesce(GeneCuration.evidence_score, 0).desc(), Gene.id)
        .all()
    )

    # If no genes found, return early
    if not new_genes:
        await logger.info("No new genes without annotations found")
        return {"message": "No new genes found", "count": 0, "status": "completed"}

    # Generate task ID
    task_id = str(uuid.uuid4())

    # Schedule background update
    background_tasks.add_task(
        _run_pipeline_update,
        UpdateStrategy.FULL,
        None,  # sources
        [g.id for g in new_genes],
        False,  # force
        task_id,
    )

    await logger.info("New genes update scheduled", gene_count=len(new_genes), task_id=task_id)

    return {
        "task_id": task_id,
        "status": "scheduled",
        "message": f"Scheduled processing for {len(new_genes)} new genes",
        "count": len(new_genes),
        "gene_ids": [g.id for g in new_genes][:10],  # First 10 for preview
    }


@router.post("/pipeline/update-missing/{source_name}", dependencies=[Depends(require_admin)])
@limiter.limit(LIMIT_PIPELINE)
async def update_missing_source(
    request: Request,
    response: Response,
    source_name: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Update genes missing annotations from specific source.

    Args:
        source_name: Name of the annotation source
        db: Database session

    Returns:
        Update result with count of genes being updated
    """
    await logger.info(
        "Admin action: Missing source update requested",
        user_id=current_user.id,
        username=current_user.username,
        source=source_name,
    )
    await logger.info("Missing source update requested", source=source_name)

    # Validate source exists
    source = db.query(AnnotationSource).filter_by(source_name=source_name, is_active=True).first()

    if not source:
        raise GeneNotFoundError(source_name)

    # Generate task ID
    task_id = str(uuid.uuid4())

    # Schedule background update - the heavy query will be done in the background
    background_tasks.add_task(_run_missing_source_update, source_name, task_id)

    await logger.info(f"{source_name} missing update scheduled", task_id=task_id)

    return {
        "task_id": task_id,
        "status": "scheduled",
        "message": f"Scheduled update for genes missing {source_name} annotations",
        "source": source_name,
        "description": "Finding and updating genes without this source's annotations",
    }


@router.post("/pipeline/validate")
async def validate_annotations(
    source: str | None = Query(None, description="Specific source to validate"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Validate annotation data consistency.

    Args:
        source: Optional source to validate
        db: Database session

    Returns:
        Validation results
    """
    from app.pipeline.annotation_pipeline import AnnotationPipeline

    pipeline = AnnotationPipeline(db)
    results = await pipeline.validate_annotations(source)

    return results


@router.post("/scheduler/trigger/{job_id}", dependencies=[Depends(require_admin)])
async def trigger_scheduled_job(
    job_id: str,
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Manually trigger a scheduled job.

    Args:
        job_id: ID of the job to trigger

    Returns:
        Trigger status
    """
    await logger.info(
        "Admin action: Scheduled job triggered",
        user_id=current_user.id,
        username=current_user.username,
        job_id=job_id,
    )

    from app.core.scheduler import annotation_scheduler

    success = annotation_scheduler.trigger_job(job_id)

    if success:
        return {
            "status": "triggered",
            "job_id": job_id,
            "message": f"Job {job_id} has been triggered",
        }
    else:
        raise GeneNotFoundError(job_id)


@router.delete("/reset")
async def reset_gene_annotations(
    background_tasks: BackgroundTasks,
    source: str | None = None,
    gene_ids: list[int] | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Reset/clear gene annotations from the database.

    This endpoint allows administrators to clear annotation data, optionally filtered
    by source and/or specific gene IDs.

    Args:
        source: Optional source name to filter deletions
        gene_ids: Optional list of gene IDs to limit the reset
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Current authenticated user (must be admin)

    Returns:
        Dictionary with deletion confirmation and statistics
    """
    task_id = str(uuid.uuid4())

    await logger.warning(
        "Gene annotation reset requested",
        task_id=task_id,
        user_id=current_user.id if current_user else None,
        source=source,
        gene_ids_count=len(gene_ids) if gene_ids else None,
    )

    # Run the actual reset in the background
    background_tasks.add_task(
        _run_annotation_reset,
        source=source,
        gene_ids=gene_ids,
        task_id=task_id,
        user_id=current_user.id if current_user else None,
    )

    return {
        "status": "accepted",
        "task_id": task_id,
        "message": f"Annotation reset initiated for {source or 'all sources'}",
        "affected_genes": len(gene_ids) if gene_ids else "all",
    }


# Background task helpers


async def _run_pipeline_update(
    strategy: Any,
    sources: list[str] | None,
    gene_ids: list[int] | None,
    force: bool,
    task_id: str,
) -> None:
    """Background task to run pipeline update."""
    await logger.info(
        "Background pipeline update started",
        task_id=task_id,
        strategy=strategy.value if hasattr(strategy, "value") else strategy,
        sources=sources,
        gene_ids=gene_ids[:5] if gene_ids else None,
        force=force,
    )

    from app.core.database import SessionLocal
    from app.pipeline.annotation_pipeline import AnnotationPipeline

    # Create new database session for background task
    db = SessionLocal()

    try:
        await logger.debug("Creating AnnotationPipeline instance", task_id=task_id)
        pipeline = AnnotationPipeline(db)

        await logger.debug("Starting pipeline.run_update", task_id=task_id)
        results = await pipeline.run_update(
            strategy=strategy, sources=sources, gene_ids=gene_ids, force=force, task_id=task_id
        )

        await logger.info(
            "Pipeline update completed",
            task_id=task_id,
            results=results,
            sources_updated=results.get("sources_updated", []),
            genes_updated=results.get("genes_updated", 0),
        )
    except Exception as e:
        import traceback

        await logger.error(
            f"Pipeline update failed: {str(e)}",
            task_id=task_id,
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
        )
    finally:
        db.close()
        await logger.debug("Database session closed", task_id=task_id)


async def _run_missing_source_update(source_name: str, task_id: str) -> None:
    """Background task to update genes missing a specific source."""
    await logger.info(
        "Background missing source update started", task_id=task_id, source=source_name
    )

    from sqlalchemy import exists

    from app.core.database import SessionLocal
    from app.pipeline.annotation_pipeline import AnnotationPipeline, UpdateStrategy

    # Create new database session for background task
    db = SessionLocal()

    try:
        # Find genes without this source's annotations
        genes_with_source_subq = exists().where(
            GeneAnnotation.gene_id == Gene.id, GeneAnnotation.source == source_name
        )

        # Order by evidence_score DESC to prioritize clinically important genes
        from sqlalchemy import func

        from app.models.gene import GeneCuration

        missing_genes = (
            db.query(Gene)
            .outerjoin(GeneCuration, Gene.id == GeneCuration.gene_id)
            .filter(~genes_with_source_subq)
            .order_by(func.coalesce(GeneCuration.evidence_score, 0).desc(), Gene.id)
            .all()
        )

        if not missing_genes:
            await logger.info(f"All genes have {source_name} annotations", task_id=task_id)
            return

        await logger.info(
            f"Found {len(missing_genes)} genes missing {source_name}", task_id=task_id
        )

        # Create pipeline instance and run update
        pipeline = AnnotationPipeline(db)
        results = await pipeline.run_update(
            strategy=UpdateStrategy.SELECTIVE,
            sources=[source_name],
            gene_ids=[g.id for g in missing_genes],
            force=False,
            task_id=task_id,
        )

        await logger.info(
            f"Missing source update completed for {source_name}",
            task_id=task_id,
            gene_count=len(missing_genes),
            results=results,
        )
    except Exception as e:
        import traceback

        await logger.error(
            f"Missing source update failed for {source_name}: {str(e)}",
            task_id=task_id,
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
        )
    finally:
        db.close()
        await logger.debug("Database session closed", task_id=task_id)


async def _run_annotation_reset(
    source: str | None, gene_ids: list[int] | None, task_id: str, user_id: int | None
) -> None:
    """Background task to reset gene annotations."""
    from app.core.database import SessionLocal

    db = SessionLocal()

    try:
        await logger.info(
            "Starting annotation reset",
            task_id=task_id,
            source=source,
            gene_ids_count=len(gene_ids) if gene_ids else None,
        )

        # Build the query
        query = db.query(GeneAnnotation)

        # Apply filters
        if source:
            query = query.filter(GeneAnnotation.source == source)
        if gene_ids:
            query = query.filter(GeneAnnotation.gene_id.in_(gene_ids))

        # Count before deletion for logging
        count_before = query.count()

        # Perform the deletion
        query.delete(synchronize_session=False)
        db.commit()

        # Clear cache for affected data
        from app.core.cache_service import get_cache_service

        cache = get_cache_service(db)

        # Clear annotation cache namespace
        await cache.clear_namespace("annotations")

        await logger.info(
            "Annotation reset completed",
            task_id=task_id,
            user_id=user_id,
            source=source,
            deleted_count=count_before,
            gene_ids_count=len(gene_ids) if gene_ids else None,
        )

    except Exception as e:
        import traceback

        await logger.error(
            f"Annotation reset failed: {str(e)}",
            task_id=task_id,
            user_id=user_id,
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
        )
        raise
    finally:
        db.close()
