"""
CRUD operations for statistics and data analysis
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.gene_filters import (
    get_gene_evidence_filter_join,
)
from app.core.logging import get_logger
from app.crud.statistics_handlers import SourceDistributionHandlerFactory

logger = get_logger(__name__)


class CRUDStatistics:
    """CRUD operations for statistics and data analysis"""

    def get_source_overlaps(
        self, db: Session, selected_sources: list[str] | None = None, min_tier: str | None = None
    ) -> dict[str, Any]:
        """
        Calculate gene intersections between data sources for UpSet plot visualization

        Args:
            db: Database session
            selected_sources: Optional list of source names to include. If None, uses all sources.
            min_tier: Optional minimum evidence tier for filtering

        Returns:
            Dictionary with sets and intersections data for UpSet.js
        """
        try:
            from app.core.gene_filters import get_tier_filter_join_clause

            # Build WHERE clause for source filtering, score filtering, and tier filtering
            join_clause, filter_clause = get_tier_filter_join_clause(min_tier)
            where_clauses = [filter_clause]
            params = {}

            if selected_sources:
                where_clauses.append("gene_evidence.source_name = ANY(:selected_sources)")
                params["selected_sources"] = selected_sources

            where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Get source names and their gene counts (filtered by both source and score)
            sources_query = f"""
                SELECT
                    gene_evidence.source_name,
                    COUNT(DISTINCT gene_evidence.gene_id) as gene_count,
                    array_agg(DISTINCT gene_evidence.gene_id ORDER BY gene_evidence.gene_id) as gene_ids
                FROM gene_evidence
                {join_clause}
                {where_clause}
                GROUP BY gene_evidence.source_name
                ORDER BY gene_evidence.source_name
            """

            sources_result = db.execute(text(sources_query), params).fetchall()

            # Build sets data
            sets = []
            source_gene_map = {}

            for row in sources_result:
                source_name = row[0]
                gene_count = row[1]
                gene_ids = list(row[2]) if row[2] else []

                sets.append({"name": source_name, "size": gene_count})
                source_gene_map[source_name] = set(gene_ids)

            # Calculate all possible intersections using set theory
            source_names = list(source_gene_map.keys())
            intersections = []

            # Generate all possible combinations (2^n - 1, excluding empty set)
            from itertools import combinations

            for r in range(1, len(source_names) + 1):
                for combo in combinations(source_names, r):
                    # Find intersection of all sources in this combination
                    gene_intersection = source_gene_map[combo[0]].copy()
                    for source in combo[1:]:
                        gene_intersection &= source_gene_map[source]

                    # Exclude genes that appear in sources not in this combination
                    for source in source_names:
                        if source not in combo:
                            gene_intersection -= source_gene_map[source]

                    if gene_intersection:  # Only include non-empty intersections
                        # Get gene symbols for the intersection
                        gene_symbols = db.execute(
                            text("""
                                SELECT approved_symbol
                                FROM genes
                                WHERE id = ANY(:gene_ids)
                                ORDER BY approved_symbol
                            """),
                            {"gene_ids": list(gene_intersection)},
                        ).fetchall()

                        intersections.append(
                            {
                                "sets": list(combo),
                                "size": len(gene_intersection),
                                "genes": [row[0] for row in gene_symbols],
                            }
                        )

            # Sort intersections by size (descending) for better visualization
            intersections.sort(key=lambda x: x["size"], reverse=True)

            # Calculate summary statistics - count unique genes in selected sources
            if selected_sources:
                # Use the same tier filter as the main query
                total_genes_query = f"""
                    SELECT COUNT(DISTINCT gene_evidence.gene_id)
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause}
                    AND gene_evidence.source_name = ANY(:selected_sources)
                """
                total_unique_genes = (
                    db.execute(
                        text(total_genes_query), {"selected_sources": selected_sources}
                    ).scalar()
                    or 0
                )
            else:
                # If no source filter, count all genes respecting tier filter
                total_genes_query = f"""
                    SELECT COUNT(DISTINCT gene_evidence.gene_id)
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause}
                """
                total_unique_genes = (
                    db.execute(text(total_genes_query)).scalar()
                    or 0
                )

            # Find genes that appear in all sources
            all_sources_genes = set(source_gene_map[source_names[0]])
            for source in source_names[1:]:
                all_sources_genes &= source_gene_map[source]

            # Find genes that appear in only one source
            single_source_count = sum(
                1 for intersection in intersections if len(intersection["sets"]) == 1
            )

            return {
                "sets": sets,
                "intersections": intersections,
                "total_unique_genes": total_unique_genes,
                "overlap_statistics": {
                    "highest_overlap_count": len(source_names),
                    "genes_in_all_sources": len(all_sources_genes),
                    "single_source_combinations": single_source_count,
                    "total_combinations": len(intersections),
                },
            }

        except Exception as e:
            logger.sync_error(
                "Error calculating source overlaps", error=e, selected_sources=selected_sources
            )
            raise

    def get_source_distributions(
        self,
        db: Session,
        min_tier: str | None = None
    ) -> dict[str, Any]:
        """
        Calculate source-specific distributions using handler pattern.

        Args:
            db: Database session
            min_tier: Optional minimum evidence tier for filtering

        Returns:
            Dict with source-specific distribution data
        """
        try:
            from app.core.gene_filters import get_tier_filter_join_clause

            logger.sync_info("Calculating source distributions", min_tier=min_tier)

            # Get filter clauses (respects score filter + tier filter)
            join_clause, filter_clause = get_tier_filter_join_clause(min_tier)

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
                    {"category": row[0], "gene_count": row[1]}
                    for row in distribution_data
                ]

                source_distributions[source_name] = {
                    "distribution": distribution,
                    "metadata": metadata,
                }

            logger.sync_info(
                "Source distributions calculated",
                sources=len(source_distributions),
                min_tier=min_tier
            )

            return source_distributions

        except Exception as e:
            logger.sync_error(
                "Error calculating source distributions",
                error=e,
                min_tier=min_tier
            )
            raise

    def get_source_distributions_old(self, db: Session) -> dict[str, Any]:
        """
        DEPRECATED: Old implementation with embedded SQL.
        Kept temporarily for reference. Will be removed after frontend migration.

        Calculate source count distributions for bar chart visualizations

        Returns:
            Dictionary with distribution data for each source
        """
        try:
            # Get all sources (filtered by score if configured)
            join_clause, filter_clause = get_gene_evidence_filter_join()
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

                # For sources with countable elements (panels, publications, etc.)
                if source_name == "PanelApp":
                    # Count panels per gene (with score filtering)
                    join_for_dist, filter_for_dist = get_gene_evidence_filter_join()
                    distribution_data = db.execute(
                        text(f"""
                            SELECT
                                panel_count,
                                COUNT(*) as gene_count
                            FROM (
                                SELECT
                                    gene_evidence.gene_id,
                                    jsonb_array_length(COALESCE(gene_evidence.evidence_data->'panels', '[]'::jsonb)) as panel_count
                                FROM gene_evidence
                                {join_for_dist}
                                WHERE {filter_for_dist} AND gene_evidence.source_name = :source_name
                            ) panel_counts
                            GROUP BY panel_count
                            ORDER BY panel_count
                        """),
                        {"source_name": source_name},
                    ).fetchall()

                    metadata = db.execute(
                        text("""
                            WITH panel_stats AS (
                                SELECT
                                    jsonb_array_length(COALESCE(evidence_data->'panels', '[]'::jsonb)) as panel_count
                                FROM gene_evidence
                                WHERE source_name = :source_name
                            )
                            SELECT
                                COUNT(DISTINCT panel_count) as total_unique_counts,
                                MAX(panel_count) as max_panels_per_gene,
                                AVG(panel_count::float) as avg_panels_per_gene
                            FROM panel_stats
                        """),
                        {"source_name": source_name},
                    ).first()

                elif source_name == "PubTator":
                    # Count publications per gene (with score filtering)
                    join_for_dist, filter_for_dist = get_gene_evidence_filter_join()
                    distribution_data = db.execute(
                        text(f"""
                            SELECT
                                pub_count,
                                COUNT(*) as gene_count
                            FROM (
                                SELECT
                                    gene_evidence.gene_id,
                                    jsonb_array_length(COALESCE(gene_evidence.evidence_data->'pmids', '[]'::jsonb)) as pub_count
                                FROM gene_evidence
                                {join_for_dist}
                                WHERE {filter_for_dist} AND gene_evidence.source_name = :source_name
                            ) pub_counts
                            GROUP BY pub_count
                            ORDER BY pub_count
                        """),
                        {"source_name": source_name},
                    ).fetchall()

                    join_for_meta, filter_for_meta = get_gene_evidence_filter_join()
                    metadata = db.execute(
                        text(f"""
                            WITH pub_stats AS (
                                SELECT
                                    jsonb_array_length(COALESCE(evidence_data->'pmids', '[]'::jsonb)) as pub_count
                                FROM gene_evidence
                                {join_for_meta}
                                WHERE {filter_for_meta} AND source_name = :source_name
                            )
                            SELECT
                                COUNT(DISTINCT pub_count) as total_unique_counts,
                                MAX(pub_count) as max_publications_per_gene,
                                AVG(pub_count::float) as avg_publications_per_gene
                            FROM pub_stats
                        """),
                        {"source_name": source_name},
                    ).first()

                elif source_name == "DiagnosticPanels":
                    # Count diagnostic panels per gene (with score filtering)
                    join_for_dist, filter_for_dist = get_gene_evidence_filter_join()
                    distribution_data = db.execute(
                        text(f"""
                            SELECT
                                panel_count,
                                COUNT(*) as gene_count
                            FROM (
                                SELECT
                                    gene_evidence.gene_id,
                                    jsonb_array_length(COALESCE(gene_evidence.evidence_data->'panels', '[]'::jsonb)) as panel_count
                                FROM gene_evidence
                                {join_for_dist}
                                WHERE {filter_for_dist} AND gene_evidence.source_name = :source_name
                            ) panel_counts
                            GROUP BY panel_count
                            ORDER BY panel_count
                        """),
                        {"source_name": source_name},
                    ).fetchall()

                    join_for_meta, filter_for_meta = get_gene_evidence_filter_join()
                    metadata = db.execute(
                        text(f"""
                            WITH panel_stats AS (
                                SELECT
                                    jsonb_array_length(COALESCE(evidence_data->'panels', '[]'::jsonb)) as panel_count
                                FROM gene_evidence
                                {join_for_meta}
                                WHERE {filter_for_meta} AND source_name = :source_name
                            )
                            SELECT
                                COUNT(DISTINCT panel_count) as total_unique_counts,
                                MAX(panel_count) as max_panels_per_gene,
                                AVG(panel_count::float) as avg_panels_per_gene
                            FROM panel_stats
                        """),
                        {"source_name": source_name},
                    ).first()

                else:
                    # For sources like ClinGen, GenCC, HPO - count evidence items per gene (with score filtering)
                    join_for_dist, filter_for_dist = get_gene_evidence_filter_join()
                    distribution_data = db.execute(
                        text(f"""
                            SELECT
                                1 as evidence_count,
                                COUNT(*) as gene_count
                            FROM gene_evidence
                            {join_for_dist}
                            WHERE {filter_for_dist} AND gene_evidence.source_name = :source_name
                            GROUP BY 1
                        """),
                        {"source_name": source_name},
                    ).fetchall()

                    join_for_meta, filter_for_meta = get_gene_evidence_filter_join()
                    metadata = db.execute(
                        text(f"""
                            SELECT
                                COUNT(*) as total_genes,
                                1 as max_evidence_per_gene,
                                1.0 as avg_evidence_per_gene
                            FROM gene_evidence
                            {join_for_meta}
                            WHERE {filter_for_meta} AND gene_evidence.source_name = :source_name
                        """),
                        {"source_name": source_name},
                    ).first()

                # Convert to list of dictionaries
                distribution = [
                    {"source_count": row[0], "gene_count": row[1]} for row in distribution_data
                ]

                # Build metadata
                meta_dict = {}
                if metadata:
                    if source_name == "PanelApp":
                        meta_dict = {
                            "total_unique_panel_counts": metadata[0] or 0,
                            "max_panels_per_gene": metadata[1] or 0,
                            "avg_panels_per_gene": round(metadata[2] or 0, 2),
                        }
                    elif source_name == "PubTator":
                        meta_dict = {
                            "total_unique_publication_counts": metadata[0] or 0,
                            "max_publications_per_gene": metadata[1] or 0,
                            "avg_publications_per_gene": round(metadata[2] or 0, 2),
                        }
                    elif source_name == "DiagnosticPanels":
                        meta_dict = {
                            "total_unique_panel_counts": metadata[0] or 0,
                            "max_panels_per_gene": metadata[1] or 0,
                            "avg_panels_per_gene": round(metadata[2] or 0, 2),
                        }
                    else:
                        meta_dict = {
                            "total_genes": metadata[0] or 0,
                            "max_evidence_per_gene": metadata[1] or 0,
                            "avg_evidence_per_gene": round(metadata[2] or 0, 2),
                        }

                source_distributions[source_name] = {
                    "distribution": distribution,
                    "metadata": meta_dict,
                }

            return source_distributions

        except Exception as e:
            logger.sync_error("Error calculating source distributions", error=e)
            raise

    def get_evidence_composition(
        self,
        db: Session,
        min_tier: str | None = None,
        hide_zero_scores: bool = True
    ) -> dict[str, Any]:
        """
        Analyze evidence quality and composition across sources

        Args:
            db: Database session
            min_tier: Optional minimum evidence tier for filtering
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
                    "order": 1
                },
                "multi_source_support": {
                    "label": "Multi-Source Support",
                    "color": "#2196F3",  # info (blue)
                    "order": 2
                },
                "established_support": {
                    "label": "Established Support",
                    "color": "#1976D2",  # primary (darker blue)
                    "order": 3
                },
                "preliminary_evidence": {
                    "label": "Preliminary Evidence",
                    "color": "#FFC107",  # warning (amber)
                    "order": 4
                },
                "minimal_evidence": {
                    "label": "Minimal Evidence",
                    "color": "#9E9E9E",  # grey
                    "order": 5
                },
                "no_evidence": {
                    "label": "Insufficient Evidence",
                    "color": "#BDBDBD",  # lighter grey
                    "order": 6
                }
            }

            # Build WHERE clause - filter out zero scores by default (matches /genes endpoint behavior)
            where_clauses = []
            if hide_zero_scores:
                where_clauses.append("gs.percentage_score > 0")

            # Add tier filter if specified
            if min_tier:
                tier_order = tier_config_map.get(min_tier, {}).get("order", 999)
                valid_tiers = [tier for tier, config in tier_config_map.items() if config["order"] >= tier_order]
                tier_list_str = ", ".join(f"'{tier}'" for tier in valid_tiers)
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
                if row[0] in tier_config_map  # Now includes 'no_evidence' when hide_zero_scores=False
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
                    "total_genes": sum(
                        item["gene_count"] for item in evidence_tier_distribution
                    ),
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
            # FIXED: Remove undefined source_name variable from error logging
            logger.sync_error(
                "Error analyzing evidence composition", error=e, min_tier=min_tier
            )
            raise


# Create singleton instance
statistics_crud = CRUDStatistics()
