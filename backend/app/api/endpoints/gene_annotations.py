"""
API endpoints for gene annotations.
"""

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.logging import get_logger
from app.models.gene import Gene
from app.models.gene_annotation import AnnotationSource, GeneAnnotation
from app.models.user import User
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource
from app.pipeline.sources.annotations.descartes import DescartesAnnotationSource
from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource
from app.pipeline.sources.annotations.gtex import GTExAnnotationSource
from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource
from app.pipeline.sources.annotations.hpo import HPOAnnotationSource
from app.pipeline.sources.annotations.mpo_mgi import MPOMGIAnnotationSource
from app.pipeline.sources.annotations.string_ppi import StringPPIAnnotationSource
from app.pipeline.tasks.percentile_updater import (
    update_percentiles_for_source,
    validate_percentiles,
)

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
    background_tasks: BackgroundTasks,
    sources: list[str] = Query(
        ["hgnc", "gnomad", "gtex", "hpo", "clinvar", "string_ppi"], description="Sources to update"
    ),
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
            # Transaction is already committed by store_annotation when not in batch mode
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
    await logger.info(
        f"Percentile refresh requested for {source}",
        user_id=current_user.id
    )

    # Validate source
    valid_sources = ["string_ppi", "gnomad", "gtex"]
    if source not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {valid_sources}"
        )

    # Schedule background task
    background_tasks.add_task(
        update_percentiles_for_source,
        db,
        source
    )

    return {
        "status": "scheduled",
        "source": source,
        "message": f"Global percentile recalculation scheduled for {source}"
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
    background_tasks: BackgroundTasks,
    strategy: str = Query(
        "incremental", description="Update strategy: full, incremental, forced, selective"
    ),
    sources: list[str] | None = Query(None, description="Specific sources to update"),
    gene_ids: list[int] | None = Query(None, description="Specific gene IDs to update"),
    force: bool = Query(False, description="Force update regardless of TTL"),
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


@router.post("/pipeline/update-failed")
async def update_failed_annotations(
    background_tasks: BackgroundTasks,
    sources: list[str] | None = Query(None, description="Specific sources to retry"),
    db: Session = Depends(get_db),
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

    await logger.info("Failed annotations update requested", sources=sources)

    # Query genes that have incomplete annotations
    # We'll define "failed" as genes with evidence score but missing annotations
    from sqlalchemy import and_, exists

    from app.models.gene import GeneCuration
    from app.models.gene_annotation import GeneAnnotation

    # Find genes with evidence score but missing/incomplete annotations
    failed_query = db.query(Gene).join(
        GeneCuration,
        GeneCuration.gene_id == Gene.id
    ).filter(
        and_(
            GeneCuration.evidence_score > 0,
            ~exists().where(GeneAnnotation.gene_id == Gene.id)
        )
    )

    failed_genes = failed_query.limit(50).all()  # Limit to 50 genes at a time

    if not failed_genes:
        await logger.info("No failed genes found to retry")
        return {"message": "No failed genes to retry", "count": 0, "status": "completed"}

    # Generate task ID
    import uuid
    task_id = str(uuid.uuid4())

    # Schedule background update
    background_tasks.add_task(
        _run_pipeline_update,
        UpdateStrategy.INCREMENTAL,
        sources,
        [g.id for g in failed_genes],
        False,  # force
        task_id
    )

    await logger.info(
        "Failed annotations update scheduled",
        gene_count=len(failed_genes),
        task_id=task_id
    )

    return {
        "task_id": task_id,
        "status": "scheduled",
        "message": f"Scheduled retry for {len(failed_genes)} failed genes",
        "count": len(failed_genes),
        "gene_ids": [g.id for g in failed_genes][:10],  # First 10 for preview
    }


@router.post("/pipeline/update-new")
async def update_new_genes(
    background_tasks: BackgroundTasks,
    days_back: int = Query(7, description="Number of days to look back for new genes"),
    db: Session = Depends(get_db),
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

    await logger.info("New genes update requested", days_back=days_back)

    # Query genes without annotations
    # Using left outer join to find genes with no annotations
    new_genes = db.query(Gene).outerjoin(
        GeneAnnotation,
        Gene.id == GeneAnnotation.gene_id
    ).filter(
        GeneAnnotation.id.is_(None)
    ).all()

    # If no genes found, return early
    if not new_genes:
        await logger.info("No new genes without annotations found")
        return {"message": "No new genes found", "count": 0, "status": "completed"}

    # Generate task ID
    import uuid
    task_id = str(uuid.uuid4())

    # Schedule background update
    background_tasks.add_task(
        _run_pipeline_update,
        UpdateStrategy.FULL,
        None,  # sources
        [g.id for g in new_genes],
        False,  # force
        task_id
    )

    await logger.info(
        "New genes update scheduled",
        gene_count=len(new_genes),
        task_id=task_id
    )

    return {
        "task_id": task_id,
        "status": "scheduled",
        "message": f"Scheduled processing for {len(new_genes)} new genes",
        "count": len(new_genes),
        "gene_ids": [g.id for g in new_genes][:10],  # First 10 for preview
    }


@router.post("/pipeline/update-missing/{source_name}")
async def update_missing_source(
    source_name: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Update genes missing annotations from specific source.

    Args:
        source_name: Name of the annotation source
        db: Database session

    Returns:
        Update result with count of genes being updated
    """

    await logger.info("Missing source update requested", source=source_name)

    # Validate source exists
    source = db.query(AnnotationSource).filter_by(
        source_name=source_name,
        is_active=True
    ).first()

    if not source:
        raise HTTPException(
            status_code=404,
            detail=f"Source {source_name} not found or inactive"
        )

    # Generate task ID
    import uuid
    task_id = str(uuid.uuid4())

    # Schedule background update - the heavy query will be done in the background
    background_tasks.add_task(
        _run_missing_source_update,
        source_name,
        task_id
    )

    await logger.info(
        f"{source_name} missing update scheduled",
        task_id=task_id
    )

    return {
        "task_id": task_id,
        "status": "scheduled",
        "message": f"Scheduled update for genes missing {source_name} annotations",
        "source": source_name,
        "description": "Finding and updating genes without this source's annotations"
    }


async def _run_pipeline_update(
    strategy, sources: list[str] | None, gene_ids: list[int] | None, force: bool, task_id: str
):
    """Background task to run pipeline update."""
    await logger.info(
        "Background pipeline update started",
        task_id=task_id,
        strategy=strategy.value if hasattr(strategy, 'value') else strategy,
        sources=sources,
        gene_ids=gene_ids[:5] if gene_ids else None,
        force=force
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
            genes_updated=results.get("genes_updated", 0)
        )
    except Exception as e:
        import traceback

        await logger.error(
            f"Pipeline update failed: {str(e)}",
            task_id=task_id,
            error_type=type(e).__name__,
            traceback=traceback.format_exc()
        )
    finally:
        db.close()
        await logger.debug("Database session closed", task_id=task_id)


async def _run_missing_source_update(source_name: str, task_id: str):
    """Background task to update genes missing a specific source."""
    await logger.info(
        "Background missing source update started",
        task_id=task_id,
        source=source_name
    )

    from sqlalchemy import exists

    from app.core.database import SessionLocal
    from app.pipeline.annotation_pipeline import AnnotationPipeline, UpdateStrategy

    # Create new database session for background task
    db = SessionLocal()

    try:
        # Find genes without this source's annotations
        # This heavy query now runs in background
        genes_with_source_subq = exists().where(
            GeneAnnotation.gene_id == Gene.id,
            GeneAnnotation.source == source_name
        )

        missing_genes = db.query(Gene).filter(
            ~genes_with_source_subq
        ).all()

        if not missing_genes:
            await logger.info(
                f"All genes have {source_name} annotations",
                task_id=task_id
            )
            return

        await logger.info(
            f"Found {len(missing_genes)} genes missing {source_name}",
            task_id=task_id
        )

        # Create pipeline instance and run update
        pipeline = AnnotationPipeline(db)
        results = await pipeline.run_update(
            strategy=UpdateStrategy.SELECTIVE,
            sources=[source_name],
            gene_ids=[g.id for g in missing_genes],
            force=False,
            task_id=task_id
        )

        await logger.info(
            f"Missing source update completed for {source_name}",
            task_id=task_id,
            gene_count=len(missing_genes),
            results=results
        )
    except Exception as e:
        import traceback
        await logger.error(
            f"Missing source update failed for {source_name}: {str(e)}",
            task_id=task_id,
            error_type=type(e).__name__,
            traceback=traceback.format_exc()
        )
    finally:
        db.close()
        await logger.debug("Database session closed", task_id=task_id)


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
    by source and/or specific gene IDs. This is useful for:
    - Forcing a complete refresh of annotation data
    - Clearing corrupted or outdated annotations
    - Resetting specific sources before re-importing

    Args:
        source: Optional source name to filter deletions (e.g., 'hgnc', 'clinvar')
        gene_ids: Optional list of gene IDs to limit the reset to specific genes
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
        gene_ids_count=len(gene_ids) if gene_ids else None
    )

    # Run the actual reset in the background
    background_tasks.add_task(
        _run_annotation_reset,
        source=source,
        gene_ids=gene_ids,
        task_id=task_id,
        user_id=current_user.id if current_user else None
    )

    return {
        "status": "accepted",
        "task_id": task_id,
        "message": f"Annotation reset initiated for {source or 'all sources'}",
        "affected_genes": len(gene_ids) if gene_ids else "all",
    }


async def _run_annotation_reset(
    source: str | None,
    gene_ids: list[int] | None,
    task_id: str,
    user_id: int | None
):
    """Background task to reset gene annotations."""
    from app.core.database import SessionLocal

    db = SessionLocal()

    try:
        await logger.info(
            "Starting annotation reset",
            task_id=task_id,
            source=source,
            gene_ids_count=len(gene_ids) if gene_ids else None
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

        # Clear relevant cache namespaces
        if source:
            await cache.invalidate_pattern(f"annotations:{source}:*")
        else:
            # Clear all annotation caches
            await cache.invalidate_pattern("annotations:*")

        # If specific genes, clear their individual caches
        if gene_ids:
            for gene_id in gene_ids:
                await cache.invalidate_pattern(f"gene:{gene_id}:*")

        await logger.info(
            "Annotation reset completed",
            task_id=task_id,
            user_id=user_id,
            source=source,
            deleted_count=count_before,
            gene_ids_count=len(gene_ids) if gene_ids else None
        )

    except Exception as e:
        import traceback
        await logger.error(
            f"Annotation reset failed: {str(e)}",
            task_id=task_id,
            user_id=user_id,
            error_type=type(e).__name__,
            traceback=traceback.format_exc()
        )
        raise
    finally:
        db.close()
# Trigger reload
