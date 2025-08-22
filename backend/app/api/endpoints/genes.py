"""
Gene API endpoints
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.crud.gene import gene_crud
from app.schemas.gene import Gene, GeneCreate, GeneList

router = APIRouter()

@router.get("/", response_model=GeneList)
async def get_genes(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    search: str | None = Query(None, description="Search term for gene symbol or HGNC ID"),
    min_score: float | None = Query(
        None, ge=0, le=100, description="Minimum evidence score (0-100)"
    ),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_desc: bool = Query(False, description="Sort in descending order"),
    db: Session = Depends(get_db),
) -> GeneList:
    """
    Get list of genes with optional filtering and sorting.
    Scores are percentages (0-100) calculated from percentiles across all active sources.
    OPTIMIZED: Uses single query with aggregation to avoid N+1 query problem.
    """
    # Use the optimized method that gets data with sources in a single query
    genes = gene_crud.get_genes_with_aggregated_data(
        db,
        skip=skip,
        limit=limit,
        search=search,
        min_score=min_score,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )

    # Get total count for pagination
    total = gene_crud.count(db, search=search, min_score=min_score)

    # Transform to response schema - NO MORE N+1 QUERIES!
    items = []
    for gene_data in genes:
        # Sources are already included in gene_data from the aggregated query
        items.append(
            Gene(
                id=gene_data["id"],  # type: ignore[arg-type]
                hgnc_id=gene_data["hgnc_id"],  # type: ignore[arg-type]
                approved_symbol=gene_data["approved_symbol"],  # type: ignore[arg-type]
                aliases=gene_data["aliases"],  # type: ignore[arg-type]
                created_at=gene_data["created_at"],  # type: ignore[arg-type]
                updated_at=gene_data["updated_at"],  # type: ignore[arg-type]
                evidence_count=gene_data["evidence_count"],
                evidence_score=gene_data["percentage_score"],  # Use percentage score (0-100)
                sources=gene_data["source_names"],  # Now directly from the aggregated query!
            )
        )

    return GeneList(items=items, total=total, page=(skip // limit) + 1, per_page=limit)

@router.get("/{gene_symbol}", response_model=Gene)
async def get_gene(gene_symbol: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get gene by symbol with percentage score (0-100)
    """
    gene = gene_crud.get_by_symbol(db, gene_symbol)
    if not gene:
        raise HTTPException(status_code=404, detail=f"Gene '{gene_symbol}' not found")

    # Get score from view
    score_data = gene_crud.get_gene_score(db, gene.id)  # type: ignore[arg-type]

    # Get evidence sources
    evidence = gene_crud.get_evidence(db, gene.id)  # type: ignore[arg-type]

    # Get display names for static sources
    static_source_names = {}
    result = db.execute(
        text("""
            SELECT 'static_' || id::text as internal_name, display_name
            FROM static_sources
            WHERE is_active = true
        """)
    )
    for row in result:
        static_source_names[row[0]] = row[1]

    # Map source names to display names
    sources = list({static_source_names.get(e.source_name, e.source_name) for e in evidence})

    # Get normalized scores breakdown
    score_breakdown = {}
    if gene.id:
        result = db.execute(
            text("""
                SELECT source_name, normalized_score
                FROM combined_evidence_scores
                WHERE gene_id = :gene_id
                ORDER BY source_name
            """),
            {"gene_id": gene.id}
        )
        for row in result:
            # Use display name for static sources
            source_display_name = static_source_names.get(row[0], row[0])
            score_breakdown[source_display_name] = round(float(row[1]), 4) if row[1] is not None else 0.0

    # Build response
    return {
        "id": gene.id,
        "hgnc_id": gene.hgnc_id,
        "approved_symbol": gene.approved_symbol,
        "aliases": gene.aliases or [],
        "created_at": gene.created_at,
        "updated_at": gene.updated_at,
        "evidence_count": score_data["evidence_count"] if score_data else 0,
        "evidence_score": score_data["percentage_score"] if score_data else None,
        "sources": sources,
        "score_breakdown": score_breakdown,  # Raw normalized scores per source
    }

@router.get("/{gene_symbol}/evidence")
async def get_gene_evidence(gene_symbol: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get all evidence for a gene with normalized scores
    """
    gene = gene_crud.get_by_symbol(db, gene_symbol)
    if not gene:
        raise HTTPException(status_code=404, detail=f"Gene '{gene_symbol}' not found")

    evidence = gene_crud.get_evidence(db, gene.id)  # type: ignore[arg-type]

    # Get normalized scores for each evidence
    normalized_scores = {}
    if gene.id:
        result = db.execute(
            text("""
                SELECT evidence_id, normalized_score
                FROM combined_evidence_scores
                WHERE gene_id = :gene_id
            """),
            {"gene_id": gene.id}
        )
        for row in result:
            normalized_scores[row[0]] = round(float(row[1]), 4) if row[1] is not None else 0.0

    # Get display names for static sources (map static_X to display names)
    static_source_names = {}
    result = db.execute(
        text("""
            SELECT 'static_' || id::text as internal_name, display_name
            FROM static_sources
            WHERE is_active = true
        """)
    )
    for row in result:
        static_source_names[row[0]] = row[1]

    # Aggregate diagnostic panel evidence
    aggregated_evidence = []
    diagnostic_panels_data: dict[str, Any] = {}
    diagnostic_panels_providers = []
    diagnostic_panels_ids = []

    for e in evidence:
        display_name = static_source_names.get(e.source_name, e.source_name)

        # If this is Diagnostic Panels, aggregate them
        if display_name == "Diagnostic Panels":
            diagnostic_panels_ids.append(e.id)
            diagnostic_panels_providers.append(e.source_detail)

            # Merge the panel data
            if not diagnostic_panels_data:
                diagnostic_panels_data = {
                    "id": e.id,  # Use first ID
                    "source_name": display_name,
                    "evidence_data": {
                        "providers": {}
                    },
                    "evidence_date": e.evidence_date,
                    "created_at": e.created_at,
                    "normalized_score": normalized_scores.get(e.id, 0.0)
                }

            # Add this provider's panels
            provider = e.source_detail or "Unknown"
            diagnostic_panels_data["evidence_data"]["providers"][provider] = e.evidence_data.get("panels", [])

            # Update normalized score to max
            current_score = normalized_scores.get(e.id, 0.0)
            if current_score > diagnostic_panels_data["normalized_score"]:
                diagnostic_panels_data["normalized_score"] = current_score
        else:
            # Regular evidence entry
            aggregated_evidence.append({
                "id": e.id,
                "source_name": display_name,
                "source_detail": e.source_detail,
                "evidence_data": e.evidence_data,
                "evidence_date": e.evidence_date,
                "created_at": e.created_at,
                "normalized_score": normalized_scores.get(e.id, 0.0),
            })

    # Add aggregated diagnostic panels if any
    if diagnostic_panels_data:
        # Set proper source_detail
        provider_count = len(diagnostic_panels_providers)
        diagnostic_panels_data["source_detail"] = f"{provider_count} providers"

        # Copy metadata from first evidence if available
        first_panel = next((e for e in evidence if static_source_names.get(e.source_name, e.source_name) == "Diagnostic Panels"), None)
        if first_panel and "metadata" in first_panel.evidence_data:
            diagnostic_panels_data["evidence_data"]["metadata"] = first_panel.evidence_data["metadata"]
        if first_panel and "confidence" in first_panel.evidence_data:
            diagnostic_panels_data["evidence_data"]["confidence"] = first_panel.evidence_data["confidence"]

        aggregated_evidence.append(diagnostic_panels_data)

    return {
        "gene_symbol": gene.approved_symbol,
        "gene_id": gene.id,
        "evidence_count": len(aggregated_evidence),
        "evidence": aggregated_evidence,
    }

@router.post("/", response_model=Gene)
def create_gene(gene_in: GeneCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Create a new gene
    """
    # Check if gene already exists
    existing = gene_crud.get_by_symbol(db, gene_in.approved_symbol)
    if existing:
        raise HTTPException(
            status_code=400, detail=f"Gene '{gene_in.approved_symbol}' already exists"
        )

    gene = gene_crud.create(db, gene_in)

    return {
        "id": gene.id,
        "hgnc_id": gene.hgnc_id,
        "approved_symbol": gene.approved_symbol,
        "aliases": gene.aliases or [],
        "created_at": gene.created_at,
        "updated_at": gene.updated_at,
        "evidence_count": 0,
        "evidence_score": None,
        "sources": [],
    }
