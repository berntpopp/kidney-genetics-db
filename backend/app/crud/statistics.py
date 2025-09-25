"""
CRUD operations for statistics and data analysis
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)


class CRUDStatistics:
    """CRUD operations for statistics and data analysis"""

    def get_source_overlaps(
        self, db: Session, selected_sources: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Calculate gene intersections between data sources for UpSet plot visualization

        Args:
            db: Database session
            selected_sources: Optional list of source names to include. If None, uses all sources.

        Returns:
            Dictionary with sets and intersections data for UpSet.js
        """
        try:
            # Build WHERE clause for source filtering if specified
            where_clause = ""
            params = {}

            if selected_sources:
                where_clause = "WHERE source_name = ANY(:selected_sources)"
                params["selected_sources"] = selected_sources

            # Get source names and their gene counts (filtered if specified)
            sources_query = f"""
                SELECT
                    source_name,
                    COUNT(DISTINCT gene_id) as gene_count,
                    array_agg(DISTINCT gene_id ORDER BY gene_id) as gene_ids
                FROM gene_evidence
                {where_clause}
                GROUP BY source_name
                ORDER BY source_name
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
                total_genes_query = """
                    SELECT COUNT(DISTINCT gene_id)
                    FROM gene_evidence
                    WHERE source_name = ANY(:selected_sources)
                """
                total_unique_genes = (
                    db.execute(
                        text(total_genes_query), {"selected_sources": selected_sources}
                    ).scalar()
                    or 0
                )
            else:
                # If no source filter, get all genes with evidence
                total_unique_genes = (
                    db.execute(text("SELECT COUNT(DISTINCT gene_id) FROM gene_evidence")).scalar()
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

    def get_source_distributions(self, db: Session) -> dict[str, Any]:
        """
        Calculate source count distributions for bar chart visualizations

        Returns:
            Dictionary with distribution data for each source
        """
        try:
            # Get all sources
            sources = db.execute(
                text("SELECT DISTINCT source_name FROM gene_evidence ORDER BY source_name")
            ).fetchall()

            source_distributions = {}

            for source_row in sources:
                source_name = source_row[0]

                # For sources with countable elements (panels, publications, etc.)
                if source_name == "PanelApp":
                    # Count panels per gene
                    distribution_data = db.execute(
                        text("""
                            SELECT
                                panel_count,
                                COUNT(*) as gene_count
                            FROM (
                                SELECT
                                    gene_id,
                                    jsonb_array_length(COALESCE(evidence_data->'panels', '[]'::jsonb)) as panel_count
                                FROM gene_evidence
                                WHERE source_name = :source_name
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
                    # Count publications per gene
                    distribution_data = db.execute(
                        text("""
                            SELECT
                                pub_count,
                                COUNT(*) as gene_count
                            FROM (
                                SELECT
                                    gene_id,
                                    jsonb_array_length(COALESCE(evidence_data->'pmids', '[]'::jsonb)) as pub_count
                                FROM gene_evidence
                                WHERE source_name = :source_name
                            ) pub_counts
                            GROUP BY pub_count
                            ORDER BY pub_count
                        """),
                        {"source_name": source_name},
                    ).fetchall()

                    metadata = db.execute(
                        text("""
                            WITH pub_stats AS (
                                SELECT
                                    jsonb_array_length(COALESCE(evidence_data->'pmids', '[]'::jsonb)) as pub_count
                                FROM gene_evidence
                                WHERE source_name = :source_name
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
                    # Count diagnostic panels per gene
                    distribution_data = db.execute(
                        text("""
                            SELECT
                                panel_count,
                                COUNT(*) as gene_count
                            FROM (
                                SELECT
                                    gene_id,
                                    jsonb_array_length(COALESCE(evidence_data->'panels', '[]'::jsonb)) as panel_count
                                FROM gene_evidence
                                WHERE source_name = :source_name
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

                else:
                    # For sources like ClinGen, GenCC, HPO - count evidence items per gene
                    distribution_data = db.execute(
                        text("""
                            SELECT
                                1 as evidence_count,
                                COUNT(*) as gene_count
                            FROM gene_evidence
                            WHERE source_name = :source_name
                            GROUP BY 1
                        """),
                        {"source_name": source_name},
                    ).fetchall()

                    metadata = db.execute(
                        text("""
                            SELECT
                                COUNT(*) as total_genes,
                                1 as max_evidence_per_gene,
                                1.0 as avg_evidence_per_gene
                            FROM gene_evidence
                            WHERE source_name = :source_name
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

    def get_evidence_composition(self, db: Session) -> dict[str, Any]:
        """
        Analyze evidence quality and composition across sources

        Returns:
            Dictionary with evidence composition analysis
        """
        try:
            # Get evidence score distribution from gene_scores view
            score_distribution = db.execute(
                text("""
                    SELECT
                        CASE
                            WHEN percentage_score >= 90 THEN '90-100'
                            WHEN percentage_score >= 70 THEN '70-90'
                            WHEN percentage_score >= 50 THEN '50-70'
                            WHEN percentage_score >= 30 THEN '30-50'
                            ELSE '0-30'
                        END as score_range,
                        COUNT(*) as gene_count
                    FROM gene_scores
                    GROUP BY 1
                    ORDER BY MIN(percentage_score) DESC
                """)
            ).fetchall()

            # Map score ranges to confidence levels
            confidence_mapping = {
                "90-100": "Very High Confidence",
                "70-90": "High Confidence",
                "50-70": "Medium Confidence",
                "30-50": "Low Confidence",
                "0-30": "Very Low Confidence",
            }

            evidence_quality_distribution = [
                {
                    "score_range": row[0],
                    "gene_count": row[1],
                    "label": confidence_mapping.get(row[0], f"{row[0]} Confidence"),
                }
                for row in score_distribution
            ]

            # Calculate source contribution weights (based on active sources)
            source_stats = db.execute(
                text("""
                    SELECT
                        source_name,
                        COUNT(DISTINCT gene_id) as gene_count,
                        COUNT(*) as evidence_count
                    FROM gene_evidence
                    GROUP BY source_name
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
                text("""
                    SELECT
                        source_count,
                        COUNT(*) as gene_count,
                        ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER()), 2) as percentage
                    FROM gene_scores
                    GROUP BY source_count
                    ORDER BY source_count DESC
                """)
            ).fetchall()

            source_coverage_distribution = [
                {"source_count": row[0], "gene_count": row[1], "percentage": row[2]}
                for row in coverage_stats
            ]

            return {
                "evidence_quality_distribution": evidence_quality_distribution,
                "source_contribution_weights": source_contribution_weights,
                "source_coverage_distribution": source_coverage_distribution,
                "summary_statistics": {
                    "total_genes": sum(
                        item["gene_count"] for item in evidence_quality_distribution
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
            logger.sync_error(
                "Error analyzing evidence composition", error=e, source_name=source_name
            )
            raise


# Create singleton instance
statistics_crud = CRUDStatistics()
