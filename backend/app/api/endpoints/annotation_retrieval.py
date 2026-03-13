"""GET endpoints for gene annotations — read-only annotation retrieval."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import GeneNotFoundError
from app.core.logging import get_logger
from app.models.gene import Gene
from app.models.gene_annotation import AnnotationSource, GeneAnnotation

router = APIRouter()
logger = get_logger(__name__)


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
    cached: dict[str, Any] | None = await cache_service.get(
        key=cache_key, namespace="annotations", default=None
    )
    if cached:
        logger.sync_debug(f"Cache hit for gene {gene_id}", source=source)
        return cached

    # Get the gene
    gene = db.query(Gene).filter(Gene.id == gene_id).first()
    if not gene:
        raise GeneNotFoundError(gene_id)

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
    from app.core.constants import CACHE_TTL_LONG

    await cache_service.set(key=cache_key, value=result, namespace="annotations", ttl=CACHE_TTL_LONG)

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
    cached: dict[str, Any] | None = await cache_service.get(
        key=cache_key, namespace="annotations", default=None
    )
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
        raise GeneNotFoundError(gene_id)

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
    from app.core.constants import CACHE_TTL_EXTENDED

    await cache_service.set(key=cache_key, value=summary, namespace="annotations", ttl=CACHE_TTL_EXTENDED)

    return summary


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

    # Filter by active status if requested
    if active_only:
        query = query.filter(AnnotationSource.is_active.is_(True))

    # Order by priority (descending) then by source_name
    sources = query.order_by(AnnotationSource.priority.desc(), AnnotationSource.source_name).all()

    return [
        {
            "source_name": source.source_name,
            "display_name": source.display_name,
            "version": source.version,
            "description": source.description,
            "url": source.url,
            "base_url": source.base_url,
            "is_active": source.is_active,
            "priority": source.priority,
            "update_frequency": source.update_frequency,
            "last_update": source.last_update.isoformat() if source.last_update else None,
            "next_update": source.next_update.isoformat() if source.next_update else None,
            "created_at": source.created_at.isoformat() if source.created_at else None,
            "updated_at": source.updated_at.isoformat() if source.updated_at else None,
        }
        for source in sources
    ]


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
    from app.core.exceptions import ValidationError as DomainValidationError

    # Limit batch size
    if len(gene_ids) > 100:
        raise DomainValidationError(field="gene_ids", reason="Batch size limited to 100 genes")

    # Build query
    query = db.query(GeneAnnotation).filter(GeneAnnotation.gene_id.in_(gene_ids))

    if sources:
        query = query.filter(GeneAnnotation.source.in_(sources))

    annotations = query.all()

    # Group by gene
    results: dict[int, dict[str, list[dict[str, Any]]]] = {}
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
