"""
Main HPO data processing pipeline for kidney phenotypes.
"""

import logging
from typing import Any

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.config import settings
from app.core.datasource_config import get_source_parameter
from app.core.hpo.annotations import HPOAnnotations
from app.core.hpo.terms import HPOTerms
from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

class HPOPipeline:
    """Main HPO data processing pipeline for kidney/urinary phenotypes."""

    # Default root term for kidney/urinary phenotypes
    KIDNEY_ROOT_TERM = "HP:0010935"  # Abnormality of the upper urinary tract

    def __init__(
        self, cache_service: CacheService | None = None, http_client: CachedHttpClient | None = None
    ):
        """
        Initialize the HPO pipeline.

        Args:
            cache_service: Cache service for data persistence
            http_client: HTTP client with caching capabilities
        """
        self.terms = HPOTerms(cache_service, http_client)
        self.annotations = HPOAnnotations(cache_service, http_client)

        # Configuration
        self.root_term = getattr(settings, "HPO_KIDNEY_ROOT_TERM", self.KIDNEY_ROOT_TERM)
        self.max_depth = getattr(settings, "HPO_MAX_DEPTH", 10)
        self.batch_size = getattr(settings, "HPO_BATCH_SIZE", 10)

    async def process_kidney_phenotypes(
        self, tracker: ProgressTracker | None = None
    ) -> dict[str, Any]:
        """
        Main pipeline for processing kidney/urinary phenotypes.

        Process flow:
        1. Get descendants of HP:0010935 (Abnormality of the upper urinary tract)
        2. Fetch annotations for all descendant terms
        3. Aggregate gene evidence with HPO terms

        Args:
            tracker: Progress tracker for status updates

        Returns:
            Dictionary of gene evidence with structure:
            {
                "gene_symbol": {
                    "entrez_id": int,
                    "hpo_terms": [str]
                }
            }
        """
        if tracker:
            tracker.update(operation="Fetching kidney/urinary HPO terms...")

        # Step 1: Get all relevant HPO terms
        logger.info(f"Getting descendants of {self.root_term}")
        descendants = await self.terms.get_descendants(
            self.root_term, max_depth=self.max_depth, include_self=True
        )

        logger.info(f"Found {len(descendants)} kidney-related HPO terms")

        if not descendants:
            logger.error(f"No descendant terms found for {self.root_term} - API may be unavailable")
            return {}

        if tracker:
            tracker.update(operation=f"Found {len(descendants)} kidney-related HPO terms")

        # Step 2: Batch fetch annotations for all terms
        if tracker:
            tracker.update(operation="Fetching gene-disease associations...")

        annotations_map = await self.annotations.batch_get_annotations(
            list(descendants), batch_size=self.batch_size,
            delay=get_source_parameter("HPO", "request_delay", 0.2)
        )

        logger.info(f"Fetched annotations for {len(annotations_map)} terms")
        if annotations_map:
            first_term = list(annotations_map.keys())[0]
            first_annotation = annotations_map[first_term]
            logger.info(
                f"Example annotation for {first_term}: {len(first_annotation.genes) if first_annotation else 0} genes"
            )

        # Step 3: Aggregate gene evidence
        gene_evidence = {}

        total_terms = len(annotations_map)
        processed = 0

        for hpo_id, term_annotations in annotations_map.items():
            processed += 1

            if tracker:
                tracker.update(
                    current_item=processed,
                    total_items=total_terms,
                    operation=f"Processing {hpo_id}",
                )

            # Process genes from this HPO term
            for gene in term_annotations.genes:
                gene_symbol = gene.name

                # Initialize gene entry if new
                if gene_symbol not in gene_evidence:
                    gene_evidence[gene_symbol] = {
                        "entrez_id": gene.entrez_id,
                        "hpo_terms": set(),
                    }

                # Add HPO term
                gene_evidence[gene_symbol]["hpo_terms"].add(hpo_id)

        # Step 4: Convert sets to lists for JSON serialization
        for gene_data in gene_evidence.values():
            gene_data["hpo_terms"] = sorted(gene_data["hpo_terms"])

        logger.info(f"Processed {len(gene_evidence)} genes with kidney phenotypes")

        if tracker:
            tracker.update(
                operation=f"Completed: {len(gene_evidence)} genes with kidney phenotypes"
            )

        return gene_evidence

    async def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the HPO data processing.

        Returns:
            Dictionary with statistics
        """
        # Get basic stats about the root term
        descendants = await self.terms.get_descendants(self.root_term, max_depth=self.max_depth)

        # Sample annotations for statistics
        sample_annotations = await self.annotations.get_term_annotations(self.root_term)

        stats = {
            "root_term": self.root_term,
            "total_descendant_terms": len(descendants),
            "max_depth": self.max_depth,
            "sample_genes": 0,
            "sample_diseases": 0,
        }

        if sample_annotations:
            stats["sample_genes"] = len(sample_annotations.genes)
            stats["sample_diseases"] = len(sample_annotations.diseases)

        return stats
