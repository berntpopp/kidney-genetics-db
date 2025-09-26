"""
Data source API endpoints
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.background_tasks import task_manager
from app.core.datasource_config import DATA_SOURCE_CONFIG, get_auto_update_sources
from app.core.exceptions import DataSourceError
from app.core.responses import ResponseBuilder
from app.models.gene import PipelineRun
from app.schemas.datasource import DataSource, DataSourceStats

router = APIRouter()


@router.get("/")
async def get_datasources(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get information about all data sources and their current status
    """
    sources = []

    try:
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
    except Exception:
        # If query fails, return empty result
        result = []

    # Create a mapping of source stats
    source_stats = {}
    for row in result:
        source_stats[row[0]] = {
            "gene_count": row[1],
            "evidence_count": row[2],
            "last_updated": row[3],
        }

    # Get meaningful metadata for each source

    # ClinGen: expert panels and classification levels
    try:
        clingen_metadata = db.execute(
            text(
                """
                WITH panels AS (
                    SELECT jsonb_array_elements_text(evidence_data->'expert_panels') as panel
                    FROM gene_evidence
                    WHERE source_name = 'ClinGen'
                ),
                validities AS (
                    SELECT jsonb_array_elements(evidence_data->'validities') as validity
                    FROM gene_evidence
                    WHERE source_name = 'ClinGen'
                )
                SELECT
                    (SELECT COUNT(DISTINCT panel) FROM panels) as panel_count,
                    (SELECT COUNT(DISTINCT validity->>'classification') FROM validities) as classification_count
            """
            )
        ).fetchone()
    except Exception:
        clingen_metadata = None

    # GenCC: submissions and submitters
    gencc_metadata = db.execute(
        text(
            """
            WITH submissions AS (
                SELECT jsonb_array_elements(evidence_data->'submissions') as submission
                FROM gene_evidence
                WHERE source_name = 'GenCC'
            )
            SELECT
                COUNT(*) as submission_count,
                COUNT(DISTINCT submission->>'submitter') as submitter_count
            FROM submissions
        """
        )
    ).fetchone()

    # HPO: phenotype terms (count distinct HPO IDs)
    hpo_metadata = db.execute(
        text(
            """
            WITH hpo_ids AS (
                SELECT DISTINCT jsonb_array_elements_text(evidence_data->'hpo_terms') as hpo_id
                FROM gene_evidence
                WHERE source_name = 'HPO'
            )
            SELECT COUNT(*) as phenotype_count
            FROM hpo_ids
        """
        )
    ).scalar()

    # PubTator: unique publications
    pubtator_metadata = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT pmid) as unique_publications
            FROM (
                SELECT jsonb_array_elements_text(evidence_data->'pmids') as pmid
                FROM gene_evidence
                WHERE source_name = 'PubTator'
            ) pmids
        """
        )
    ).scalar()

    # PanelApp: panels and regions
    panelapp_metadata = db.execute(
        text(
            """
            WITH panel_data AS (
                SELECT jsonb_array_elements(evidence_data->'panels') as panel
                FROM gene_evidence
                WHERE source_name = 'PanelApp'
            )
            SELECT
                COUNT(DISTINCT panel->>'name') as panel_count,
                COUNT(DISTINCT panel->>'region') as region_count
            FROM panel_data
        """
        )
    ).fetchone()

    # DiagnosticPanels: providers and panels
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
                COUNT(DISTINCT panel) as panel_count,
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

            # Add source-specific meaningful metadata
            if source_name == "ClinGen" and clingen_metadata:
                stats.metadata["expert_panels"] = clingen_metadata[0] or 0
                stats.metadata["classifications"] = clingen_metadata[1] or 0
                stats.metadata["type"] = "Expert Curation"

            elif source_name == "GenCC" and gencc_metadata:
                stats.metadata["submissions"] = gencc_metadata[0] or 0
                stats.metadata["submitters"] = gencc_metadata[1] or 0
                stats.metadata["type"] = "Clinical Validity"

            elif source_name == "HPO":
                stats.metadata["phenotype_terms"] = hpo_metadata or 0
                stats.metadata["type"] = "Phenotype Ontology"

            elif source_name == "PubTator":
                stats.metadata["publications"] = pubtator_metadata or 0
                stats.metadata["type"] = "Literature Mining"
                stats.metadata["search_query"] = (
                    '("kidney disease" OR "renal disease") AND (gene OR syndrome) AND (variant OR mutation)'
                )

            elif source_name == "PanelApp" and panelapp_metadata:
                stats.metadata["panels"] = panelapp_metadata[0] or 0
                stats.metadata["regions"] = panelapp_metadata[1] or 0
                stats.metadata["region_names"] = ["UK", "Australia"]
                stats.metadata["type"] = "Clinical Panels"

            elif source_name == "DiagnosticPanels" and diagnostic_metadata:
                stats.metadata["providers"] = diagnostic_metadata[0] or 0
                stats.metadata["panels"] = diagnostic_metadata[1] or 0
                stats.metadata["provider_list"] = [
                    p for p in (diagnostic_metadata[2] or []) if p and p != "test_provider"
                ]
                stats.metadata["type"] = "Diagnostic Labs"
                stats.metadata["upload_type"] = "manual"

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
                        "message": "Upload diagnostic panel files via the API",
                    },
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

    # Get actual unique gene count (only genes with evidence)
    unique_genes = (
        db.execute(text("SELECT COUNT(DISTINCT gene_id) FROM gene_evidence")).scalar() or 0
    )

    # Get orphaned gene count
    orphaned_genes = (
        db.execute(
            text("""
        SELECT COUNT(*)
        FROM genes g
        WHERE NOT EXISTS (
            SELECT 1 FROM gene_evidence ge WHERE ge.gene_id = g.id
        )
    """)
        ).scalar()
        or 0
    )

    # Get total evidence records
    total_evidence = db.execute(text("SELECT COUNT(*) FROM gene_evidence")).scalar() or 0

    # Get last update from any source
    last_update = db.execute(text("SELECT MAX(updated_at) FROM gene_evidence")).scalar()

    # Calculate source coverage
    source_coverage = 0
    if unique_genes > 0:
        avg_sources_per_gene = total_evidence / unique_genes
        source_coverage = min(round((avg_sources_per_gene / 6) * 100), 100)

    # Field explanations for tooltips
    explanations = {
        "active_sources": "Number of data sources currently integrated and providing gene evidence",
        "unique_genes": f"Total number of distinct genes across all sources ({unique_genes:,} genes with kidney disease associations)",
        "source_coverage": f"Average overlap between sources ({source_coverage}%). Each gene appears in ~{round(total_evidence / unique_genes, 1) if unique_genes > 0 else 0} sources on average. Higher coverage indicates stronger validation across multiple sources.",
        "last_updated": "Most recent data update from any source. Updates occur when sources are refreshed or new data is uploaded.",
        # Source-specific explanations
        "expert_panels": "Number of clinical expert panels that have reviewed and validated gene-disease relationships",
        "classifications": "Different levels of gene-disease validity (Definitive, Strong, Moderate, Limited, Disputed, Refuted)",
        "submissions": "Individual gene-disease relationship submissions from consortium members",
        "submitters": "Number of organizations contributing gene-disease validity assessments",
        "phenotypes": "Distinct Human Phenotype Ontology terms associated with kidney/urinary system abnormalities",
        "publications": "Unique PubMed articles mentioning kidney disease genes identified through text mining",
        "panels": "Clinical or diagnostic gene panels for kidney disease testing",
        "regions": "Geographic regions or organizations maintaining the gene panels",
        "providers": "Commercial diagnostic laboratories offering kidney genetic testing panels",
    }

    return ResponseBuilder.build_success_response(
        data={
            "sources": sources,
            "total_active": active_count,
            "total_sources": len(sources),
            "last_pipeline_run": last_run.completed_at if last_run else None,
            "total_unique_genes": unique_genes,
            "orphaned_genes": orphaned_genes,
            "total_evidence_records": total_evidence,
            "last_data_update": last_update,
            "explanations": explanations,
        }
    )


@router.get("/{source_name}")
async def get_datasource(source_name: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get detailed information about a specific data source
    """
    # Get basic config
    if source_name not in DATA_SOURCE_CONFIG:
        raise DataSourceError(source_name, "configuration", "Unknown data source")

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

        return ResponseBuilder.build_success_response(
            data={
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
        )
    else:
        return ResponseBuilder.build_success_response(
            data={
                "name": source_name,
                "display_name": config["display_name"],
                "description": config["description"],
                "status": "inactive" if source_name not in ["HPO"] else "error",
                "url": config["url"],
                "documentation_url": config["documentation_url"],
                "stats": None,
                "message": "No data available for this source",
            }
        )


@router.post("/{source_name}/update")
async def update_datasource(
    source_name: str,
    mode: Literal["smart", "full"] = Query(
        "smart", description="Update mode: smart (incremental) or full (complete refresh)"
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Trigger update for a specific data source with mode selection.

    Modes:
    - smart: Incremental update, stops when hitting database duplicates (default)
    - full: Complete refresh, deletes existing entries first
    """
    if source_name not in DATA_SOURCE_CONFIG:
        raise DataSourceError(source_name, "update", "Unknown data source")

    try:
        await task_manager.run_source(source_name, mode=mode)
        return ResponseBuilder.build_success_response(
            data={
                "message": f"{mode.capitalize()} update triggered for {source_name}",
                "status": "started",
                "mode": mode,
            }
        )
    except Exception as e:
        raise DataSourceError(source_name, "update", f"Failed to start update: {e!s}") from e


@router.post("/update-all")
async def update_all_datasources(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Trigger updates for all available data sources that support auto-update
    """
    try:
        sources = get_auto_update_sources()
        for source_name in sources:
            await task_manager.run_source(source_name)

        return ResponseBuilder.build_success_response(
            data={
                "message": f"Updates triggered for {len(sources)} sources",
                "sources": sources,
                "status": "started",
            }
        )
    except Exception as e:
        raise DataSourceError("multiple", "bulk_update", f"Failed to start updates: {e!s}") from e
