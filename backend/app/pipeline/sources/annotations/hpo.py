"""
HPO (Human Phenotype Ontology) Annotation Source

Fetches HPO terms and disease associations for genes using the JAX HPO API.
Uses NCBI Gene IDs to retrieve comprehensive phenotype annotations.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.logging import get_logger
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource

logger = get_logger(__name__)


class HPOAnnotationSource(BaseAnnotationSource):
    """
    HPO phenotype annotations for genes.

    Uses the JAX HPO API to fetch:
    1. NCBI Gene ID via gene symbol search
    2. HPO terms and diseases directly associated with the gene
    """

    source_name = "hpo"
    display_name = "Human Phenotype Ontology"
    version = "1.0"

    # Cache configuration
    cache_ttl_days = 7

    # API endpoints
    hpo_api_url = "https://ontology.jax.org/api"

    # Class-level cache for kidney terms (shared across all instances)
    _kidney_terms_cache = None
    _kidney_terms_cache_time = None

    def __init__(self, session):
        """Initialize the HPO annotation source."""
        super().__init__(session)

        # Update source configuration
        if self.source_record:
            self.source_record.update_frequency = "weekly"
            self.source_record.description = "Human phenotype terms and disease associations for genes"
            self.source_record.base_url = self.hpo_api_url
            self.session.commit()

    async def search_gene_for_ncbi_id(self, gene_symbol: str) -> str | None:
        """
        Search for a gene symbol to get its NCBI Gene ID.

        Args:
            gene_symbol: Human gene symbol (e.g., "ARID1B")

        Returns:
            NCBI Gene ID (e.g., "2904") or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                # Search for the gene using the gene search endpoint
                search_url = f"{self.hpo_api_url}/network/search/gene"
                params = {
                    "q": gene_symbol,
                    "limit": -1  # Get all results
                }

                response = await client.get(search_url, params=params, timeout=30.0)

                if response.status_code != 200:
                    logger.sync_warning(
                        f"Gene search failed for {gene_symbol}",
                        status_code=response.status_code
                    )
                    return None

                # Parse JSON response
                data = response.json()

                # The response has a "results" array
                results = data.get("results", [])

                # Find exact match first
                for gene_result in results:
                    if gene_result.get("name") == gene_symbol:
                        # Extract NCBI Gene ID from the id field
                        # Format is "NCBIGene:12345"
                        gene_id = gene_result.get("id", "")
                        if gene_id.startswith("NCBIGene:"):
                            ncbi_id = gene_id.replace("NCBIGene:", "")
                            logger.sync_info(
                                f"Found NCBI Gene ID for {gene_symbol}",
                                ncbi_id=ncbi_id
                            )
                            return ncbi_id

                # If no exact match, try case-insensitive match
                gene_symbol_upper = gene_symbol.upper()
                for gene_result in results:
                    if gene_result.get("name", "").upper() == gene_symbol_upper:
                        gene_id = gene_result.get("id", "")
                        if gene_id.startswith("NCBIGene:"):
                            ncbi_id = gene_id.replace("NCBIGene:", "")
                            logger.sync_info(
                                f"Found NCBI Gene ID (case-insensitive) for {gene_symbol}",
                                ncbi_id=ncbi_id
                            )
                            return ncbi_id

                logger.sync_warning(f"No NCBI Gene ID found for {gene_symbol}")
                return None

        except Exception as e:
            logger.sync_error(
                "Error searching for NCBI Gene ID",
                gene_symbol=gene_symbol,
                error=str(e)
            )
            return None

    async def get_gene_annotations(self, ncbi_gene_id: str) -> dict[str, Any] | None:
        """
        Get HPO annotations for a gene using its NCBI Gene ID.

        Args:
            ncbi_gene_id: NCBI Gene ID (e.g., "2904")

        Returns:
            Dictionary with phenotypes and diseases or None if error
        """
        try:
            async with httpx.AsyncClient() as client:
                # Get annotations using the NCBI Gene ID
                annotation_url = f"{self.hpo_api_url}/network/annotation/NCBIGene:{ncbi_gene_id}"

                response = await client.get(annotation_url, timeout=30.0)

                if response.status_code == 404:
                    logger.sync_warning(
                        f"No HPO annotations found for NCBIGene:{ncbi_gene_id}"
                    )
                    return {
                        "phenotypes": [],
                        "diseases": []
                    }

                if response.status_code != 200:
                    logger.sync_warning(
                        "Failed to get HPO annotations",
                        ncbi_gene_id=ncbi_gene_id,
                        status_code=response.status_code
                    )
                    return None

                data = response.json()

                # Extract phenotypes (HPO terms)
                phenotypes = []
                for phenotype in data.get("phenotypes", []):
                    phenotypes.append({
                        "id": phenotype.get("id"),
                        "name": phenotype.get("name"),
                        "definition": phenotype.get("definition")
                    })

                # Extract diseases
                diseases = []
                for disease in data.get("diseases", []):
                    diseases.append({
                        "id": disease.get("id"),
                        "name": disease.get("name"),
                        "dbId": disease.get("dbId"),
                        "db": disease.get("db")
                    })

                return {
                    "phenotypes": phenotypes,
                    "diseases": diseases
                }

        except Exception as e:
            logger.sync_error(
                "Error fetching HPO annotations",
                ncbi_gene_id=ncbi_gene_id,
                error=str(e)
            )
            return None

    async def get_kidney_term_descendants(self) -> set[str]:
        """
        Get cached set of kidney HPO term descendants.
        Reuses the existing HPO pipeline logic and configuration for DRY principle.
        """
        import time

        from app.core.datasource_config import get_source_parameter

        # Check if we have a recent cache (cache for 24 hours)
        if (self._kidney_terms_cache is not None and
            self._kidney_terms_cache_time is not None and
            time.time() - self._kidney_terms_cache_time < 86400):
            return self._kidney_terms_cache

        # Use the existing HPO pipeline to get kidney terms
        from app.core.hpo.pipeline import HPOPipeline

        pipeline = HPOPipeline()

        # Get ALL configured kidney root terms from configuration
        kidney_root_terms = get_source_parameter("HPO", "kidney_terms", [])

        # Collect all descendants from ALL configured kidney root terms
        kidney_term_ids = set()
        for root_term in kidney_root_terms:
            try:
                descendants = await pipeline.terms.get_descendants(
                    root_term,
                    max_depth=pipeline.max_depth,
                    include_self=True
                )
                kidney_term_ids.update(descendants)
            except Exception as e:
                logger.sync_warning(f"Failed to get descendants for {root_term}: {e}")

        # Cache for reuse
        self._kidney_terms_cache = kidney_term_ids
        self._kidney_terms_cache_time = time.time()

        logger.sync_info(f"Loaded {len(kidney_term_ids)} kidney HPO term descendants")

        return kidney_term_ids

    async def filter_kidney_phenotypes(self, phenotypes: list[dict]) -> list[dict]:
        """
        Filter for kidney-related phenotypes.
        Simple and clean - just checks if phenotype ID is in kidney term descendants.

        Args:
            phenotypes: List of HPO phenotype dictionaries

        Returns:
            List of kidney-related phenotypes
        """
        # Get the cached kidney term descendants
        kidney_term_ids = await self.get_kidney_term_descendants()

        # Simple filter - phenotype is kidney-related if its ID is in the descendant set
        return [
            phenotype for phenotype in phenotypes
            if phenotype.get("id") in kidney_term_ids
        ]

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch HPO annotation for a gene.

        Args:
            gene: Gene object to fetch annotations for

        Returns:
            Dictionary with annotation data or None if not found
        """
        try:
            # Step 1: Get NCBI Gene ID for the gene symbol
            ncbi_gene_id = await self.search_gene_for_ncbi_id(gene.approved_symbol)

            if not ncbi_gene_id:
                # No NCBI Gene ID found, return empty annotation
                return {
                    "gene_symbol": gene.approved_symbol,
                    "ncbi_gene_id": None,
                    "has_hpo_data": False,
                    "phenotypes": [],
                    "phenotype_count": 0,
                    "diseases": [],
                    "disease_count": 0,
                    "kidney_phenotypes": [],
                    "kidney_phenotype_count": 0,
                    "has_kidney_phenotype": False,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }

            # Step 2: Get HPO annotations using NCBI Gene ID
            annotations = await self.get_gene_annotations(ncbi_gene_id)

            if annotations is None:
                # Error occurred
                return None

            phenotypes = annotations.get("phenotypes", [])
            diseases = annotations.get("diseases", [])

            # Step 3: Filter for kidney-related phenotypes
            kidney_phenotypes = await self.filter_kidney_phenotypes(phenotypes)

            return {
                "gene_symbol": gene.approved_symbol,
                "ncbi_gene_id": ncbi_gene_id,
                "has_hpo_data": len(phenotypes) > 0 or len(diseases) > 0,
                "phenotypes": phenotypes,
                "phenotype_count": len(phenotypes),
                "diseases": diseases,
                "disease_count": len(diseases),
                "kidney_phenotypes": kidney_phenotypes,
                "kidney_phenotype_count": len(kidney_phenotypes),
                "has_kidney_phenotype": len(kidney_phenotypes) > 0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.sync_error(
                f"Error fetching HPO annotation for {gene.approved_symbol}: {str(e)}"
            )
            return None

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Batch fetch annotations for multiple genes.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene_id to annotation data
        """
        results = {}

        # Process genes in parallel (limit concurrency)
        batch_size = 10  # HPO API can handle moderate concurrency

        for i in range(0, len(genes), batch_size):
            batch = genes[i:i + batch_size]

            # Create tasks for this batch
            tasks = [self.fetch_annotation(gene) for gene in batch]

            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for gene, result in zip(batch, batch_results, strict=False):
                if isinstance(result, Exception):
                    logger.sync_error(f"Failed to fetch HPO for {gene.approved_symbol}: {result}")
                    results[gene.id] = None
                else:
                    results[gene.id] = result

            # Small delay between batches to be respectful to the API
            if i + batch_size < len(genes):
                await asyncio.sleep(0.2)

        return results

    def validate_annotation(self, annotation_data: dict[str, Any]) -> bool:
        """Validate that annotation data has required fields"""
        required_fields = [
            "gene_symbol",
            "ncbi_gene_id",
            "has_hpo_data",
            "phenotypes",
            "phenotype_count",
            "diseases",
            "disease_count",
            "kidney_phenotypes",
            "kidney_phenotype_count",
            "has_kidney_phenotype"
        ]
        return all(field in annotation_data for field in required_fields)

    def get_summary_fields(self) -> dict[str, str]:
        """
        Get fields to include in materialized view.
        Returns mapping of JSONB paths to column names.
        """
        return {
            "hpo_ncbi_gene_id": "annotations->>'ncbi_gene_id'",
            "has_hpo_phenotypes": "(annotations->>'has_hpo_data')::BOOLEAN",
            "hpo_phenotype_count": "(annotations->>'phenotype_count')::INTEGER",
            "hpo_disease_count": "(annotations->>'disease_count')::INTEGER",
            "has_kidney_phenotype": "(annotations->>'has_kidney_phenotype')::BOOLEAN",
            "kidney_phenotype_count": "(annotations->>'kidney_phenotype_count')::INTEGER"
        }

