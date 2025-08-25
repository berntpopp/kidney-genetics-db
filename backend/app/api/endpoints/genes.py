"""
Gene API endpoints - JSON:API compliant using reusable components
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.exceptions import GeneNotFoundError, ValidationError
from app.core.jsonapi import (
    build_jsonapi_response,
    get_jsonapi_params,
    get_range_filters,
    get_search_filter,
    get_sort_param,
    jsonapi_endpoint,
)
from app.models.gene import Gene, GeneEvidence
from app.schemas.gene import GeneCreate

router = APIRouter()


@router.get("/{gene_id}/annotations", response_model=dict)
async def get_gene_annotations(
    gene_id: int | str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get gene annotations (including gnomAD constraint scores).

    Can be called with either gene ID or gene symbol.
    """
    from app.models.gene_annotation import GeneAnnotation

    # Check if gene_id is numeric or symbol
    try:
        gene_id_int = int(gene_id)
        gene = db.query(Gene).filter(Gene.id == gene_id_int).first()
    except ValueError:
        # It's a symbol
        gene = db.query(Gene).filter(Gene.approved_symbol == gene_id).first()

    if not gene:
        raise GeneNotFoundError(f"Gene {gene_id} not found")

    # Get all annotations for this gene
    annotations = db.query(GeneAnnotation).filter(GeneAnnotation.gene_id == gene.id).all()

    # Transform to response format
    result = {"gene_id": gene.id, "gene_symbol": gene.approved_symbol, "annotations": {}}

    for ann in annotations:
        result["annotations"][ann.source] = {
            "version": ann.version,
            "data": ann.annotations,
            "updated_at": ann.updated_at.isoformat() if ann.updated_at else None,
        }

    return result


def transform_gene_to_jsonapi(results) -> list[dict]:
    """Transform gene query results to JSON:API format."""
    data = []
    for row in results:
        data.append(
            {
                "type": "genes",
                "id": str(row[0]),
                "attributes": {
                    "hgnc_id": row[1],
                    "approved_symbol": row[2],
                    "aliases": row[3] or [],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None,
                    "evidence_count": row[6],
                    "evidence_score": float(row[7]) if row[7] is not None else None,
                    "sources": list(row[8]) if row[8] else [],
                },
            }
        )
    return data


@router.get("/", response_model=dict)
@jsonapi_endpoint(
    resource_type="genes", model=Gene, searchable_fields=["approved_symbol", "hgnc_id"]
)
async def get_genes(
    db: Session = Depends(get_db),
    # JSON:API pagination
    params: dict = Depends(get_jsonapi_params),
    # JSON:API filters
    search: str | None = Depends(get_search_filter),
    score_range: tuple[float | None, float | None] = Depends(
        get_range_filters("score", min_ge=0, max_le=100)
    ),
    count_range: tuple[int | None, int | None] = Depends(get_range_filters("count", min_ge=0)),
    filter_source: str | None = Query(None, alias="filter[source]"),
    # JSON:API sorting
    sort: str | None = Depends(get_sort_param("-evidence_score,approved_symbol")),
) -> dict[str, Any]:
    """
    Get genes with JSON:API compliant response using reusable components.

    Query parameters follow JSON:API specification:
    - Pagination: page[number], page[size]
    - Filtering: filter[search], filter[min_score], filter[source], etc.
    - Sorting: sort=-evidence_score,approved_symbol (prefix with - for descending)
    """
    # Build WHERE clauses first
    where_clauses = ["1=1"]
    query_params = {}

    # Apply filters
    if search:
        where_clauses.append("(g.approved_symbol ILIKE :search OR g.hgnc_id ILIKE :search)")
        query_params["search"] = f"%{search}%"

    min_score, max_score = score_range
    if min_score is not None:
        where_clauses.append("gs.percentage_score >= :min_score")
        query_params["min_score"] = min_score

    if max_score is not None:
        where_clauses.append("gs.percentage_score <= :max_score")
        query_params["max_score"] = max_score

    min_count, max_count = count_range
    if min_count is not None:
        where_clauses.append("gs.evidence_count >= :min_count")
        query_params["min_count"] = min_count

    if max_count is not None:
        where_clauses.append("gs.evidence_count <= :max_count")
        query_params["max_count"] = max_count

    if filter_source:
        where_clauses.append(
            "EXISTS (SELECT 1 FROM gene_evidence ge2 WHERE ge2.gene_id = g.id AND ge2.source_name = :source)"
        )
        query_params["source"] = filter_source

    where_clause = " AND ".join(where_clauses)

    # Simple count query without complex aggregations
    count_query = f"""
        SELECT COUNT(DISTINCT g.id)
        FROM genes g
        LEFT JOIN gene_scores gs ON gs.gene_id = g.id
        LEFT JOIN gene_evidence ge ON g.id = ge.gene_id
        WHERE {where_clause}
    """
    total = db.execute(text(count_query), query_params).scalar() or 0

    # Build sort clause
    sort_clause = ""
    if sort:
        sort_fields = []
        field_mapping = {
            "id": "g.id",
            "symbol": "g.approved_symbol",
            "approved_symbol": "g.approved_symbol",
            "hgnc_id": "g.hgnc_id",
            "score": "evidence_score",
            "evidence_score": "evidence_score",
            "count": "evidence_count",
            "evidence_count": "evidence_count",
            "created_at": "g.created_at",
            "updated_at": "g.updated_at",
        }

        for field in sort.split(","):
            field = field.strip()
            if field:
                if field.startswith("-"):
                    column = field[1:]
                    direction = "DESC NULLS LAST"
                else:
                    column = field.lstrip("+")
                    direction = "ASC NULLS FIRST"

                if column in field_mapping:
                    sort_fields.append(f"{field_mapping[column]} {direction}")

        if sort_fields:
            sort_clause = f" ORDER BY {', '.join(sort_fields)}"
    else:
        sort_clause = " ORDER BY gs.percentage_score DESC NULLS LAST, g.approved_symbol ASC"

    # Data query with aggregations and sorting
    data_query = f"""
        SELECT DISTINCT
            g.id,
            g.hgnc_id,
            g.approved_symbol,
            g.aliases,
            g.created_at,
            g.updated_at,
            COALESCE(gs.evidence_count, 0) as evidence_count,
            gs.percentage_score as evidence_score,
            COALESCE(
                array_agg(DISTINCT ge.source_name ORDER BY ge.source_name)
                FILTER (WHERE ge.source_name IS NOT NULL),
                ARRAY[]::text[]
            ) as sources
        FROM genes g
        LEFT JOIN gene_scores gs ON gs.gene_id = g.id
        LEFT JOIN gene_evidence ge ON g.id = ge.gene_id
        WHERE {where_clause}
        GROUP BY
            g.id, g.hgnc_id, g.approved_symbol, g.aliases,
            g.created_at, g.updated_at, gs.evidence_count, gs.percentage_score
        {sort_clause}
    """

    # Apply pagination
    page_number = params["page_number"]
    page_size = params["page_size"]
    offset = (page_number - 1) * page_size

    # Add pagination to data query
    final_query = f"{data_query} LIMIT :limit OFFSET :offset"
    query_params["limit"] = page_size
    query_params["offset"] = offset

    # Execute query
    results = db.execute(text(final_query), query_params).fetchall()

    # Transform to JSON:API format
    data = transform_gene_to_jsonapi(results)

    # Get metadata for filters dynamically
    # Get max evidence count
    max_count_result = db.execute(text("SELECT MAX(evidence_count) FROM gene_scores")).scalar() or 0

    # Get all available sources
    sources_result = db.execute(
        text("SELECT DISTINCT source_name FROM gene_evidence ORDER BY source_name")
    ).fetchall()
    available_sources = [row[0] for row in sources_result]

    filter_meta = {
        "evidence_score": {"min": 0, "max": 100},
        "evidence_count": {"min": 0, "max": max_count_result},
        "available_sources": available_sources,
    }

    # Build response using reusable helper
    response = build_jsonapi_response(
        data=data,
        total=total,
        page_number=page_number,
        page_size=page_size,
        base_url="/api/genes",
    )

    # Add filter metadata to response
    response["meta"]["filters"] = filter_meta
    return response


@router.get("/{gene_symbol}", response_model=dict)
@jsonapi_endpoint(resource_type="genes", model=Gene)
async def get_gene(
    gene_symbol: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get single gene by symbol with JSON:API format.
    """
    # Get gene (case-insensitive)
    gene = db.query(Gene).filter(func.upper(Gene.approved_symbol) == gene_symbol.upper()).first()

    if not gene:
        raise GeneNotFoundError(gene_symbol)

    # Get score data from view
    score_result = db.execute(
        text("""
            SELECT
                evidence_count,
                percentage_score,
                source_scores
            FROM gene_scores
            WHERE gene_id = :gene_id
        """),
        {"gene_id": gene.id},
    ).first()

    # Get sources
    sources_result = db.execute(
        text("""
            SELECT DISTINCT source_name
            FROM gene_evidence
            WHERE gene_id = :gene_id
            ORDER BY source_name
        """),
        {"gene_id": gene.id},
    ).fetchall()

    sources = [row[0] for row in sources_result]

    # Get score breakdown
    score_breakdown = {}
    if gene.id:
        breakdown_result = db.execute(
            text("""
                SELECT source_name, normalized_score
                FROM combined_evidence_scores
                WHERE gene_id = :gene_id
                ORDER BY source_name
            """),
            {"gene_id": gene.id},
        )
        for row in breakdown_result:
            score_breakdown[row[0]] = round(float(row[1]), 4) if row[1] is not None else 0.0

    # Format as JSON:API
    return {
        "data": {
            "type": "genes",
            "id": str(gene.id),
            "attributes": {
                "hgnc_id": gene.hgnc_id,
                "approved_symbol": gene.approved_symbol,
                "aliases": gene.aliases or [],
                "created_at": gene.created_at.isoformat() if gene.created_at else None,
                "updated_at": gene.updated_at.isoformat() if gene.updated_at else None,
                "evidence_count": score_result[0] if score_result else 0,
                "evidence_score": float(score_result[1])
                if score_result and score_result[1]
                else None,
                "sources": sources,
                "score_breakdown": score_breakdown,
                "source_scores": score_result[2] if score_result else {},
            },
        }
    }


@router.get("/{gene_symbol}/evidence", response_model=dict)
@jsonapi_endpoint(resource_type="evidence", model=GeneEvidence)
async def get_gene_evidence(
    gene_symbol: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get all evidence for a gene in JSON:API format.
    """
    # Get gene
    gene = db.query(Gene).filter(func.upper(Gene.approved_symbol) == gene_symbol.upper()).first()

    if not gene:
        raise GeneNotFoundError(gene_symbol)

    # Get evidence
    evidence = db.query(GeneEvidence).filter(GeneEvidence.gene_id == gene.id).all()

    # Get normalized scores
    normalized_scores = {}
    if gene.id:
        result = db.execute(
            text("""
                SELECT evidence_id, normalized_score
                FROM combined_evidence_scores
                WHERE gene_id = :gene_id
            """),
            {"gene_id": gene.id},
        )
        for row in result:
            normalized_scores[row[0]] = round(float(row[1]), 4) if row[1] is not None else 0.0

    # Format evidence as JSON:API
    evidence_data = []
    for e in evidence:
        evidence_data.append(
            {
                "type": "evidence",
                "id": str(e.id),
                "attributes": {
                    "source_name": e.source_name,
                    "source_detail": e.source_detail,
                    "evidence_data": e.evidence_data,
                    "evidence_date": e.evidence_date.isoformat() if e.evidence_date else None,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "normalized_score": normalized_scores.get(e.id, 0.0),
                },
                "relationships": {"gene": {"data": {"type": "genes", "id": str(gene.id)}}},
            }
        )

    return {
        "data": evidence_data,
        "meta": {
            "gene_symbol": gene.approved_symbol,
            "gene_id": gene.id,
            "evidence_count": len(evidence_data),
        },
    }


@router.post("/", response_model=dict)
async def create_gene(
    gene_in: GeneCreate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Create a new gene in JSON:API format.
    """
    from app.crud.gene import gene_crud

    # Check if gene already exists
    existing = (
        db.query(Gene)
        .filter(func.upper(Gene.approved_symbol) == gene_in.approved_symbol.upper())
        .first()
    )

    if existing:
        raise ValidationError(
            field="approved_symbol", reason=f"Gene '{gene_in.approved_symbol}' already exists"
        )

    # Create gene
    gene = gene_crud.create(db, gene_in)

    # Format as JSON:API
    return {
        "data": {
            "type": "genes",
            "id": str(gene.id),
            "attributes": {
                "hgnc_id": gene.hgnc_id,
                "approved_symbol": gene.approved_symbol,
                "aliases": gene.aliases or [],
                "created_at": gene.created_at.isoformat() if gene.created_at else None,
                "updated_at": gene.updated_at.isoformat() if gene.updated_at else None,
                "evidence_count": 0,
                "evidence_score": None,
                "sources": [],
            },
        }
    }
