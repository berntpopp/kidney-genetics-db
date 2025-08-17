"""
Unified HPO (Human Phenotype Ontology) data source implementation.

This module replaces the previous HPO implementations with a single,
async-first implementation using the unified data source architecture.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.datasource_config import get_source_cache_ttl, get_source_parameter
from app.pipeline.sources.unified.base import UnifiedDataSource

logger = logging.getLogger(__name__)


class HPOUnifiedSource(UnifiedDataSource):
    """
    Unified HPO client with intelligent caching and async processing.
    
    Features:
    - Async-first design with batch processing
    - Kidney phenotype hierarchy traversal
    - Gene-disease associations via HPO API
    - Inheritance pattern extraction
    - OMIM disease information integration
    """

    @property
    def source_name(self) -> str:
        return "HPO"

    @property
    def namespace(self) -> str:
        return "hpo"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | None = None,
        **kwargs
    ):
        """Initialize HPO client with phenotype ontology capabilities."""
        super().__init__(cache_service, http_client, db_session, **kwargs)

        # HPO configuration from centralized config
        self.api_url = get_source_parameter("HPO", "api_url", "https://ontology.jax.org/api")
        self.browser_url = get_source_parameter("HPO", "browser_url", "https://hpo.jax.org")

        # Root kidney phenotype term
        self.kidney_root_term = get_source_parameter("HPO", "kidney_root_term", "HP:0010935")

        # Additional kidney-related root terms
        self.kidney_terms = get_source_parameter("HPO", "kidney_terms", [
            "HP:0010935",  # Abnormality of upper urinary tract
            "HP:0000077",  # Abnormality of the kidney
            "HP:0012210",  # Abnormal renal morphology
            "HP:0000079",  # Abnormality of the urinary system
        ])

        # Processing settings
        self.max_depth = get_source_parameter("HPO", "max_depth", 10)
        self.batch_size = get_source_parameter("HPO", "batch_size", 5)
        self.request_delay = get_source_parameter("HPO", "request_delay", 0.2)

        logger.info(f"HPOUnifiedSource initialized with root term: {self.kidney_root_term}")

    def _get_default_ttl(self) -> int:
        """Get default TTL for HPO data."""
        return get_source_cache_ttl("HPO")

    async def fetch_raw_data(self) -> dict[str, Any]:
        """
        Fetch kidney-related phenotypes and associated genes from HPO.
        
        Returns:
            Dictionary with phenotypes and gene associations
        """
        logger.info("📥 Fetching HPO data for kidney phenotypes...")

        # Use the modular HPO pipeline
        from app.core.hpo.pipeline import HPOPipeline

        pipeline = HPOPipeline(self.cache_service, self.http_client)

        # Process kidney phenotypes and get gene associations
        gene_evidence_map = await pipeline.process_kidney_phenotypes(None)

        return {
            "gene_evidence": gene_evidence_map,
            "root_term": self.kidney_root_term,
            "fetch_date": datetime.now(timezone.utc).isoformat()
        }

    async def _fetch_phenotype_hierarchy(self, root_term: str) -> list[str]:
        """
        Fetch all descendant terms of a phenotype.
        
        Args:
            root_term: HPO term ID (e.g., HP:0010935)
            
        Returns:
            List of HPO term IDs including root and descendants
        """
        async def _fetch_descendants():
            """Internal function to fetch term hierarchy."""
            url = f"{self.api_url}/hpo/terms/{root_term}"

            try:
                response = await self.http_client.get(url, timeout=30)

                if response.status_code == 200:
                    data = response.json()

                    # Extract descendant terms
                    descendants = [root_term]

                    # Get children recursively
                    children = data.get("children", [])
                    for child in children:
                        child_id = child.get("ontologyId")
                        if child_id:
                            descendants.append(child_id)
                            # Recursively get descendants
                            child_descendants = await self._fetch_phenotype_hierarchy(child_id)
                            descendants.extend(child_descendants)

                    return list(set(descendants))
                else:
                    logger.error(f"Failed to fetch HPO term {root_term}: HTTP {response.status_code}")
                    return [root_term]

            except Exception as e:
                logger.error(f"Error fetching HPO hierarchy for {root_term}: {e}")
                return [root_term]

        # Use unified caching
        cache_key = f"hierarchy:{root_term}"
        terms = await self.fetch_with_cache(
            cache_key=cache_key,
            fetch_func=_fetch_descendants,
            ttl=self.cache_ttl * 7  # Cache for a week
        )

        return terms or [root_term]

    async def _fetch_gene_associations(self, hpo_term: str) -> list[dict[str, Any]]:
        """
        Fetch gene associations for an HPO term.
        
        Args:
            hpo_term: HPO term ID
            
        Returns:
            List of gene associations
        """
        async def _fetch_associations():
            """Internal function to fetch associations."""
            url = f"{self.api_url}/hpo/terms/{hpo_term}/genes"

            try:
                response = await self.http_client.get(url, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    return data.get("associations", [])
                else:
                    logger.debug(f"No gene associations for {hpo_term}: HTTP {response.status_code}")
                    return []

            except Exception as e:
                logger.error(f"Error fetching associations for {hpo_term}: {e}")
                return []

        # Use unified caching
        cache_key = f"associations:{hpo_term}"
        associations = await self.fetch_with_cache(
            cache_key=cache_key,
            fetch_func=_fetch_associations,
            ttl=self.cache_ttl
        )

        return associations or []

    async def process_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process HPO data into structured gene information.
        
        Args:
            raw_data: Raw data with gene evidence
            
        Returns:
            Dictionary mapping gene symbols to aggregated data
        """
        if not raw_data or "gene_evidence" not in raw_data:
            return {}

        gene_evidence_map = raw_data["gene_evidence"]
        gene_data_map = {}

        logger.info(f"🔄 Processing HPO data for {len(gene_evidence_map)} genes...")

        for gene_symbol, evidence_data in gene_evidence_map.items():
            # Clean and validate gene symbol
            if not gene_symbol or len(gene_symbol) < 2:
                continue

            # Structure the evidence data
            gene_data_map[gene_symbol] = {
                "hpo_terms": evidence_data.get("hpo_terms", []),
                "diseases": evidence_data.get("diseases", []),
                "phenotypes": evidence_data.get("phenotypes", []),
                "inheritance_patterns": evidence_data.get("inheritance_patterns", set()),
                "evidence_score": self._calculate_hpo_score(evidence_data),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            # Convert sets to lists for JSON serialization
            if isinstance(gene_data_map[gene_symbol]["inheritance_patterns"], set):
                gene_data_map[gene_symbol]["inheritance_patterns"] = list(
                    gene_data_map[gene_symbol]["inheritance_patterns"]
                )

        logger.info(
            f"🎯 HPO processing complete: "
            f"{len(gene_data_map)} genes with kidney phenotypes"
        )

        return gene_data_map

    def _calculate_hpo_score(self, evidence_data: dict[str, Any]) -> float:
        """
        Calculate evidence score based on HPO data.
        
        Args:
            evidence_data: Evidence data for a gene
            
        Returns:
            Calculated score (0-100)
        """
        score = 0.0

        # Score based on number of HPO terms
        hpo_count = len(evidence_data.get("hpo_terms", []))
        score += min(hpo_count * 5, 30)  # Max 30 points for HPO terms

        # Score based on number of diseases
        disease_count = len(evidence_data.get("diseases", []))
        score += min(disease_count * 10, 40)  # Max 40 points for diseases

        # Score based on inheritance patterns
        inheritance_patterns = evidence_data.get("inheritance_patterns", set())
        if inheritance_patterns:
            score += 20  # 20 points for having inheritance info

        # Bonus for specific high-confidence patterns
        if "Autosomal dominant" in inheritance_patterns:
            score += 5
        if "Autosomal recessive" in inheritance_patterns:
            score += 5

        return min(score, 100.0)

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        """
        Check if a gene record is kidney-related.
        
        Always returns True as we pre-filter with kidney phenotypes.
        """
        return True

    def _get_source_detail(self, evidence_data: dict[str, Any]) -> str:
        """
        Generate source detail string for evidence.
        
        Args:
            evidence_data: Evidence data
            
        Returns:
            Source detail string
        """
        hpo_count = len(evidence_data.get("hpo_terms", []))
        disease_count = len(evidence_data.get("diseases", []))

        return f"HPO: {hpo_count} phenotypes, {disease_count} diseases"

    async def fetch_disease_info(self, disease_id: str) -> dict[str, Any] | None:
        """
        Fetch detailed disease information.
        
        Args:
            disease_id: Disease identifier (e.g., OMIM:123456)
            
        Returns:
            Disease information or None
        """
        async def _fetch_disease():
            """Internal function to fetch disease data."""
            url = f"{self.api_url}/diseases/{disease_id}"

            try:
                response = await self.http_client.get(url, timeout=30)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.debug(f"Disease {disease_id} not found: HTTP {response.status_code}")
                    return None

            except Exception as e:
                logger.error(f"Error fetching disease {disease_id}: {e}")
                return None

        # Use unified caching
        cache_key = f"disease:{disease_id}"
        disease_info = await self.fetch_with_cache(
            cache_key=cache_key,
            fetch_func=_fetch_disease,
            ttl=self.cache_ttl * 7  # Cache for a week
        )

        return disease_info
