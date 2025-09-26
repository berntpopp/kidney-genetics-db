"""
Unified HPO (Human Phenotype Ontology) data source implementation.

This module replaces the previous HPO implementations with a single,
async-first implementation using the unified data source architecture.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.datasource_config import get_source_cache_ttl, get_source_parameter
from app.core.logging import get_logger
from app.pipeline.sources.unified.base import UnifiedDataSource

if TYPE_CHECKING:
    from app.core.progress_tracker import ProgressTracker

logger = get_logger(__name__)


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
        **kwargs,
    ):
        """Initialize HPO client with phenotype ontology capabilities."""
        super().__init__(cache_service, http_client, db_session, **kwargs)

        # HPO configuration from centralized config
        self.api_url = get_source_parameter("HPO", "api_url", "https://ontology.jax.org/api")
        self.browser_url = get_source_parameter("HPO", "browser_url", "https://hpo.jax.org")

        # Root kidney phenotype term
        self.kidney_root_term = get_source_parameter("HPO", "kidney_root_term", "HP:0010935")

        # Additional kidney-related root terms
        self.kidney_terms = get_source_parameter(
            "HPO",
            "kidney_terms",
            [
                "HP:0010935",  # Abnormality of upper urinary tract
                "HP:0000077",  # Abnormality of the kidney
                "HP:0012210",  # Abnormal renal morphology
                "HP:0000079",  # Abnormality of the urinary system
            ],
        )

        # Processing settings
        self.max_depth = get_source_parameter("HPO", "max_depth", 10)
        self.batch_size = get_source_parameter("HPO", "batch_size", 5)
        self.request_delay = get_source_parameter("HPO", "request_delay", 0.2)

        logger.sync_info("HPOUnifiedSource initialized", root_term=self.kidney_root_term)

    def _get_default_ttl(self) -> int:
        """Get default TTL for HPO data."""
        return get_source_cache_ttl("HPO")

    async def fetch_raw_data(self, tracker: "ProgressTracker" = None) -> dict[str, Any]:
        """
        Fetch kidney-related phenotypes and associated genes from HPO.

        Returns:
            Dictionary with phenotypes and gene associations
        """
        logger.sync_info("Fetching HPO data for kidney phenotypes")

        # Use the modular HPO pipeline
        from app.core.hpo.pipeline import HPOPipeline

        pipeline = HPOPipeline(self.cache_service, self.http_client)

        # Process kidney phenotypes and get gene associations
        gene_evidence_map = await pipeline.process_kidney_phenotypes(None)

        return {
            "gene_evidence": gene_evidence_map,
            "root_term": self.kidney_root_term,
            "fetch_date": datetime.now(timezone.utc).isoformat(),
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
                    logger.sync_error(
                        "Failed to fetch HPO term",
                        root_term=root_term,
                        status_code=response.status_code,
                    )
                    return [root_term]

            except Exception as e:
                logger.sync_error("Error fetching HPO hierarchy", root_term=root_term, error=str(e))
                return [root_term]

        # Use unified caching
        cache_key = f"hierarchy:{root_term}"
        terms = await self.fetch_with_cache(
            cache_key=cache_key,
            fetch_func=_fetch_descendants,
            ttl=self.cache_ttl * 7,  # Cache for a week
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
                    logger.sync_debug(
                        "No gene associations for HPO term",
                        hpo_term=hpo_term,
                        status_code=response.status_code,
                    )
                    return []

            except Exception as e:
                logger.sync_error("Error fetching associations", hpo_term=hpo_term, error=str(e))
                return []

        # Use unified caching
        cache_key = f"associations:{hpo_term}"
        associations = await self.fetch_with_cache(
            cache_key=cache_key, fetch_func=_fetch_associations, ttl=self.cache_ttl
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

        logger.sync_info("Processing HPO data", gene_count=len(gene_evidence_map))

        for gene_symbol, evidence_data in gene_evidence_map.items():
            # Clean and validate gene symbol
            if not gene_symbol or len(gene_symbol) < 2:
                continue

            # Structure the evidence data including syndromic assessment
            hpo_terms = evidence_data.get("hpo_terms", [])
            phenotype_ids = {term["id"] for term in hpo_terms if "id" in term}

            # Calculate syndromic assessment
            syndromic_assessment = await self._assess_syndromic_features(phenotype_ids)

            gene_data_map[gene_symbol] = {
                "hpo_terms": hpo_terms,
                "evidence_score": self._calculate_hpo_score(evidence_data),
                "syndromic_assessment": syndromic_assessment,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        logger.sync_info(
            "HPO processing complete",
            genes_processed=len(gene_data_map),
            description="genes with kidney phenotypes",
        )

        return gene_data_map

    def _calculate_hpo_score(self, evidence_data: dict[str, Any]) -> float:
        """
        Calculate evidence score based on HPO data.

        Note: Score is now based purely on phenotype count since
        disease associations are handled by disease-specific sources.

        Args:
            evidence_data: Evidence data for a gene

        Returns:
            Calculated score (0-100)
        """
        # Score based on number of HPO terms
        # Using a logarithmic scale to avoid oversaturation
        hpo_count = len(evidence_data.get("hpo_terms", []))

        if hpo_count == 0:
            return 0.0
        elif hpo_count <= 5:
            score = hpo_count * 20  # 1-5 terms: 20-100 points
        elif hpo_count <= 10:
            score = 100 + (hpo_count - 5) * 10  # 6-10 terms: 100-150 points
        else:
            # Diminishing returns for many terms
            import math

            score = 150 + math.log(hpo_count - 9) * 20

        # Cap at 100 - actual normalization happens via percentile ranking
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

        return f"HPO: {hpo_count} phenotypes"

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
                    logger.sync_debug(
                        "Disease not found", disease_id=disease_id, status_code=response.status_code
                    )
                    return None

            except Exception as e:
                logger.sync_error("Error fetching disease", disease_id=disease_id, error=str(e))
                return None

        # Use unified caching
        cache_key = f"disease:{disease_id}"
        disease_info = await self.fetch_with_cache(
            cache_key=cache_key,
            fetch_func=_fetch_disease,
            ttl=self.cache_ttl * 7,  # Cache for a week
        )

        return disease_info

    async def _assess_syndromic_features(self, phenotype_ids: set[str]) -> dict:
        """
        Assess if gene has syndromic features based on HPO phenotypes.

        Args:
            phenotype_ids: Set of HPO term IDs for the gene

        Returns:
            Dictionary with syndromic assessment results
        """
        from app.core.datasource_config import get_source_parameter

        # If no phenotypes, return default assessment
        if not phenotype_ids:
            return {
                "is_syndromic": False,
                "category_scores": {},
                "syndromic_score": 0,
                "extra_renal_categories": [],
                "extra_renal_term_counts": {},
            }

        # Get syndromic indicators configuration
        syndromic_indicators = get_source_parameter("HPO", "syndromic_indicators", {})

        # Fetch descendants for each syndromic indicator term
        from app.core.cache_service import get_cache_service
        from app.core.cached_http_client import CachedHttpClient
        from app.core.hpo.pipeline import HPOPipeline

        cache_service = self.cache_service
        http_client = self.http_client

        # Create HPO pipeline if we don't have cache/client
        if not cache_service or not http_client:
            cache_service = get_cache_service(self.db_session) if self.db_session else None
            http_client = CachedHttpClient(cache_service=cache_service) if cache_service else None

        pipeline = HPOPipeline(cache_service=cache_service, http_client=http_client)

        # Get descendants for each category
        syndromic_descendants = {}
        for category, root_term in syndromic_indicators.items():
            descendants = await pipeline.terms.get_descendants(
                root_term, max_depth=pipeline.max_depth, include_self=True
            )
            syndromic_descendants[category] = descendants or set()

        # Calculate matches for each category
        category_matches = {}
        category_scores = {}

        for category, descendant_terms in syndromic_descendants.items():
            matches = phenotype_ids.intersection(descendant_terms)
            if matches:
                category_matches[category] = len(matches)
                # Calculate proportional score for this category
                category_scores[category] = len(matches) / len(phenotype_ids)

        # Calculate overall syndromic score (average of category scores)
        syndromic_score = (
            sum(category_scores.values()) / len(category_scores) if category_scores else 0
        )

        # Determine if syndromic (using 30% threshold as in R implementation)
        is_syndromic = syndromic_score >= 0.3

        return {
            "is_syndromic": is_syndromic,
            "category_scores": category_scores,
            "syndromic_score": syndromic_score,
            "extra_renal_categories": list(category_matches.keys()),
            "extra_renal_term_counts": category_matches,
        }
