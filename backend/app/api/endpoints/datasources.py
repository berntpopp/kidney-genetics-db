"""
Data source API endpoints
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.background_tasks import task_manager
from app.core.datasource_config import DATA_SOURCE_CONFIG, get_auto_update_sources
from app.models.gene import PipelineRun
from app.schemas.datasource import DataSource, DataSourceList, DataSourceStats

router = APIRouter()


@router.get("/", response_model=DataSourceList)
async def get_datasources(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get information about all data sources and their current status
    """
    sources = []

    # Get statistics for each source from the database
    result = db.execute(
        text(
            """
            SELECT
                source_name,
                COUNT(DISTINCT gene_id) as gene_count,
                COUNT(*) as evidence_count,
                MAX(updated_at) as last_updated
            FROM gene_evidence
            GROUP BY source_name
            ORDER BY source_name
        """
        )
    ).fetchall()

    # Create a mapping of source stats
    source_stats = {}
    for row in result:
        source_stats[row[0]] = {
            "gene_count": row[1],
            "evidence_count": row[2],
            "last_updated": row[3],
        }

    # Get additional metadata for specific sources
    panelapp_metadata = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT panel_name) as panel_count
            FROM (
                SELECT jsonb_array_elements(evidence_data->'panels')->>'name' as panel_name
                FROM gene_evidence
                WHERE source_name = 'PanelApp'
            ) panels
        """
        )
    ).scalar()

    pubtator_metadata = db.execute(
        text(
            """
            SELECT
                SUM((evidence_data->>'publication_count')::int) as total_publications,
                (SELECT COUNT(DISTINCT pmid) FROM (
                    SELECT jsonb_array_elements_text(evidence_data->'pmids') as pmid
                    FROM gene_evidence
                    WHERE source_name = 'PubTator'
                ) pmids) as unique_pmids
            FROM gene_evidence
            WHERE source_name = 'PubTator'
        """
        )
    ).fetchone()

    # Get DiagnosticPanels metadata
    diagnostic_metadata = db.execute(
        text(
            """
            WITH providers_panels AS (
                SELECT 
                    jsonb_array_elements_text(evidence_data->'providers') as provider,
                    jsonb_array_elements_text(evidence_data->'panels') as panel
                FROM gene_evidence
                WHERE source_name = 'DiagnosticPanels'
            )
            SELECT 
                COUNT(DISTINCT provider) as provider_count,
                COUNT(DISTINCT panel) as total_panels,
                ARRAY_AGG(DISTINCT provider ORDER BY provider) as providers
            FROM providers_panels
        """
        )
    ).fetchone()

    # No longer need to query static sources - they've been replaced by hybrid sources

    # Build data source list
    for source_name, config in DATA_SOURCE_CONFIG.items():
        if source_name in source_stats:
            # Source is active (has data)
            stats = DataSourceStats(
                gene_count=source_stats[source_name]["gene_count"],
                evidence_count=source_stats[source_name]["evidence_count"],
                last_updated=source_stats[source_name]["last_updated"],
                metadata={},
            )

            # Add source-specific metadata
            if source_name == "PanelApp" and panelapp_metadata:
                stats.metadata["panel_count"] = panelapp_metadata or 0
                stats.metadata["regions"] = ["UK", "Australia"]

            elif source_name == "PubTator" and pubtator_metadata:
                stats.metadata["total_publications"] = pubtator_metadata[0] or 0
                stats.metadata["unique_pmids"] = pubtator_metadata[1] or 0
                stats.metadata["search_query"] = (
                    '("kidney disease" OR "renal disease") AND (gene OR syndrome) AND (variant OR mutation)'
                )

            elif source_name == "DiagnosticPanels" and diagnostic_metadata:
                stats.metadata["provider_count"] = diagnostic_metadata[0] or 0
                stats.metadata["total_panels"] = diagnostic_metadata[1] or 0
                stats.metadata["providers"] = [p for p in (diagnostic_metadata[2] or []) if p and p != "test_provider"]
                stats.metadata["upload_type"] = "manual"
                stats.metadata["supported_formats"] = ["json", "csv", "tsv", "xlsx", "xls"]

            status = "active"
        else:
            # Source is configured but has no data
            if config.get("hybrid_source", False) or source_name == "DiagnosticPanels":
                # Manual upload source - show as ready
                status = "ready_for_upload"
                stats = DataSourceStats(
                    gene_count=0,
                    evidence_count=0,
                    last_updated=None,
                    metadata={
                        "upload_type": "manual",
                        "supported_formats": ["json", "csv", "tsv", "xlsx", "xls"],
                        "message": "Upload diagnostic panel files via the API"
                    }
                )
            else:
                status = "inactive"
                stats = None

        sources.append(
            DataSource(
                name=source_name,
                display_name=config["display_name"],
                description=config["description"],
                status=status,
                stats=stats,
                url=config["url"],
                documentation_url=config["documentation_url"],
            )
        )

    # Static sources have been replaced by hybrid source (DiagnosticPanels)

    # Get last pipeline run
    last_run = (
        db.query(PipelineRun)
        .filter(PipelineRun.status == "completed")
        .order_by(PipelineRun.completed_at.desc())
        .first()
    )

    # Count active sources
    active_count = len([s for s in sources if s.status == "active"])

    return DataSourceList(
        sources=sources,
        total_active=active_count,
        total_sources=len(sources),
        last_pipeline_run=last_run.completed_at if last_run else None,
    )


@router.get("/{source_name}")
async def get_datasource(source_name: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get detailed information about a specific data source
    """
    # Get basic config
    if source_name not in DATA_SOURCE_CONFIG:
        return {"error": f"Unknown data source: {source_name}"}

    config = DATA_SOURCE_CONFIG[source_name]

    # Get statistics
    stats = db.execute(
        text(
            """
            SELECT
                COUNT(DISTINCT gene_id) as gene_count,
                COUNT(*) as evidence_count,
                MAX(updated_at) as last_updated
            FROM gene_evidence
            WHERE source_name = :source_name
        """
        ),
        {"source_name": source_name},
    ).fetchone()

    if stats and stats[0] > 0:
        # Get top genes for this source
        top_genes = db.execute(
            text(
                """
                SELECT
                    g.approved_symbol,
                    ces.normalized_score,
                    CASE
                        WHEN ge.source_name = 'PanelApp' THEN
                            jsonb_array_length(COALESCE(ge.evidence_data->'panels', '[]'::jsonb))
                        WHEN ge.source_name = 'PubTator' THEN
                            COALESCE((ge.evidence_data->>'publication_count')::int, 0)
                        WHEN ge.source_name LIKE 'static_%' THEN
                            jsonb_array_length(COALESCE(ge.evidence_data->'panels', '[]'::jsonb))
                        ELSE 0
                    END as count
                FROM gene_evidence ge
                JOIN genes g ON ge.gene_id = g.id
                JOIN combined_evidence_scores ces ON ge.id = ces.evidence_id
                WHERE ge.source_name = :source_name
                ORDER BY ces.normalized_score DESC
                LIMIT 10
            """
            ),
            {"source_name": source_name},
        ).fetchall()

        return {
            "name": source_name,
            "display_name": config["display_name"],
            "description": config["description"],
            "status": "active",
            "url": config["url"],
            "documentation_url": config["documentation_url"],
            "stats": {
                "gene_count": stats[0],
                "evidence_count": stats[1],
                "last_updated": stats[2].isoformat() if stats[2] else None,
            },
            "top_genes": [
                {
                    "symbol": gene[0],
                    "score": round(gene[1], 4) if gene[1] else 0.0,
                    "count": gene[2],
                }
                for gene in top_genes
            ],
        }
    else:
        return {
            "name": source_name,
            "display_name": config["display_name"],
            "description": config["description"],
            "status": "inactive" if source_name not in ["HPO"] else "error",
            "url": config["url"],
            "documentation_url": config["documentation_url"],
            "stats": None,
            "message": "No data available for this source",
        }


@router.post("/{source_name}/update")
async def update_datasource(source_name: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Trigger update for a specific data source
    """
    if source_name not in DATA_SOURCE_CONFIG:
        raise HTTPException(status_code=404, detail=f"Unknown data source: {source_name}")

    try:
        await task_manager.run_source(source_name)
        return {"message": f"Update triggered for {source_name}", "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start update: {e!s}") from e


@router.post("/update-all")
async def update_all_datasources(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Trigger updates for all available data sources that support auto-update
    """
    try:
        sources = get_auto_update_sources()
        for source_name in sources:
            await task_manager.run_source(source_name)

        return {
            "message": f"Updates triggered for {len(sources)} sources",
            "sources": sources,
            "status": "started",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start updates: {e!s}") from e
