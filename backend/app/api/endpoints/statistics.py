"""
Statistics API endpoints
"""

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.exceptions import ValidationError
from app.core.responses import ResponseBuilder
from app.crud.statistics import statistics_crud

router = APIRouter()


@router.get("/source-overlaps")
async def get_source_overlaps(
    sources: list[str] | None = Query(
        None, description="Specific source names to include in analysis"
    ),
    min_tier: str | None = Query(
        None,
        description="Minimum evidence tier (Very High, High, Medium, Low)"
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get gene intersections between data sources for UpSet plot visualization.

    Args:
        sources: Optional list of source names to filter analysis (e.g., ['PanelApp', 'ClinGen'])
                If None, includes all available sources.
        min_tier: Optional minimum evidence tier for filtering

    Returns data optimized for UpSet.js library with sets and intersections.
    """
    start_time = time.time()

    try:
        overlap_data = statistics_crud.get_source_overlaps(
            db, selected_sources=sources, min_tier=min_tier
        )

        query_duration_ms = round((time.time() - start_time) * 1000, 2)

        return ResponseBuilder.build_success_response(
            data=overlap_data,
            meta={
                "description": "Gene intersections between data sources for UpSet plot visualization",
                "query_duration_ms": query_duration_ms,
                "data_version": datetime.utcnow().strftime("%Y%m%d"),
                "visualization_type": "upset_plot",
                "min_tier": min_tier,
            },
        )

    except Exception as e:
        raise ValidationError(
            field="source_overlaps", reason=f"Failed to calculate source overlaps: {str(e)}"
        ) from e


@router.get("/source-distributions")
async def get_source_distributions(
    min_tier: str | None = Query(
        None,
        description="Minimum evidence tier (Very High, High, Medium, Low)"
    ),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Get source count distributions for bar chart visualizations.

    Returns distribution data showing how many genes appear in X number of
    panels/publications/evidence items for each source.

    Args:
        min_tier: Optional minimum evidence tier for filtering
    """
    start_time = time.time()

    try:
        distribution_data = statistics_crud.get_source_distributions(db, min_tier=min_tier)

        query_duration_ms = round((time.time() - start_time) * 1000, 2)

        return ResponseBuilder.build_success_response(
            data=distribution_data,
            meta={
                "description": "Source count distributions for bar chart visualization",
                "query_duration_ms": query_duration_ms,
                "data_version": datetime.utcnow().strftime("%Y%m%d"),
                "visualization_type": "bar_charts",
                "source_count": len(distribution_data),
                "min_tier": min_tier,
            },
        )

    except Exception as e:
        raise ValidationError(
            field="source_distributions",
            reason=f"Failed to calculate source distributions: {str(e)}",
        ) from e


@router.get("/evidence-composition")
async def get_evidence_composition(
    min_tier: str | None = Query(
        None,
        description="Minimum evidence tier (comprehensive_support, multi_source_support, established_support, preliminary_evidence, minimal_evidence)"
    ),
    hide_zero_scores: bool = Query(
        True,
        description="Hide genes with percentage_score = 0 (default: true, matching /genes endpoint)"
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get evidence quality and composition analysis.

    Uses actual evidence_tier column from gene_scores view, matching /genes endpoint behavior.
    By default excludes genes with insufficient evidence (percentage_score = 0).

    Returns breakdown of evidence tiers, source contribution weights,
    and coverage statistics for comprehensive analysis.

    Args:
        min_tier: Optional minimum evidence tier for filtering
        hide_zero_scores: Hide genes with insufficient evidence (default: True)
    """
    start_time = time.time()

    try:
        composition_data = statistics_crud.get_evidence_composition(
            db,
            min_tier=min_tier,
            hide_zero_scores=hide_zero_scores
        )

        query_duration_ms = round((time.time() - start_time) * 1000, 2)

        return ResponseBuilder.build_success_response(
            data=composition_data,
            meta={
                "description": "Evidence quality and composition analysis using actual evidence tiers",
                "query_duration_ms": query_duration_ms,
                "data_version": datetime.utcnow().strftime("%Y%m%d"),
                "visualization_type": "composition_analysis",
                "min_tier": min_tier,
                "hide_zero_scores": hide_zero_scores,
            },
        )

    except Exception as e:
        raise ValidationError(
            field="evidence_composition",
            reason=f"Failed to analyze evidence composition: {str(e)}",
        ) from e


@router.get("/summary")
async def get_statistics_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get summary statistics for dashboard overview.

    Returns high-level statistics combining key metrics from all analyses
    for use in dashboard summary cards and quick insights.
    """
    start_time = time.time()

    try:
        # Get summary data from each analysis
        overlap_data = statistics_crud.get_source_overlaps(db)
        composition_data = statistics_crud.get_evidence_composition(db)
        distribution_data = statistics_crud.get_source_distributions(db)

        # Extract key summary metrics
        summary = {
            "overview": {
                "total_genes": overlap_data["total_unique_genes"],
                "active_sources": len(overlap_data["sets"]),
                "total_intersections": len(overlap_data["intersections"]),
                "genes_in_all_sources": overlap_data["overlap_statistics"]["genes_in_all_sources"],
            },
            "quality": {
                "avg_sources_per_gene": composition_data["summary_statistics"][
                    "avg_sources_per_gene"
                ],
                "total_evidence_records": composition_data["summary_statistics"][
                    "total_evidence_records"
                ],
                "high_confidence_genes": sum(
                    item["gene_count"]
                    for item in composition_data["evidence_quality_distribution"]
                    if "High" in item["label"]
                ),
            },
            "coverage": {
                "single_source_genes": overlap_data["overlap_statistics"][
                    "single_source_combinations"
                ],
                "multi_source_genes": overlap_data["total_unique_genes"]
                - overlap_data["overlap_statistics"]["single_source_combinations"],
                "source_distribution_variety": len(distribution_data),
            },
        }

        query_duration_ms = round((time.time() - start_time) * 1000, 2)

        return ResponseBuilder.build_success_response(
            data=summary,
            meta={
                "description": "Summary statistics for dashboard overview",
                "query_duration_ms": query_duration_ms,
                "data_version": datetime.utcnow().strftime("%Y%m%d"),
                "visualization_type": "summary_dashboard",
            },
        )

    except Exception as e:
        raise ValidationError(
            field="statistics_summary", reason=f"Failed to generate statistics summary: {str(e)}"
        ) from e
