"""
Source-specific distribution handlers.
Follows Open/Closed Principle - add new sources without modifying existing code.
"""

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)


class DistributionHandler(ABC):
    """Base handler for source distribution queries"""

    @abstractmethod
    def get_distribution(
        self,
        db: Session,
        join_clause: str,
        filter_clause: str
    ) -> tuple[list[Any], dict[str, Any]]:
        """
        Get distribution data and metadata for a source.

        Returns:
            Tuple of (distribution_data, metadata_dict)
        """
        pass


class DiagnosticPanelsHandler(DistributionHandler):
    """Provider distribution for DiagnosticPanels"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating provider distribution", source="DiagnosticPanels")

        # Extract providers from JSONB providers array
        distribution_data = db.execute(
            text(f"""
                WITH provider_counts AS (
                    SELECT
                        gene_evidence.gene_id,
                        jsonb_array_elements_text(evidence_data->'providers') as provider
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause} AND source_name = 'DiagnosticPanels'
                )
                SELECT
                    provider,
                    COUNT(DISTINCT provider_counts.gene_id) as gene_count
                FROM provider_counts
                WHERE provider IS NOT NULL
                GROUP BY provider
                ORDER BY gene_count DESC
            """)
        ).fetchall()

        total_providers = len(distribution_data)
        total_genes = sum(row[1] for row in distribution_data)

        metadata = {
            "total_providers": total_providers,
            "total_genes": total_genes,
            "visualization_type": "provider_bar_chart",
        }

        logger.sync_info(
            "Provider distribution calculated",
            source="DiagnosticPanels",
            providers=total_providers,
            genes=total_genes
        )

        return distribution_data, metadata


class ClinGenHandler(DistributionHandler):
    """Classification distribution for ClinGen"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating classification distribution", source="ClinGen")

        # ClinGen stores classifications as array of strings
        distribution_data = db.execute(
            text(f"""
                WITH classification_data AS (
                    SELECT
                        gene_evidence.gene_id,
                        jsonb_array_elements_text(evidence_data->'classifications') as classification
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause} AND source_name = 'ClinGen'
                )
                SELECT
                    classification,
                    COUNT(DISTINCT classification_data.gene_id) as gene_count
                FROM classification_data
                WHERE classification IS NOT NULL
                GROUP BY classification
                ORDER BY
                    CASE classification
                        WHEN 'Definitive' THEN 1
                        WHEN 'Strong' THEN 2
                        WHEN 'Moderate' THEN 3
                        WHEN 'Limited' THEN 4
                        WHEN 'Disputed' THEN 5
                        WHEN 'Refuted' THEN 6
                        ELSE 7
                    END
            """)
        ).fetchall()

        total_genes = sum(row[1] for row in distribution_data)

        metadata = {
            "total_classifications": len(distribution_data),
            "total_genes": total_genes,
            "visualization_type": "classification_donut",
        }

        logger.sync_info(
            "Classification distribution calculated",
            source="ClinGen",
            classifications=len(distribution_data),
            genes=total_genes
        )

        return distribution_data, metadata


class GenCCHandler(DistributionHandler):
    """Classification distribution for GenCC"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating classification distribution", source="GenCC")

        # GenCC stores classifications in submissions array
        distribution_data = db.execute(
            text(f"""
                WITH gencc_classifications AS (
                    SELECT
                        gene_evidence.gene_id,
                        submission->>'classification' as classification
                    FROM gene_evidence
                    {join_clause},
                    jsonb_array_elements(evidence_data->'submissions') as submission
                    WHERE {filter_clause}
                        AND source_name = 'GenCC'
                )
                SELECT
                    classification,
                    COUNT(DISTINCT gene_id) as gene_count
                FROM gencc_classifications
                WHERE classification IS NOT NULL
                GROUP BY classification
                ORDER BY
                    CASE classification
                        WHEN 'Definitive' THEN 1
                        WHEN 'Strong' THEN 2
                        WHEN 'Moderate' THEN 3
                        WHEN 'Limited' THEN 4
                        WHEN 'Supportive' THEN 5
                        WHEN 'Disputed Evidence' THEN 6
                        WHEN 'No Known Disease Relationship' THEN 7
                        ELSE 8
                    END
            """)
        ).fetchall()

        total_genes = sum(row[1] for row in distribution_data)

        metadata = {
            "total_classifications": len(distribution_data),
            "total_genes": total_genes,
            "visualization_type": "classification_donut",
        }

        logger.sync_info(
            "Classification distribution calculated",
            source="GenCC",
            classifications=len(distribution_data),
            genes=total_genes
        )

        return distribution_data, metadata


class HPOHandler(DistributionHandler):
    """Phenotype count distribution for HPO"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating phenotype distribution", source="HPO")

        distribution_data = db.execute(
            text(f"""
                WITH phenotype_counts AS (
                    SELECT
                        gene_evidence.gene_id,
                        jsonb_array_length(COALESCE(evidence_data->'phenotypes', '[]'::jsonb)) as phenotype_count
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause} AND source_name = 'HPO'
                )
                SELECT
                    CASE
                        WHEN phenotype_count = 0 THEN 'No phenotypes'
                        WHEN phenotype_count BETWEEN 1 AND 5 THEN '1-5'
                        WHEN phenotype_count BETWEEN 6 AND 10 THEN '6-10'
                        WHEN phenotype_count BETWEEN 11 AND 20 THEN '11-20'
                        WHEN phenotype_count BETWEEN 21 AND 50 THEN '21-50'
                        ELSE '50+'
                    END as phenotype_range,
                    COUNT(*) as gene_count
                FROM phenotype_counts
                GROUP BY 1
                ORDER BY MIN(phenotype_count)
            """)
        ).fetchall()

        total_genes = sum(row[1] for row in distribution_data)

        metadata = {
            "total_ranges": len(distribution_data),
            "total_genes": total_genes,
            "visualization_type": "phenotype_histogram",
        }

        logger.sync_info(
            "Phenotype distribution calculated",
            source="HPO",
            ranges=len(distribution_data),
            genes=total_genes
        )

        return distribution_data, metadata


class PanelAppHandler(DistributionHandler):
    """Panel count distribution for PanelApp (existing - keep as-is)"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating panel distribution", source="PanelApp")

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
                    {join_clause}
                    WHERE {filter_clause} AND gene_evidence.source_name = 'PanelApp'
                ) panel_counts
                GROUP BY panel_count
                ORDER BY panel_count
            """)
        ).fetchall()

        metadata = {
            "max_panels": max(row[0] for row in distribution_data) if distribution_data else 0,
            "visualization_type": "panel_histogram",
        }

        return distribution_data, metadata


class PubTatorHandler(DistributionHandler):
    """Publication count distribution for PubTator (existing - keep as-is)"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating publication distribution", source="PubTator")

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
                    {join_clause}
                    WHERE {filter_clause} AND gene_evidence.source_name = 'PubTator'
                ) pub_counts
                GROUP BY pub_count
                ORDER BY pub_count
            """)
        ).fetchall()

        metadata = {
            "max_publications": max(row[0] for row in distribution_data) if distribution_data else 0,
            "visualization_type": "publication_histogram",
        }

        return distribution_data, metadata


class LiteratureHandler(DistributionHandler):
    """Publication count distribution for Literature"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_info("Calculating publication distribution", source="Literature")

        distribution_data = db.execute(
            text(f"""
                SELECT
                    pub_count,
                    COUNT(*) as gene_count
                FROM (
                    SELECT
                        gene_evidence.gene_id,
                        jsonb_array_length(COALESCE(gene_evidence.evidence_data->'publications', '[]'::jsonb)) as pub_count
                    FROM gene_evidence
                    {join_clause}
                    WHERE {filter_clause} AND gene_evidence.source_name = 'Literature'
                ) pub_counts
                GROUP BY pub_count
                ORDER BY pub_count
            """)
        ).fetchall()

        metadata = {
            "max_publications": max(row[0] for row in distribution_data) if distribution_data else 0,
            "visualization_type": "publication_histogram",
        }

        return distribution_data, metadata


class DefaultHandler(DistributionHandler):
    """Default handler for sources without specific logic"""

    def get_distribution(self, db, join_clause, filter_clause):
        logger.sync_warning("Using default handler - no specific distribution logic")
        return [], {"note": "No distribution available"}


class SourceDistributionHandlerFactory:
    """Factory for getting appropriate handler"""

    _handlers = {
        "DiagnosticPanels": DiagnosticPanelsHandler(),
        "ClinGen": ClinGenHandler(),
        "GenCC": GenCCHandler(),
        "HPO": HPOHandler(),
        "Literature": LiteratureHandler(),
        "PanelApp": PanelAppHandler(),
        "PubTator": PubTatorHandler(),
    }

    @classmethod
    def get_handler(cls, source_name: str) -> DistributionHandler:
        """Get handler for source"""
        return cls._handlers.get(source_name, DefaultHandler())
