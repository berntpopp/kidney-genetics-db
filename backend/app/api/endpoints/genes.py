"""
Gene API endpoints
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.crud.gene import gene_crud
from app.schemas.gene import Gene, GeneCreate, GeneList

router = APIRouter()


@router.get("/", response_model=GeneList)
def get_genes(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    search: str | None = Query(None, description="Search term for gene symbol or HGNC ID"),
    min_score: float | None = Query(None, ge=0, le=100, description="Minimum evidence score (0-100)"),
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_desc: bool = Query(False, description="Sort in descending order"),
    db: Session = Depends(get_db),
) -> GeneList:
    """
    Get list of genes with optional filtering and sorting.
    Scores are percentages (0-100) calculated from percentiles across all active sources.
    """
    # Use the new method that gets data from the gene_scores view
    genes = gene_crud.get_multi_with_scores(
        db, skip=skip, limit=limit, search=search, min_score=min_score,
        sort_by=sort_by, sort_desc=sort_desc
    )

    # Get total count for pagination
    total = gene_crud.count(db, search=search, min_score=min_score)

    # Transform to response schema
    items = []
    for gene_data in genes:
        # Get evidence sources from database
        evidence = gene_crud.get_evidence(db, gene_data["id"])
        sources = list({e.source_name for e in evidence})

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
                sources=sources,
            )
        )

    return GeneList(items=items, total=total, page=(skip // limit) + 1, per_page=limit)


@router.get("/{gene_symbol}", response_model=Gene)
def get_gene(gene_symbol: str, db: Session = Depends(get_db)) -> dict[str, Any]:
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
    sources = list({e.source_name for e in evidence})

    # Build response
    result = {
        "id": gene.id,
        "hgnc_id": gene.hgnc_id,
        "approved_symbol": gene.approved_symbol,
        "aliases": gene.aliases or [],
        "created_at": gene.created_at,
        "updated_at": gene.updated_at,
        "evidence_count": score_data["evidence_count"] if score_data else 0,
        "evidence_score": score_data["percentage_score"] if score_data else None,
        "sources": sources,
    }

    return result


@router.get("/{gene_symbol}/evidence")
def get_gene_evidence(gene_symbol: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get all evidence for a gene
    """
    gene = gene_crud.get_by_symbol(db, gene_symbol)
    if not gene:
        raise HTTPException(status_code=404, detail=f"Gene '{gene_symbol}' not found")

    evidence = gene_crud.get_evidence(db, gene.id)  # type: ignore[arg-type]

    return {
        "gene_symbol": gene.approved_symbol,
        "gene_id": gene.id,
        "evidence_count": len(evidence),
        "evidence": [
            {
                "id": e.id,
                "source_name": e.source_name,
                "source_detail": e.source_detail,
                "evidence_data": e.evidence_data,
                "evidence_date": e.evidence_date,
                "created_at": e.created_at,
            }
            for e in evidence
        ],
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
