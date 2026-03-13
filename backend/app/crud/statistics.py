"""
CRUD operations for statistics and data analysis
"""

from typing import Any, TypedDict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.gene_filters import (
    get_gene_evidence_filter_join,
)
from app.core.logging import get_logger
from app.crud.statistics_handlers import SourceDistributionHandlerFactory


class IntersectionDict(TypedDict):
    """Type for intersection data in source overlaps."""

    sets: list[str]
    size: int
    genes: list[str]


logger = get_logger(__name__)


class CRUDStatistics:
    """CRUD operations for statistics and data analysis"""

    def get_source_overlaps(
        self,
        db: Session,
        selected_sources: list[str] | None = None,
        hide_zero_scores: bool = True,
        filter_tiers: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Calculate gene intersections between data sources for UpSet plot visualization

        Args:
            db: Database session
            selected_sources: Optional list of source names to include. If None, uses all sources.
            hide_zero_scores: Hide genes with percentage_score = 0 (default: True)
            filter_tiers: Optional list of evidence tiers for filtering (comma-separated)

        Returns:
            Dictionary with sets and intersections data for UpSet.js
        """
        try:
            logger.sync_debug(
                "get_source_overlaps called",
                filter_tiers=filter_tiers,
                hide_zero_scores=hide_zero_scores,
                selected_sources=selected_sources,
            )

            # Build WHERE clause
            join_clause, filter_clause = get_gene_evidence_filter_join(hide_zero_scores)
            where_clauses = [filter_clause]

            # Add tier filtering if specified
            if filter_tiers and len(filter_tiers) > 0:
                # Ensure gene_scores JOIN exists (needed for gs.evidence_tier)
                if not join_clause:
                    join_clause = "INNER JOIN gene_scores gs ON gs.gene_id = gene_evidence.gene_id"
                tier_list_str = ", ".join([f"'{tier}'" for tier in filter_tiers])
                where_clauses.append(f"gs.evidence_tier IN ({tier_list_str})")
                logger.sync_debug("Added tier filtering", tier_list=tier_list_str)

            filter_clause = (
                " AND ".join(where_clauses) if len(where_clauses) > 1 else where_clauses[0]
            )

            # Build params dict for source filtering only
            params = {}

            # Add source filtering
            where_parts = [filter_clause]
            if selected_sources:
                where_parts.append("gene_evidence.source_name = ANY(:selected_sources)")
                params["selected_sources"] = selected_sources

            where_clause = "WHERE " + " AND ".join(where_parts) if where_parts else ""

            logger.sync_debug("WHERE clause built", where_clause=where_clause, params=params)

            # Single-query bitmask approach: assign a power-of-2 per source,
            # sum per gene, group by bitmask. O(1) DB queries instead of O(2^n).

            # Step 1: Get all source names for bitmask mapping
            source_names_result = db.execute(
                text(f"""
                    SELECT DISTINCT gene_evidence.source_name
                    FROM gene_evidence
                    {join_clause}
                    {where_clause}
                    ORDER BY gene_evidence.source_name
                """),
                params,
            ).fetchall()
            source_names = [row[0] for row in source_names_result]

            if not source_names:
                return {
                    "sets": [],
                    "intersections": [],
                    "total_unique_genes": 0,
                    "overlap_statistics": {
                        "highest_overlap_count": 0,
                        "genes_in_all_sources": 0,
                        "single_source_combinations": 0,
                        "total_combinations": 0,
                    },
                }

            # Build CASE expression for bitmask
            case_parts = []
            for i, _name in enumerate(source_names):
                case_parts.append(
                    f"WHEN gene_evidence.source_name = :src_{i} THEN {1 << i}"
                )
            case_expr = " ".join(case_parts)

            source_params = {f"src_{i}": name for i, name in enumerate(source_names)}
            all_params = {**params, **source_params}

            # Step 2: Single query -- bitmask per gene, grouped
            bitmask_query = f"""
                WITH gene_bitmasks AS (
                    SELECT
                        gene_evidence.gene_id,
                        SUM(DISTINCT CASE {case_expr} ELSE 0 END)::bigint
                            AS source_bitmask
                    FROM gene_evidence
                    {join_clause}
                    {where_clause}
                    GROUP BY gene_evidence.gene_id
                ),
                bitmask_groups AS (
                    SELECT
                        source_bitmask,
                        COUNT(*) AS gene_count,
                        array_agg(gene_id ORDER BY gene_id) AS gene_ids
                    FROM gene_bitmasks
                    GROUP BY source_bitmask
                )
                SELECT
                    bg.source_bitmask,
                    bg.gene_count,
                    array_agg(g.approved_symbol ORDER BY g.approved_symbol)
                        AS gene_symbols
                FROM bitmask_groups bg
                JOIN LATERAL unnest(bg.gene_ids) AS gid ON true
                JOIN genes g ON g.id = gid
                GROUP BY bg.source_bitmask, bg.gene_count
                ORDER BY bg.gene_count DESC
            """

            bitmask_results = db.execute(
                text(bitmask_query), all_params
            ).fetchall()

            # Step 3: Decode bitmasks into source combinations
            source_gene_counts: dict[str, int] = dict.fromkeys(source_names, 0)
            intersections: list[IntersectionDict] = []

            for row in bitmask_results:
                bitmask = int(row[0])
                gene_count = row[1]
                gene_symbols = list(row[2]) if row[2] else []

                # Decode which sources this bitmask represents
                combo_sources = [
                    source_names[i]
                    for i in range(len(source_names))
                    if bitmask & (1 << i)
                ]

                # Accumulate per-source totals
                for src in combo_sources:
                    source_gene_counts[src] += gene_count

                intersections.append({
                    "sets": combo_sources,
                    "size": gene_count,
                    "genes": gene_symbols,
                })

            # Build sets list
            sets = [
                {"name": name, "size": source_gene_counts[name]}
                for name in source_names
            ]

            # Sort intersections by size descending
            intersections.sort(key=lambda x: x["size"], reverse=True)

            # Summary statistics - count unique genes
            if selected_sources:
                total_genes_query = f"""
                    SELECT COUNT(DISTINCT gene_evidence.gene_id)
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause}
                    AND gene_evidence.source_name = ANY(:selected_sources)
                """
                total_unique_genes = (
                    db.execute(
                        text(total_genes_query),
                        {"selected_sources": selected_sources},
                    ).scalar()
                    or 0
                )
            else:
                total_genes_query = f"""
                    SELECT COUNT(DISTINCT gene_evidence.gene_id)
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause}
                """
                total_unique_genes = (
                    db.execute(text(total_genes_query)).scalar() or 0
                )

            # Find genes in all sources from bitmask results
            genes_in_all_sources = 0
            for intersection in intersections:
                if len(intersection["sets"]) == len(source_names):
                    genes_in_all_sources = intersection["size"]
                    break

            # Count single-source combinations
            single_source_count = sum(
                1
                for intersection in intersections
                if len(intersection["sets"]) == 1
            )

            return {
                "sets": sets,
                "intersections": intersections,
                "total_unique_genes": total_unique_genes,
                "overlap_statistics": {
                    "highest_overlap_count": len(source_names),
                    "genes_in_all_sources": genes_in_all_sources,
                    "single_source_combinations": single_source_count,
                    "total_combinations": len(intersections),
                },
            }

        except Exception as e:
            logger.sync_error(
                "Error calculating source overlaps", error=e, selected_sources=selected_sources
            )
            raise

    def get_pairwise_overlaps_from_view(self, db: Session) -> list[dict[str, Any]]:
        """
        Read pre-computed pairwise source overlap statistics from the materialized view.

        Returns unfiltered overlap data. For filtered queries, use get_source_overlaps() instead.
        """
        try:
            rows = db.execute(
                text(
                    "SELECT source1, source2, overlap_count, "
                    "source1_total, source2_total, overlap_percentage "
                    "FROM source_overlap_statistics "
                    "ORDER BY overlap_count DESC"
                )
            ).fetchall()
            return [
                {
                    "source1": r[0],
                    "source2": r[1],
                    "overlap_count": r[2],
                    "source1_total": r[3],
                    "source2_total": r[4],
                    "overlap_percentage": float(r[5]),
                }
                for r in rows
            ]
        except Exception as e:
            logger.sync_error("Error reading source_overlap_statistics view", error=e)
            raise

    def get_source_distributions(
        self, db: Session, hide_zero_scores: bool = True, filter_tiers: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Calculate source-specific distributions using handler pattern.

        Args:
            db: Database session
            hide_zero_scores: Hide genes with percentage_score = 0 (default: True)
            filter_tiers: Optional list of evidence tiers for filtering

        Returns:
            Dict with source-specific distribution data
        """
        try:
            logger.sync_debug(
                "get_source_distributions called",
                filter_tiers=filter_tiers,
                hide_zero_scores=hide_zero_scores,
            )

            # Build WHERE clause
            join_clause, filter_clause = get_gene_evidence_filter_join(hide_zero_scores)
            where_clauses = [filter_clause]

            # Add tier filtering if specified
            if filter_tiers:
                if not join_clause:
                    join_clause = "INNER JOIN gene_scores gs ON gs.gene_id = gene_evidence.gene_id"
                tier_list_str = ", ".join([f"'{tier}'" for tier in filter_tiers])
                where_clauses.append(f"gs.evidence_tier IN ({tier_list_str})")

            filter_clause = (
                " AND ".join(where_clauses) if len(where_clauses) > 1 else where_clauses[0]
            )

            logger.sync_debug(
                "WHERE clause built for source distributions",
                join_clause=join_clause,
                filter_clause=filter_clause,
            )

            # Get all sources with filtering
            sources_query = f"""
                SELECT DISTINCT gene_evidence.source_name
                FROM gene_evidence
                {join_clause}
                WHERE {filter_clause}
                ORDER BY gene_evidence.source_name
            """
            sources = db.execute(text(sources_query)).fetchall()

            source_distributions = {}

            for source_row in sources:
                source_name = source_row[0]

                # Get appropriate handler for source
                handler = SourceDistributionHandlerFactory.get_handler(source_name)

                # Get distribution data using handler
                distribution_data, metadata = handler.get_distribution(
                    db, join_clause, filter_clause
                )

                # Convert to response format
                distribution = [
                    {"category": row[0], "gene_count": row[1]} for row in distribution_data
                ]

                source_distributions[source_name] = {
                    "distribution": distribution,
                    "metadata": metadata,
                }

            logger.sync_info(
                "Source distributions calculated",
                sources=len(source_distributions),
                filter_tiers=filter_tiers,
            )

            return source_distributions

        except Exception as e:
            logger.sync_error(
                "Error calculating source distributions", error=e, filter_tiers=filter_tiers
            )
            raise

    def get_evidence_composition(
        self, db: Session, filter_tiers: list[str] | None = None, hide_zero_scores: bool = True
    ) -> dict[str, Any]:
        """
        Analyze evidence quality and composition across sources

        Args:
            db: Database session
            filter_tiers: Optional list of evidence tiers for filtering
            hide_zero_scores: Hide genes with percentage_score = 0 (default: True, matching /genes endpoint)

        Returns:
            Dictionary with evidence composition analysis using actual evidence_tier column
        """
        try:
            # Tier label and color mapping (matches frontend evidenceTiers.js)
            tier_config_map = {
                "comprehensive_support": {
                    "label": "Comprehensive Support",
                    "color": "#4CAF50",  # success (green)
                    "order": 1,
                },
                "multi_source_support": {
                    "label": "Multi-Source Support",
                    "color": "#2196F3",  # info (blue)
                    "order": 2,
                },
                "established_support": {
                    "label": "Established Support",
                    "color": "#1976D2",  # primary (darker blue)
                    "order": 3,
                },
                "preliminary_evidence": {
                    "label": "Preliminary Evidence",
                    "color": "#FFC107",  # warning (amber)
                    "order": 4,
                },
                "minimal_evidence": {
                    "label": "Minimal Evidence",
                    "color": "#9E9E9E",  # grey
                    "order": 5,
                },
                "no_evidence": {
                    "label": "Insufficient Evidence",
                    "color": "#BDBDBD",  # lighter grey
                    "order": 6,
                },
            }

            # Build WHERE clause - filter out zero scores by default (matches /genes endpoint behavior)
            where_clauses = []
            if hide_zero_scores:
                where_clauses.append("gs.percentage_score > 0")

            # Add tier filter if specified (multi-select with OR logic)
            if filter_tiers:
                tier_list_str = ", ".join(f"'{tier}'" for tier in filter_tiers)
                where_clauses.append(f"gs.evidence_tier IN ({tier_list_str})")

            where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Query actual evidence_tier column from gene_scores view (NOT percentage_score ranges!)
            score_distribution = db.execute(
                text(f"""
                    SELECT
                        gs.evidence_tier,
                        COUNT(*) as gene_count,
                        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
                    FROM gene_scores gs
                    {where_clause}
                    GROUP BY gs.evidence_tier
                    ORDER BY
                        CASE gs.evidence_tier
                            WHEN 'comprehensive_support' THEN 1
                            WHEN 'multi_source_support' THEN 2
                            WHEN 'established_support' THEN 3
                            WHEN 'preliminary_evidence' THEN 4
                            WHEN 'minimal_evidence' THEN 5
                            WHEN 'no_evidence' THEN 6
                            ELSE 7
                        END
                """)
            ).fetchall()

            # Build tier distribution with proper labels and colors
            evidence_tier_distribution = [
                {
                    "tier": row[0],
                    "tier_label": tier_config_map.get(row[0], {}).get("label", row[0]),
                    "gene_count": row[1],
                    "percentage": row[2],
                    "color": tier_config_map.get(row[0], {}).get("color", "#BDBDBD"),
                }
                for row in score_distribution
                if row[0]
                in tier_config_map  # Now includes 'no_evidence' when hide_zero_scores=False
            ]

            # Calculate source contribution weights (respecting hide_zero_scores filter)
            source_stats = db.execute(
                text(f"""
                    SELECT
                        ge.source_name,
                        COUNT(DISTINCT ge.gene_id) as gene_count,
                        COUNT(*) as evidence_count
                    FROM gene_evidence ge
                    INNER JOIN gene_scores gs ON ge.gene_id = gs.gene_id
                    {where_clause}
                    GROUP BY ge.source_name
                    ORDER BY gene_count DESC
                """)
            ).fetchall()

            total_evidence = sum(row[2] for row in source_stats)
            source_contribution_weights = {}

            for row in source_stats:
                source_name = row[0]
                evidence_count = row[2]
                weight = evidence_count / total_evidence if total_evidence > 0 else 0
                source_contribution_weights[source_name] = round(weight, 3)

            # Get source coverage statistics
            coverage_stats = db.execute(
                text(f"""
                    SELECT
                        gs.source_count,
                        COUNT(*) as gene_count,
                        ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER()), 2) as percentage
                    FROM gene_scores gs
                    {where_clause}
                    GROUP BY gs.source_count
                    ORDER BY gs.source_count DESC
                """)
            ).fetchall()

            source_coverage_distribution = [
                {"source_count": row[0], "gene_count": row[1], "percentage": row[2]}
                for row in coverage_stats
            ]

            return {
                "evidence_tier_distribution": evidence_tier_distribution,  # FIXED: Use correct field name
                "evidence_quality_distribution": evidence_tier_distribution,  # Backward compatibility
                "source_contribution_weights": source_contribution_weights,
                "source_coverage_distribution": source_coverage_distribution,
                "summary_statistics": {
                    "total_genes": sum(item["gene_count"] for item in evidence_tier_distribution),
                    "total_evidence_records": total_evidence,
                    "active_sources": len(source_stats),
                    "avg_sources_per_gene": round(
                        sum(row[0] * row[1] for row in coverage_stats)
                        / sum(row[1] for row in coverage_stats),
                        2,
                    )
                    if coverage_stats
                    else 0,
                },
            }

        except Exception as e:
            logger.sync_error(
                "Error analyzing evidence composition", error=e, filter_tiers=filter_tiers
            )
            raise


# Create singleton instance
statistics_crud = CRUDStatistics()
