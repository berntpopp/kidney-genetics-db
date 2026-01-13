"""
Gene API endpoints - JSON:API compliant using reusable components
"""

import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.datasource_config import API_DEFAULTS_CONFIG
from app.core.exceptions import GeneNotFoundError, ValidationError
from app.core.jsonapi import (
    build_jsonapi_response,
    get_jsonapi_params,
    get_range_filters,
    get_search_filter,
    get_sort_param,
    jsonapi_endpoint,
)
from app.core.logging import get_logger
from app.models.gene import Gene, GeneEvidence
from app.schemas.gene import GeneCreate
from app.schemas.network import (
    HPOClassificationData,
    HPOClassificationRequest,
    HPOClassificationResponse,
)

router = APIRouter()
logger = get_logger(__name__)

# Module-level cache for filter metadata (FastAPI recommended pattern)
_metadata_cache: dict[str, Any] = {"data": None, "timestamp": None}
_CACHE_TTL = timedelta(minutes=5)  # Semi-static data standard

# Module-level cache for HPO classifications (static data until pipeline runs)
_hpo_classifications_cache: dict[str, Any] = {"data": None, "timestamp": None}
_HPO_CACHE_TTL = timedelta(hours=1)  # HPO data changes infrequently

# Module-level cache for gene IDs queries (for URL state restoration)
_gene_ids_cache: dict[str, Any] = {}
_GENE_IDS_CACHE_TTL = timedelta(hours=1)  # Genes are semi-static

# Note: Gene annotations endpoint has been moved to the gene_annotations module
# to maintain better separation of concerns and avoid duplicate endpoints


def get_filter_metadata(db: Session) -> dict[str, Any]:
    """
    Get filter metadata with TTL-based caching.

    Caches for 5 minutes (metadata only changes when pipeline runs).
    Follows FastAPI best practice for semi-static data.

    Returns:
        dict: Filter metadata including max_count, sources, and tier distribution
    """
    now = datetime.utcnow()

    # Check cache validity
    cached_data: dict[str, Any] | None = _metadata_cache["data"]
    if cached_data and _metadata_cache["timestamp"]:
        age = now - _metadata_cache["timestamp"]
        if age < _CACHE_TTL:
            logger.sync_debug("Metadata cache HIT", age_seconds=round(age.total_seconds(), 2))
            return cached_data

    logger.sync_debug("Metadata cache MISS - fetching fresh data")

    # Cache miss or expired - fetch fresh data
    try:
        # Max evidence count
        max_count_result = db.execute(text("SELECT MAX(evidence_count) FROM gene_scores")).scalar()

        # Available sources
        sources_result = db.execute(
            text("SELECT DISTINCT source_name FROM gene_evidence ORDER BY source_name")
        ).fetchall()

        # Tier distribution
        tier_distribution_query = text("""
            SELECT
                evidence_group,
                evidence_tier,
                COUNT(*) as gene_count
            FROM gene_scores
            WHERE percentage_score > 0
            GROUP BY evidence_group, evidence_tier
            ORDER BY
                CASE evidence_group
                    WHEN 'well_supported' THEN 1
                    WHEN 'emerging_evidence' THEN 2
                    ELSE 3
                END,
                MIN(percentage_score) DESC
        """)
        tier_results = db.execute(tier_distribution_query).fetchall()

        # Build tier metadata structure
        tier_meta: dict[str, dict[str, int]] = {"well_supported": {}, "emerging_evidence": {}}

        for row in tier_results:
            group = row.evidence_group
            tier = row.evidence_tier
            count = row.gene_count
            if group in tier_meta:
                tier_meta[group][tier] = count

        # Calculate group totals
        tier_meta["well_supported"]["total"] = sum(tier_meta["well_supported"].values())
        tier_meta["emerging_evidence"]["total"] = sum(tier_meta["emerging_evidence"].values())

        metadata = {
            "max_count": max_count_result or 0,
            "sources": [row[0] for row in sources_result],
            "tier_distribution": tier_meta,
        }

        # Update cache
        _metadata_cache["data"] = metadata
        _metadata_cache["timestamp"] = now

        return metadata

    except Exception as e:
        # On error, return cached data if available, otherwise raise
        logger.sync_error(f"Error fetching filter metadata: {e}")
        stale_data: dict[str, Any] | None = _metadata_cache["data"]
        if stale_data:
            logger.sync_warning("Returning stale cached metadata due to error")
            return stale_data
        raise


def invalidate_metadata_cache() -> None:
    """
    Invalidate metadata cache.
    Call this after pipeline updates to force fresh data on next request.
    """
    _metadata_cache["data"] = None
    _metadata_cache["timestamp"] = None
    logger.sync_info("Metadata cache invalidated")


def clear_gene_ids_cache() -> None:
    """
    Clear gene IDs cache.
    Call this after pipeline updates to force fresh data on next request.
    Used for URL state restoration queries.
    """
    global _gene_ids_cache
    _gene_ids_cache = {}
    logger.sync_info("Gene IDs cache cleared")


@lru_cache(maxsize=1)
def get_total_gene_count(db_session_id: int) -> int:
    """
    Get total gene count with caching.

    Count changes rarely (only when genes added). Uses session ID to
    invalidate cache on new sessions. FastAPI recommended pattern.

    Args:
        db_session_id: Database session ID (use id(db) to get unique ID)

    Returns:
        int: Total number of genes in database
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        result = db.execute(text("SELECT COUNT(*) FROM genes")).scalar()
        return result or 0
    finally:
        db.close()


def log_slow_query(
    query_name: str,
    execution_time_ms: float,
    threshold_ms: float = 50,
    query_preview: str | None = None,
) -> None:
    """
    Log queries that exceed performance threshold.

    Queries >50ms should be monitored. Queries >100ms should be
    considered for thread pool offloading to prevent event loop blocking.

    Args:
        query_name: Descriptive name of the query
        execution_time_ms: Query execution time in milliseconds
        threshold_ms: Threshold above which to log (default: 50ms)
        query_preview: Optional query preview (first 200 chars)
    """
    if execution_time_ms > threshold_ms:
        # Suggest thread pool offloading for very slow queries
        if execution_time_ms > 100:
            logger.sync_warning(
                f"CONSIDER OFFLOADING: {query_name}",
                execution_time_ms=round(execution_time_ms, 2),
                threshold_ms=threshold_ms,
                recommendation="Use loop.run_in_executor() or run_in_threadpool() for queries >100ms",
                query_preview=query_preview[:200] if query_preview else None,
            )
        else:
            logger.sync_warning(
                f"Slow query detected: {query_name}",
                execution_time_ms=round(execution_time_ms, 2),
                threshold_ms=threshold_ms,
                query_preview=query_preview[:200] if query_preview else None,
            )


def transform_gene_to_jsonapi(results: Any) -> list[dict[str, Any]]:
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
                    "evidence_tier": row[8],
                    "evidence_group": row[9],
                    # Skip row[10] (tier_sort_order) and row[11] (group_sort_order) - internal use only
                    "sources": list(row[12]) if row[12] else [],
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
    hide_zero_scores: bool = Query(
        default=API_DEFAULTS_CONFIG.get("hide_zero_scores", True),
        alias="filter[hide_zero_scores]",
        description="Hide genes with evidence_score=0 (default: true)",
    ),
    filter_tier: str | None = Query(
        None,
        alias="filter[tier]",
        description="Filter by evidence tier (comprehensive_support, multi_source_support, established_support, preliminary_evidence, minimal_evidence)",
    ),
    filter_group: str | None = Query(
        None,
        alias="filter[group]",
        description="Filter by evidence group (well_supported, emerging_evidence)",
    ),
    # NEW: Filter by gene IDs (for URL state restoration)
    filter_ids: str | None = Query(
        None,
        alias="filter[ids]",
        description=f"Filter by gene IDs (comma-separated, max {API_DEFAULTS_CONFIG.get('max_gene_ids', 5000)}). Used for URL state restoration.",
    ),
    # JSON:API sorting
    sort: str | None = Depends(get_sort_param("-evidence_score,approved_symbol")),
) -> dict[str, Any]:
    """
    Get genes with JSON:API compliant response using reusable components.

    Query parameters follow JSON:API specification:
    - Pagination: page[number], page[size]
    - Filtering: filter[search], filter[min_score], filter[source], filter[ids], etc.
    - Sorting: sort=-evidence_score,approved_symbol (prefix with - for descending)

    NEW: filter[ids] - Filter by comma-separated gene IDs for URL state restoration.
              Used when users share network analysis URLs with specific gene sets.
              Example: /api/genes?filter[ids]=1,2,3,4,5&page[size]=100
    """
    # IMPORTANT: Do NOT cache filter[ids] queries because:
    # 1. They are paginated requests (page 1, 2, 3, etc.)
    # 2. Cache key doesn't include page number, causing all pages to return same cached result
    # 3. This is only used for URL restoration (one-time operation), so caching provides no benefit
    # 4. Caching was causing bug: 614 IDs requested but 700 genes returned (page 1 cached, returned 7 times)
    #
    # If caching is needed in future, cache key MUST include page number:
    # cache_key = f"genes_ids_{filter_ids}_page{page_number}"

    # Build WHERE clauses first
    where_clauses: list[str] = ["1=1"]
    query_params: dict[str, Any] = {}

    # Apply filters
    if search:
        where_clauses.append(
            "(g.approved_symbol ILIKE :search OR g.hgnc_id ILIKE :search OR "
            "gs.evidence_tier ILIKE :search OR gs.evidence_group ILIKE :search)"
        )
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

    # Hide genes with evidence_score=0 if enabled
    if hide_zero_scores:
        where_clauses.append("gs.percentage_score > 0")

    # Filter by evidence tier (supports multiple tiers with OR logic)
    if filter_tier:
        valid_tiers = [
            "comprehensive_support",
            "multi_source_support",
            "established_support",
            "preliminary_evidence",
            "minimal_evidence",
        ]
        # Parse comma-separated tiers
        requested_tiers = [t.strip() for t in filter_tier.split(",") if t.strip()]

        # Validate all requested tiers
        invalid_tiers = [t for t in requested_tiers if t not in valid_tiers]
        if invalid_tiers:
            raise ValidationError(
                field="filter[tier]",
                reason=f"Invalid tier(s): {', '.join(invalid_tiers)}. Must be one of: {', '.join(valid_tiers)}",
            )

        if requested_tiers:
            # Use IN clause for OR logic
            placeholders = ",".join([f":tier_{i}" for i in range(len(requested_tiers))])
            where_clauses.append(f"gs.evidence_tier IN ({placeholders})")
            for i, tier in enumerate(requested_tiers):
                query_params[f"tier_{i}"] = tier

    # Filter by evidence group
    if filter_group:
        valid_groups = ["well_supported", "emerging_evidence"]
        if filter_group not in valid_groups:
            raise ValidationError(
                field="filter[group]",
                reason=f"Invalid group. Must be one of: {', '.join(valid_groups)}",
            )
        where_clauses.append("gs.evidence_group = :group")
        query_params["group"] = filter_group

    # NEW: Filter by gene IDs (for URL state restoration)
    if filter_ids:
        # Parse and validate gene IDs
        requested_ids = []
        for id_str in filter_ids.split(","):
            id_str = id_str.strip()
            if id_str.isdigit():
                requested_ids.append(int(id_str))

        if not requested_ids:
            raise ValidationError(field="filter[ids]", reason="No valid gene IDs provided")

        # Limit to prevent abuse (uses configuration, not hardcoded)
        max_gene_ids = API_DEFAULTS_CONFIG.get("max_gene_ids", 5000)
        if len(requested_ids) > max_gene_ids:
            raise ValidationError(
                field="filter[ids]", reason=f"Maximum {max_gene_ids} gene IDs allowed per request"
            )

        # Build IN clause
        placeholders = ",".join([f":id_{i}" for i in range(len(requested_ids))])
        where_clauses.append(f"g.id IN ({placeholders})")
        for i, gene_id in enumerate(requested_ids):
            query_params[f"id_{i}"] = gene_id

        logger.sync_debug(
            "Filtering by gene IDs", count=len(requested_ids), first_five=requested_ids[:5]
        )

    where_clause = " AND ".join(where_clauses)

    # Simple count query without complex aggregations
    # Note: gene_evidence not joined here as source filtering uses EXISTS subquery
    count_query = f"""
        SELECT COUNT(DISTINCT g.id)
        FROM genes g
        LEFT JOIN gene_scores gs ON gs.gene_id = g.id
        WHERE {where_clause}
    """
    start_time = time.time()
    total = db.execute(text(count_query), query_params).scalar() or 0
    count_time_ms = (time.time() - start_time) * 1000
    log_slow_query("count_query", count_time_ms, query_preview=count_query)

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
            "evidence_tier": "tier_sort_order",
            "evidence_group": "group_sort_order",
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

    # Data query - sources and evidence_count fetched from gene_evidence table for accuracy
    # Note: Uses correlated subqueries to get actual data (not cached gene_scores values)
    data_query = f"""
        SELECT
            g.id,
            g.hgnc_id,
            g.approved_symbol,
            g.aliases,
            g.created_at,
            g.updated_at,
            COALESCE(
                (SELECT COUNT(*) FROM gene_evidence WHERE gene_id = g.id),
                0
            ) as evidence_count,
            gs.percentage_score as evidence_score,
            gs.evidence_tier,
            gs.evidence_group,
            CASE gs.evidence_tier
                WHEN 'comprehensive_support' THEN 1
                WHEN 'multi_source_support' THEN 2
                WHEN 'established_support' THEN 3
                WHEN 'preliminary_evidence' THEN 4
                WHEN 'minimal_evidence' THEN 5
                ELSE 999
            END as tier_sort_order,
            CASE gs.evidence_group
                WHEN 'well_supported' THEN 1
                WHEN 'emerging_evidence' THEN 2
                ELSE 999
            END as group_sort_order,
            COALESCE(
                (SELECT array_agg(DISTINCT source_name ORDER BY source_name)
                 FROM gene_evidence
                 WHERE gene_id = g.id),
                ARRAY[]::text[]
            ) as sources
        FROM genes g
        LEFT JOIN gene_scores gs ON gs.gene_id = g.id
        WHERE {where_clause}
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
    start_time = time.time()
    results = db.execute(text(final_query), query_params).fetchall()
    data_query_time_ms = (time.time() - start_time) * 1000
    log_slow_query("data_query", data_query_time_ms, query_preview=final_query)

    # Transform to JSON:API format
    data = transform_gene_to_jsonapi(results)

    # Get cached filter metadata (replaces 3 queries with single cached call)
    cached_metadata = get_filter_metadata(db)

    filter_meta = {
        "evidence_score": {"min": 0, "max": 100},
        "evidence_count": {"min": 0, "max": cached_metadata["max_count"]},
        "available_sources": cached_metadata["sources"],
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
    response["meta"]["evidence_tiers"] = cached_metadata["tier_distribution"]
    response["meta"]["valid_tiers"] = [
        "comprehensive_support",
        "multi_source_support",
        "established_support",
        "preliminary_evidence",
        "minimal_evidence",
    ]
    response["meta"]["valid_groups"] = ["well_supported", "emerging_evidence"]

    # Add zero-score filtering metadata
    if hide_zero_scores:
        # Use cached total gene count (session ID invalidates cache on new sessions)
        total_all_genes = get_total_gene_count(id(db))
        response["meta"]["total_genes"] = total_all_genes
        response["meta"]["hidden_zero_scores"] = total_all_genes - total
    else:
        response["meta"]["total_genes"] = total
        response["meta"]["hidden_zero_scores"] = 0

    # NOTE: We do NOT cache filter[ids] queries (see comment above for explanation)
    # This prevents the pagination bug where all pages return the same cached result

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
                source_scores,
                evidence_tier,
                evidence_group
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
                # Use actual count from gene_evidence (sources already fetched from there)
                "evidence_count": len(sources),
                "evidence_score": float(score_result[1])
                if score_result and score_result[1]
                else None,
                "evidence_tier": score_result[3] if score_result else None,
                "evidence_group": score_result[4] if score_result else None,
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


@router.post("/hpo-classifications", response_model=HPOClassificationResponse)
async def get_hpo_classifications(
    request: HPOClassificationRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get HPO clinical classifications for specified genes.

    Fetches classification data from gene_hpo_classifications view, which extracts
    clinical_group, onset_group, and is_syndromic from HPO annotations.

    This endpoint is optimized for network visualization coloring by clinical
    category instead of clustering assignments.

    Performance: <100ms for 1000 genes (cached), <500ms (uncached)

    Args:
        request: List of gene IDs to fetch classifications for
        db: Database session

    Returns:
        HPOClassificationResponse with gene classifications and metadata

    Raises:
        ValidationError: If gene_ids list is invalid (empty or >1000 items)
    """
    start_time = time.time()
    cache_key = f"hpo_classifications_{hash(tuple(sorted(request.gene_ids)))}"

    await logger.info(
        "Fetching HPO classifications",
        gene_count=len(request.gene_ids),
        cache_key=cache_key,
    )

    # Check cache
    now = datetime.utcnow()
    if _hpo_classifications_cache.get(cache_key):
        cached_data = _hpo_classifications_cache[cache_key]
        if cached_data.get("timestamp"):
            age = now - cached_data["timestamp"]
            if age < _HPO_CACHE_TTL:
                fetch_time_ms = round((time.time() - start_time) * 1000, 2)
                await logger.info(
                    "HPO classifications cache HIT",
                    cache_age_seconds=round(age.total_seconds(), 2),
                    fetch_time_ms=fetch_time_ms,
                )
                return {
                    "data": cached_data["data"],
                    "metadata": {
                        "cached": True,
                        "gene_count": len(cached_data["data"]),
                        "fetch_time_ms": fetch_time_ms,
                        "cache_age_seconds": round(age.total_seconds(), 2),
                    },
                }

    await logger.debug("HPO classifications cache MISS - fetching from database")

    # Fetch from database view
    try:
        query = text("""
            SELECT
                gene_id,
                gene_symbol,
                clinical_group,
                onset_group,
                is_syndromic
            FROM gene_hpo_classifications
            WHERE gene_id = ANY(:gene_ids)
        """)

        result = db.execute(query, {"gene_ids": request.gene_ids}).fetchall()

        # Convert to response format
        classifications = [
            HPOClassificationData(
                gene_id=row.gene_id,
                gene_symbol=row.gene_symbol,
                clinical_group=row.clinical_group,
                onset_group=row.onset_group,
                is_syndromic=row.is_syndromic,
            )
            for row in result
        ]

        fetch_time_ms = round((time.time() - start_time) * 1000, 2)

        await logger.info(
            "Fetched HPO classifications from database",
            requested_genes=len(request.gene_ids),
            returned_classifications=len(classifications),
            fetch_time_ms=fetch_time_ms,
        )

        # Update cache
        _hpo_classifications_cache[cache_key] = {
            "data": classifications,
            "timestamp": now,
        }

        return {
            "data": classifications,
            "metadata": {
                "cached": False,
                "gene_count": len(classifications),
                "fetch_time_ms": fetch_time_ms,
            },
        }

    except Exception as e:
        await logger.error(
            "Failed to fetch HPO classifications",
            error=e,
            gene_count=len(request.gene_ids),
        )
        raise
