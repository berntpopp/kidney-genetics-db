"""
API endpoints for gene annotations.
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models.gene import Gene
from app.models.gene_annotation import AnnotationSource, GeneAnnotation
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource
from app.pipeline.sources.annotations.descartes import DescartesAnnotationSource
from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource
from app.pipeline.sources.annotations.gtex import GTExAnnotationSource
from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource
from app.pipeline.sources.annotations.hpo import HPOAnnotationSource
from app.pipeline.sources.annotations.mpo_mgi import MPOMGIAnnotationSource
from app.pipeline.sources.annotations.string_ppi import StringPPIAnnotationSource

logger = get_logger(__name__)
router = APIRouter()


@router.get("/genes/{gene_id}/annotations")
async def get_gene_annotations(
    gene_id: int,
    source: str | None = Query(
        None, description="Filter by annotation source (hgnc, gnomad, gtex)"
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get all annotations for a specific gene.

    Args:
        gene_id: Gene database ID
        source: Optional source filter
        db: Database session

    Returns:
        Dictionary with annotations grouped by source
    """
    from app.core.cache_service import get_cache_service

    # Check cache first
    cache_service = get_cache_service(db)
    cache_key = f"{gene_id}:{source or 'all'}"
    cached = await cache_service.get(key=cache_key, namespace="annotations", default=None)
    if cached:
        logger.sync_debug(f"Cache hit for gene {gene_id}", source=source)
        return cached

    # Get the gene
    gene = db.query(Gene).filter(Gene.id == gene_id).first()
    if not gene:
        raise HTTPException(status_code=404, detail="Gene not found")

    # Build query
    query = db.query(GeneAnnotation).filter(GeneAnnotation.gene_id == gene_id)

    if source:
        query = query.filter(GeneAnnotation.source == source)

    annotations = query.all()

    # Group by source
    result = {
        "gene": {"id": gene.id, "symbol": gene.approved_symbol, "hgnc_id": gene.hgnc_id},
        "annotations": {},
    }

    for ann in annotations:
        if ann.source not in result["annotations"]:
            result["annotations"][ann.source] = []

        result["annotations"][ann.source].append(
            {
                "version": ann.version,
                "data": ann.annotations,
                "metadata": ann.source_metadata,
                "updated_at": ann.updated_at.isoformat() if ann.updated_at else None,
            }
        )

    # Cache the result
    await cache_service.set(key=cache_key, value=result, namespace="annotations", ttl=3600)

    return result


@router.get("/genes/{gene_id}/annotations/summary")
async def get_gene_annotation_summary(
    gene_id: int, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Get annotation summary from materialized view for fast access.

    Args:
        gene_id: Gene database ID
        db: Database session

    Returns:
        Summary of key annotation fields
    """
    from app.core.cache_service import get_cache_service

    # Check cache first
    cache_service = get_cache_service(db)
    cache_key = f"summary:{gene_id}"
    cached = await cache_service.get(key=cache_key, namespace="annotations", default=None)
    if cached:
        logger.sync_debug(f"Cache hit for summary of gene {gene_id}")
        return cached

    result = db.execute(
        text("""
        SELECT
            gene_id,
            approved_symbol,
            hgnc_id,
            ncbi_gene_id,
            mane_select_transcript,
            ensembl_gene_id,
            pli,
            oe_lof,
            oe_lof_upper,
            oe_lof_lower,
            lof_z,
            mis_z,
            syn_z,
            oe_mis,
            oe_syn
        FROM gene_annotations_summary
        WHERE gene_id = :gene_id
    """),
        {"gene_id": gene_id},
    )

    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Gene annotation summary not found")

    summary = {
        "gene_id": row.gene_id,
        "symbol": row.approved_symbol,
        "hgnc_id": row.hgnc_id,
        "identifiers": {
            "ncbi_gene_id": row.ncbi_gene_id,
            "ensembl_gene_id": row.ensembl_gene_id,
            "mane_select_transcript": row.mane_select_transcript,
        },
        "constraint_scores": {
            "pli": row.pli,
            "oe_lof": row.oe_lof,
            "oe_lof_upper": row.oe_lof_upper,
            "oe_lof_lower": row.oe_lof_lower,
            "lof_z": row.lof_z,
            "mis_z": row.mis_z,
            "syn_z": row.syn_z,
            "oe_mis": row.oe_mis,
            "oe_syn": row.oe_syn,
        },
    }

    # Cache the result
    await cache_service.set(key=cache_key, value=summary, namespace="annotations", ttl=7200)

    return summary


@router.post("/genes/{gene_id}/annotations/update")
async def update_gene_annotations(
    gene_id: int,
    sources: list[str] = Query(
        ["hgnc", "gnomad", "gtex", "hpo", "clinvar", "string_ppi"], description="Sources to update"
    ),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Trigger annotation update for a specific gene.

    Args:
        gene_id: Gene database ID
        sources: List of sources to update
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Status message
    """
    # Get the gene
    gene = db.query(Gene).filter(Gene.id == gene_id).first()
    if not gene:
        raise HTTPException(status_code=404, detail="Gene not found")

    # Schedule background updates
    for source_name in sources:
        if source_name == "hgnc":
            background_tasks.add_task(_update_hgnc_annotation, gene, db)
        elif source_name == "gnomad":
            background_tasks.add_task(_update_gnomad_annotation, gene, db)
        elif source_name == "gtex":
            background_tasks.add_task(_update_gtex_annotation, gene, db)
        elif source_name == "descartes":
            background_tasks.add_task(_update_descartes_annotation, gene, db)
        elif source_name == "hpo":
            background_tasks.add_task(_update_hpo_annotation, gene, db)
        elif source_name == "clinvar":
            background_tasks.add_task(_update_clinvar_annotation, gene, db)
        elif source_name == "mpo_mgi":
            background_tasks.add_task(_update_mpo_mgi_annotation, gene, db)
        elif source_name == "string_ppi":
            background_tasks.add_task(_update_string_ppi_annotation, gene, db)

    return {
        "status": "update_scheduled",
        "gene_id": gene_id,
        "sources": sources,
        "message": f"Annotation update scheduled for {len(sources)} sources",
    }


async def _update_hgnc_annotation(gene: Gene, db: Session):
    """Background task to update HGNC annotation."""
    from app.core.cache_service import get_cache_service

    try:
        source = HGNCAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            # Invalidate cache for this gene
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")

            await logger.info("HGNC annotation updated for gene", gene_symbol=gene.approved_symbol)
        else:
            await logger.warning(
                "Failed to update HGNC annotation", gene_symbol=gene.approved_symbol
            )
    except Exception as e:
        await logger.error(
            f"Error updating HGNC annotation: {str(e)}", gene_symbol=gene.approved_symbol
        )


async def _update_gnomad_annotation(gene: Gene, db: Session):
    """Background task to update gnomAD annotation."""
    from app.core.cache_service import get_cache_service

    try:
        source = GnomADAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            # Invalidate cache for this gene
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")

            await logger.info(
                "gnomAD annotation updated for gene", gene_symbol=gene.approved_symbol
            )
        else:
            await logger.warning(
                "Failed to update gnomAD annotation", gene_symbol=gene.approved_symbol
            )
    except Exception as e:
        await logger.error(
            f"Error updating gnomAD annotation: {str(e)}", gene_symbol=gene.approved_symbol
        )


async def _update_gtex_annotation(gene: Gene, db: Session):
    """Background task to update GTEx annotation."""
    from app.core.cache_service import get_cache_service

    try:
        source = GTExAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            # Invalidate cache for this gene
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")

            await logger.info("GTEx annotation updated for gene", gene_symbol=gene.approved_symbol)
        else:
            await logger.warning(
                "Failed to update GTEx annotation", gene_symbol=gene.approved_symbol
            )
    except Exception as e:
        await logger.error(
            f"Error updating GTEx annotation: {str(e)}", gene_symbol=gene.approved_symbol
        )


async def _update_descartes_annotation(gene: Gene, db: Session):
    """Background task to update Descartes annotation."""
    from app.core.cache_service import get_cache_service

    try:
        source = DescartesAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            # Invalidate cache for this gene
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")

            await logger.info(
                "Descartes annotation updated for gene", gene_symbol=gene.approved_symbol
            )
        else:
            await logger.warning(
                "Failed to update Descartes annotation", gene_symbol=gene.approved_symbol
            )
    except Exception as e:
        await logger.error(
            f"Error updating Descartes annotation: {str(e)}", gene_symbol=gene.approved_symbol
        )


async def _update_hpo_annotation(gene: Gene, db: Session):
    """Background task to update HPO annotation."""
    from app.core.cache_service import get_cache_service

    try:
        source = HPOAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            # Invalidate cache for this gene
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")

            await logger.info("HPO annotation updated for gene", gene_symbol=gene.approved_symbol)
        else:
            await logger.warning(
                "Failed to update HPO annotation", gene_symbol=gene.approved_symbol
            )
    except Exception as e:
        await logger.error(
            f"Error updating HPO annotation: {str(e)}", gene_symbol=gene.approved_symbol
        )


async def _update_clinvar_annotation(gene: Gene, db: Session):
    """Background task to update ClinVar annotation."""
    from app.core.cache_service import get_cache_service

    try:
        source = ClinVarAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            # Invalidate cache for this gene
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")

            await logger.info(
                "ClinVar annotation updated for gene", gene_symbol=gene.approved_symbol
            )
        else:
            await logger.warning(
                "Failed to update ClinVar annotation", gene_symbol=gene.approved_symbol
            )
    except Exception as e:
        await logger.error(
            f"Error updating ClinVar annotation: {str(e)}", gene_symbol=gene.approved_symbol
        )


async def _update_mpo_mgi_annotation(gene: Gene, db: Session):
    """Background task to update MPO/MGI annotation."""
    from app.core.cache_service import get_cache_service

    try:
        source = MPOMGIAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            # Invalidate cache for this gene
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")

            await logger.info(
                "MPO/MGI annotation updated for gene", gene_symbol=gene.approved_symbol
            )
        else:
            await logger.warning(
                "Failed to update MPO/MGI annotation", gene_symbol=gene.approved_symbol
            )
    except Exception as e:
        await logger.error(
            f"Error updating MPO/MGI annotation: {str(e)}", gene_symbol=gene.approved_symbol
        )


async def _update_string_ppi_annotation(gene: Gene, db: Session):
    """Background task to update STRING PPI annotation."""
    from app.core.cache_service import get_cache_service

    try:
        source = StringPPIAnnotationSource(db)
        success = await source.update_gene(gene)

        if success:
            # Invalidate cache for this gene
            cache_service = get_cache_service(db)
            await cache_service.delete(f"{gene.id}:*", namespace="annotations")

            await logger.info(
                "STRING PPI annotation updated for gene", gene_symbol=gene.approved_symbol
            )
        else:
            await logger.warning(
                "Failed to update STRING PPI annotation", gene_symbol=gene.approved_symbol
            )
    except Exception as e:
        await logger.error(
            f"Error updating STRING PPI annotation: {str(e)}", gene_symbol=gene.approved_symbol
        )


@router.get("/sources")
async def get_annotation_sources(
    active_only: bool = Query(True, description="Only return active sources"),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Get list of available annotation sources.

    Args:
        active_only: Filter for active sources only
        db: Database session

    Returns:
        List of annotation sources with metadata
    """
    query = db.query(AnnotationSource)

    if active_only:
        query = query.filter(AnnotationSource.is_active.is_(True))

    sources = query.order_by(AnnotationSource.priority.desc()).all()

    return [
        {
            "source_name": source.source_name,
            "display_name": source.display_name,
            "description": source.description,
            "is_active": source.is_active,
            "last_update": source.last_update.isoformat() if source.last_update else None,
            "next_update": source.next_update.isoformat() if source.next_update else None,
            "update_frequency": source.update_frequency,
            "config": source.config,
        }
        for source in sources
    ]


@router.post("/refresh-view")
async def refresh_materialized_view(db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Refresh the gene_annotations_summary materialized view.

    Args:
        db: Database session

    Returns:
        Status message
    """
    try:
        # Try concurrent refresh first
        db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY gene_annotations_summary"))
        db.commit()

        return {"status": "success", "message": "Materialized view refreshed successfully"}
    except Exception:
        # Fall back to non-concurrent refresh
        try:
            db.execute(text("REFRESH MATERIALIZED VIEW gene_annotations_summary"))
            db.commit()

            return {"status": "success", "message": "Materialized view refreshed (non-concurrent)"}
        except Exception as e2:
            raise HTTPException(
                status_code=500, detail=f"Failed to refresh materialized view: {str(e2)}"
            ) from e2


@router.get("/statistics")
async def get_annotation_statistics(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get statistics about gene annotations.

    Args:
        db: Database session

    Returns:
        Statistics dictionary
    """
    # Get counts by source
    result = db.execute(
        text("""
        SELECT
            source,
            COUNT(DISTINCT gene_id) as gene_count,
            COUNT(*) as annotation_count,
            MAX(updated_at) as last_update
        FROM gene_annotations
        GROUP BY source
    """)
    )

    sources_stats = []
    for row in result:
        sources_stats.append(
            {
                "source": row.source,
                "gene_count": row.gene_count,
                "annotation_count": row.annotation_count,
                "last_update": row.last_update.isoformat() if row.last_update else None,
            }
        )

    # Get total unique genes with annotations
    total_result = db.execute(
        text("""
        SELECT COUNT(DISTINCT gene_id) as total_genes
        FROM gene_annotations
    """)
    )
    total_genes = total_result.scalar()

    # Get genes with both HGNC and gnomAD
    both_result = db.execute(
        text("""
        SELECT COUNT(DISTINCT h.gene_id) as genes_with_both
        FROM gene_annotations h
        INNER JOIN gene_annotations g ON h.gene_id = g.gene_id
        WHERE h.source = 'hgnc' AND g.source = 'gnomad'
    """)
    )
    genes_with_both = both_result.scalar()

    return {
        "total_genes_with_annotations": total_genes,
        "genes_with_both_sources": genes_with_both,
        "sources": sources_stats,
        "materialized_view": {
            "name": "gene_annotations_summary",
            "description": "Pre-computed view with key annotation fields for fast access",
        },
    }


# Pipeline Management Endpoints


@router.post("/pipeline/update")
async def trigger_pipeline_update(
    strategy: str = Query(
        "incremental", description="Update strategy: full, incremental, forced, selective"
    ),
    sources: list[str] | None = Query(None, description="Specific sources to update"),
    gene_ids: list[int] | None = Query(None, description="Specific gene IDs to update"),
    force: bool = Query(False, description="Force update regardless of TTL"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
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
    import uuid

    from app.pipeline.annotation_pipeline import UpdateStrategy

    # Validate strategy
    try:
        update_strategy = UpdateStrategy(strategy)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy. Must be one of: {[s.value for s in UpdateStrategy]}",
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


async def _run_pipeline_update(
    strategy, sources: list[str] | None, gene_ids: list[int] | None, force: bool, task_id: str
):
    """Background task to run pipeline update."""
    from app.core.database import SessionLocal
    from app.pipeline.annotation_pipeline import AnnotationPipeline

    # Create new database session for background task
    db = SessionLocal()

    try:
        pipeline = AnnotationPipeline(db)
        results = await pipeline.run_update(
            strategy=strategy, sources=sources, gene_ids=gene_ids, force=force, task_id=task_id
        )

        await logger.info("Pipeline update completed", task_id=task_id, results=results)
    except Exception as e:
        import traceback

        await logger.error(
            f"Pipeline update failed: {str(e)}", task_id=task_id, traceback=traceback.format_exc()
        )
    finally:
        db.close()


@router.get("/pipeline/status")
async def get_pipeline_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get annotation pipeline status.

    Args:
        db: Database session

    Returns:
        Pipeline status information
    """
    from app.pipeline.annotation_pipeline import AnnotationPipeline

    pipeline = AnnotationPipeline(db)
    source_status = await pipeline.check_source_status()

    return {
        "sources": source_status,
        "pipeline_ready": all(s["is_active"] for s in source_status),
        "updates_due": [s["source"] for s in source_status if s["update_due"]],
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


@router.get("/scheduler/jobs")
async def get_scheduled_jobs() -> dict[str, Any]:
    """
    Get list of scheduled annotation update jobs.

    Returns:
        List of scheduled jobs with their status
    """
    from app.core.scheduler import annotation_scheduler

    jobs = annotation_scheduler.get_jobs()

    return {
        "scheduler_running": annotation_scheduler.is_running,
        "jobs": jobs,
        "total_jobs": len(jobs),
    }


@router.post("/scheduler/trigger/{job_id}")
async def trigger_scheduled_job(job_id: str) -> dict[str, Any]:
    """
    Manually trigger a scheduled job.

    Args:
        job_id: ID of the job to trigger

    Returns:
        Trigger status
    """
    from app.core.scheduler import annotation_scheduler

    success = annotation_scheduler.trigger_job(job_id)

    if success:
        return {
            "status": "triggered",
            "job_id": job_id,
            "message": f"Job {job_id} has been triggered",
        }
    else:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


# Cache management endpoints have been moved to /api/admin/cache
# Use the unified cache management API for all cache operations:
# - GET /api/admin/cache/stats - Get cache statistics
# - DELETE /api/admin/cache/annotations - Clear annotation namespace
# - DELETE /api/admin/cache/annotations/{key} - Delete specific cache key


@router.post("/batch")
async def batch_get_annotations(
    gene_ids: list[int],
    sources: list[str] | None = Query(None, description="Filter by sources"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get annotations for multiple genes in batch.

    Args:
        gene_ids: List of gene IDs
        sources: Optional source filter
        db: Database session

    Returns:
        Batch annotation results
    """
    # Limit batch size
    if len(gene_ids) > 100:
        raise HTTPException(status_code=400, detail="Batch size limited to 100 genes")

    # Build query
    query = db.query(GeneAnnotation).filter(GeneAnnotation.gene_id.in_(gene_ids))

    if sources:
        query = query.filter(GeneAnnotation.source.in_(sources))

    annotations = query.all()

    # Group by gene
    results = {}
    for ann in annotations:
        if ann.gene_id not in results:
            results[ann.gene_id] = {}

        if ann.source not in results[ann.gene_id]:
            results[ann.gene_id][ann.source] = []

        results[ann.gene_id][ann.source].append(
            {
                "version": ann.version,
                "data": ann.annotations,
                "updated_at": ann.updated_at.isoformat() if ann.updated_at else None,
            }
        )

    # Get gene info
    genes = db.query(Gene).filter(Gene.id.in_(gene_ids)).all()
    gene_info = {g.id: {"symbol": g.approved_symbol, "hgnc_id": g.hgnc_id} for g in genes}

    return {
        "genes": gene_info,
        "annotations": results,
        "total_genes": len(gene_ids),
        "genes_with_annotations": len(results),
    }
