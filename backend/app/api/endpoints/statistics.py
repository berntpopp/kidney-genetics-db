"""
Statistics API endpoints
"""

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.exceptions import ValidationError
from app.core.responses import ResponseBuilder
from app.crud.statistics import statistics_crud

router = APIRouter()


@router.get("/source-overlaps")
async def get_source_overlaps(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get gene intersections between all data sources for UpSet plot visualization.

    Returns data optimized for UpSet.js library with sets and intersections.
    """
    start_time = time.time()

    try:
        overlap_data = statistics_crud.get_source_overlaps(db)

        query_duration_ms = round((time.time() - start_time) * 1000, 2)

        return ResponseBuilder.build_success_response(
            data=overlap_data,
            meta={
                "description": "Gene intersections between data sources for UpSet plot visualization",
                "query_duration_ms": query_duration_ms,
                "data_version": datetime.utcnow().strftime("%Y%m%d"),
                "visualization_type": "upset_plot",
            },
        )

    except Exception as e:
        raise ValidationError(
            field="source_overlaps", message=f"Failed to calculate source overlaps: {str(e)}"
        )


@router.get("/source-distributions")
async def get_source_distributions(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get source count distributions for bar chart visualizations.

    Returns distribution data showing how many genes appear in X number of
    panels/publications/evidence items for each source.
    """
    start_time = time.time()

    try:
        distribution_data = statistics_crud.get_source_distributions(db)

        query_duration_ms = round((time.time() - start_time) * 1000, 2)

        return ResponseBuilder.build_success_response(
            data=distribution_data,
            meta={
                "description": "Source count distributions for bar chart visualization",
                "query_duration_ms": query_duration_ms,
                "data_version": datetime.utcnow().strftime("%Y%m%d"),
                "visualization_type": "bar_charts",
                "source_count": len(distribution_data),
            },
        )

    except Exception as e:
        raise ValidationError(
            field="source_distributions",
            message=f"Failed to calculate source distributions: {str(e)}",
        )


@router.get("/evidence-composition")
async def get_evidence_composition(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get evidence quality and composition analysis.

    Returns breakdown of evidence scores, source contribution weights,
    and coverage statistics for comprehensive analysis.
    """
    start_time = time.time()

    try:
        composition_data = statistics_crud.get_evidence_composition(db)

        query_duration_ms = round((time.time() - start_time) * 1000, 2)

        return ResponseBuilder.build_success_response(
            data=composition_data,
            meta={
                "description": "Evidence quality and composition analysis",
                "query_duration_ms": query_duration_ms,
                "data_version": datetime.utcnow().strftime("%Y%m%d"),
                "visualization_type": "composition_analysis",
            },
        )

    except Exception as e:
        raise ValidationError(
            field="evidence_composition",
            message=f"Failed to analyze evidence composition: {str(e)}",
        )


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
            field="statistics_summary", message=f"Failed to generate statistics summary: {str(e)}"
        )
