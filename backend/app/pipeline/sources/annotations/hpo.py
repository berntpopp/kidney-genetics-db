"""
HPO (Human Phenotype Ontology) Annotation Source

Fetches HPO terms and disease associations for genes using the JAX HPO API.
Uses NCBI Gene IDs to retrieve comprehensive phenotype annotations.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.datasource_config import ANNOTATION_COMMON_CONFIG
from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
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
    cache_ttl_days = 90

    # API endpoints
    hpo_api_url = "https://ontology.jax.org/api"

    # Class-level cache for kidney terms (shared across all instances)
    _kidney_terms_cache = None
    _kidney_terms_cache_time = None

    # Class-level caches for classification terms
    _onset_descendants_cache = None
    _syndromic_descendants_cache = None
    _classification_cache_time = None

    def __init__(self, session: "Session") -> None:
        """Initialize the HPO annotation source."""
        super().__init__(session)

        # Update source configuration
        if self.source_record:
            self.source_record.update_frequency = "weekly"
            self.source_record.description = (
                "Human phenotype terms and disease associations for genes"
            )
            self.source_record.base_url = self.hpo_api_url
            self.session.commit()

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def search_gene_for_ncbi_id(self, gene_symbol: str) -> str | None:
        """
        Search for a gene symbol to get its NCBI Gene ID.

        Args:
            gene_symbol: Human gene symbol (e.g., "ARID1B")

        Returns:
            NCBI Gene ID (e.g., "2904") or None if not found
        """
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            # Search for the gene using the gene search endpoint
            search_url = f"{self.hpo_api_url}/network/search/gene"
            params = {
                "q": gene_symbol,
                "limit": -1,  # Get all results
            }

            response = await client.get(search_url, params=params, timeout=30.0)

            if response.status_code != 200:
                logger.sync_error(
                    f"Gene search failed for {gene_symbol}", status_code=response.status_code
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
                    gene_id = str(gene_result.get("id", ""))
                    if gene_id.startswith("NCBIGene:"):
                        ncbi_id: str = gene_id.replace("NCBIGene:", "")
                        logger.sync_info(f"Found NCBI Gene ID for {gene_symbol}", ncbi_id=ncbi_id)
                        return ncbi_id

            # If no exact match, try case-insensitive match
            gene_symbol_upper = gene_symbol.upper()
            for gene_result in results:
                if str(gene_result.get("name", "")).upper() == gene_symbol_upper:
                    gene_id = str(gene_result.get("id", ""))
                    if gene_id.startswith("NCBIGene:"):
                        ncbi_id = gene_id.replace("NCBIGene:", "")
                        logger.sync_info(
                            f"Found NCBI Gene ID (case-insensitive) for {gene_symbol}",
                            ncbi_id=ncbi_id,
                        )
                        return ncbi_id

            logger.sync_warning(f"No NCBI Gene ID found for {gene_symbol}")
            return None

        except Exception as e:
            logger.sync_error(
                "Error searching for NCBI Gene ID", gene_symbol=gene_symbol, error_detail=str(e)
            )
            return None

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def get_gene_annotations(self, ncbi_gene_id: str) -> dict[str, Any] | None:
        """
        Get HPO annotations for a gene using its NCBI Gene ID.

        Args:
            ncbi_gene_id: NCBI Gene ID (e.g., "2904")

        Returns:
            Dictionary with phenotypes and diseases or None if error
        """
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            # Get annotations using the NCBI Gene ID
            annotation_url = f"{self.hpo_api_url}/network/annotation/NCBIGene:{ncbi_gene_id}"

            response = await client.get(annotation_url, timeout=30.0)

            if response.status_code == 404:
                logger.sync_warning(f"No HPO annotations found for NCBIGene:{ncbi_gene_id}")
                return {"phenotypes": [], "diseases": []}

            if response.status_code != 200:
                logger.sync_warning(
                    "Failed to get HPO annotations",
                    ncbi_gene_id=ncbi_gene_id,
                    status_code=response.status_code,
                )
                return None

            data = response.json()

            # Extract phenotypes (HPO terms)
            phenotypes = []
            for phenotype in data.get("phenotypes", []):
                phenotypes.append(
                    {
                        "id": phenotype.get("id"),
                        "name": phenotype.get("name"),
                        "definition": phenotype.get("definition"),
                    }
                )

            # Extract diseases
            diseases = []
            for disease in data.get("diseases", []):
                diseases.append(
                    {
                        "id": disease.get("id"),
                        "name": disease.get("name"),
                        "dbId": disease.get("dbId"),
                        "db": disease.get("db"),
                    }
                )

            return {"phenotypes": phenotypes, "diseases": diseases}

        except Exception as e:
            logger.sync_error(
                "Error fetching HPO annotations", ncbi_gene_id=ncbi_gene_id, error_detail=str(e)
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
        if (
            self._kidney_terms_cache is not None
            and self._kidney_terms_cache_time is not None
            and time.time() - self._kidney_terms_cache_time
            < ANNOTATION_COMMON_CONFIG["cache_time_day"]
        ):
            return self._kidney_terms_cache

        # Use the existing HPO pipeline to get kidney terms
        # Use longer timeout (90s) for HPO API - descendants endpoint returns large data (3+ MB)
        from app.core.cache_service import get_cache_service
        from app.core.cached_http_client import CachedHttpClient
        from app.core.hpo.pipeline import HPOPipeline

        try:
            cache_service = get_cache_service(self.session) if self.session else None
            http_client = (
                CachedHttpClient(cache_service=cache_service, timeout=90.0)
                if cache_service
                else None
            )
            pipeline = HPOPipeline(cache_service=cache_service, http_client=http_client)
        except Exception as e:
            logger.sync_warning(f"Could not initialize full pipeline, using basic: {e}")
            pipeline = HPOPipeline()

        # Get ALL configured kidney root terms from configuration
        kidney_root_terms = get_source_parameter("HPO", "kidney_terms", [])

        # Collect all descendants from ALL configured kidney root terms
        kidney_term_ids = set()
        for root_term in kidney_root_terms:
            try:
                descendants = await pipeline.terms.get_descendants(
                    root_term, max_depth=pipeline.max_depth, include_self=True
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
        return [phenotype for phenotype in phenotypes if phenotype.get("id") in kidney_term_ids]

    async def get_classification_term_descendants(
        self, classification_type: str, force_refresh: bool = False
    ) -> dict[str, set[str]]:
        """
        Get all descendant terms for classification categories.
        Reuses existing HPO pipeline for term traversal (DRY principle).

        Args:
            classification_type: Type of classification ("onset_groups" or "syndromic_indicators")
            force_refresh: Force cache refresh if True
        """
        import time

        from app.core.datasource_config import get_source_parameter

        logger.sync_info(f"Getting classification descendants for {classification_type}")

        # Check cache (24-hour TTL like kidney terms) - only if not forcing refresh
        if (
            not force_refresh
            and self._classification_cache_time is not None
            and time.time() - self._classification_cache_time
            < ANNOTATION_COMMON_CONFIG["cache_time_day"]
        ):
            # Return appropriate cache
            if classification_type == "onset_groups" and self._onset_descendants_cache:
                logger.sync_info(
                    f"Using cached onset descendants: {len(self._onset_descendants_cache)} groups"
                )
                return self._onset_descendants_cache
            elif (
                classification_type == "syndromic_indicators" and self._syndromic_descendants_cache
            ):
                logger.sync_info(
                    f"Using cached syndromic descendants: {len(self._syndromic_descendants_cache)} groups"
                )
                return self._syndromic_descendants_cache

        # Need to refresh cache
        logger.sync_info(f"Refreshing {classification_type} descendants cache")

        # Import with proper initialization
        from app.core.cache_service import get_cache_service
        from app.core.cached_http_client import CachedHttpClient
        from app.core.hpo.pipeline import HPOPipeline

        # Ensure proper pipeline initialization with cache and http client
        # Use longer timeout (90s) for HPO API - descendants endpoint returns large data (3+ MB)
        try:
            cache_service = get_cache_service(self.session) if self.session else None
            http_client = (
                CachedHttpClient(cache_service=cache_service, timeout=90.0)
                if cache_service
                else None
            )
            pipeline = HPOPipeline(cache_service=cache_service, http_client=http_client)
        except Exception as e:
            logger.sync_warning(f"Could not initialize full pipeline, using basic: {e}")
            pipeline = HPOPipeline()

        classification_config = get_source_parameter("HPO", classification_type, {})
        logger.sync_info(
            f"Classification config for {classification_type}: {classification_config}"
        )

        descendants_map = {}
        for group_key, group_config in classification_config.items():
            descendants = set()

            # Handle both single root_term and multiple root_terms
            root_terms = []
            if isinstance(group_config, dict):
                if "root_term" in group_config:
                    root_terms = [group_config["root_term"]]
                elif "root_terms" in group_config:
                    root_terms = group_config["root_terms"]
            else:
                # For syndromic_indicators, the value is directly the term
                root_terms = [group_config]

            logger.sync_info(f"Fetching descendants for {group_key}: root terms {root_terms}")

            # Reuse existing pipeline to get descendants
            for term in root_terms:
                try:
                    term_descendants = await pipeline.terms.get_descendants(
                        term, max_depth=pipeline.max_depth, include_self=True
                    )
                    descendants.update(term_descendants)
                    logger.sync_info(
                        f"Got {len(term_descendants)} descendants for {term} in {group_key}"
                    )
                except Exception as e:
                    logger.sync_error(
                        f"Failed to get descendants for {term} in {group_key}",
                        error_detail=str(e),
                        classification_type=classification_type,
                    )
                    # Continue with other terms

            descendants_map[group_key] = descendants
            logger.sync_info(f"{group_key}: Total {len(descendants)} descendant terms")

        # Log summary
        total_descendants = sum(len(d) for d in descendants_map.values())
        logger.sync_info(
            f"Classification {classification_type} complete",
            groups=len(descendants_map),
            total_descendants=total_descendants,
        )

        # Update cache
        if classification_type == "onset_groups":
            self._onset_descendants_cache = descendants_map
        elif classification_type == "syndromic_indicators":
            self._syndromic_descendants_cache = descendants_map

        self._classification_cache_time = time.time()

        return descendants_map

    async def classify_gene_phenotypes(self, phenotypes: list[dict]) -> dict[str, Any]:
        """
        Classify phenotypes into clinical, onset, and syndromic groups.

        Args:
            phenotypes: List of HPO phenotype dictionaries

        Returns:
            Classification results with scores and confidence
        """
        # Build set of phenotype IDs, filtering out None values and ensuring str type
        phenotype_ids: set[str] = {
            str(p.get("id")) for p in phenotypes if p.get("id") is not None
        }

        classification = {
            "clinical_group": await self._classify_clinical_group(phenotype_ids),
            "onset_group": await self._classify_onset_group(phenotype_ids),
            "syndromic_assessment": await self._assess_syndromic_features(phenotype_ids),
        }

        return classification

    async def _classify_clinical_group(self, phenotype_ids: set[str]) -> dict[str, Any]:
        """
        Classify into clinical kidney disease groups based on signature terms.
        """
        from app.core.datasource_config import get_source_parameter

        config = get_source_parameter("HPO", "clinical_groups", {})

        scores: dict[str, float] = {}
        all_matches: dict[str, list[str]] = {}

        for group_key, group_config in config.items():
            signature_terms = set(group_config.get("signature_terms", []))

            # Direct matches with signature terms
            matches = phenotype_ids.intersection(signature_terms)

            # Calculate score based on matches and weight
            weight = group_config.get("weight", 1.0)
            if signature_terms:
                score = (len(matches) / len(signature_terms)) * weight
            else:
                score = 0.0

            scores[group_key] = round(score, 3)
            if matches:
                all_matches[group_key] = list(matches)

        # Normalize scores to sum to 1.0
        total_score = sum(scores.values())
        if total_score > 0:
            scores = {k: round(v / total_score, 3) for k, v in scores.items()}

        # Determine primary group (highest score)
        primary: str | None = (
            max(scores, key=lambda k: scores.get(k, 0.0))
            if scores and max(scores.values()) > 0
            else None
        )

        return {
            "primary": primary,
            "scores": scores,
            "supporting_terms": all_matches.get(primary, []) if primary else [],
        }

    async def _classify_onset_group(self, phenotype_ids: set[str]) -> dict[str, Any]:
        """
        Classify based on age of onset using HPO term hierarchy.
        """
        # Get cached descendants for onset groups
        onset_descendants = await self.get_classification_term_descendants("onset_groups")

        scores: dict[str, int] = {}
        for group_key, descendant_terms in onset_descendants.items():
            matches = phenotype_ids.intersection(descendant_terms)
            scores[group_key] = len(matches)

        # Normalize scores to probabilities
        total = sum(scores.values())
        normalized_scores: dict[str, float] = {}
        if total > 0:
            normalized_scores = {k: round(v / total, 3) for k, v in scores.items()}
        else:
            normalized_scores = dict.fromkeys(scores, 0.0)

        primary: str | None = (
            max(normalized_scores, key=lambda k: normalized_scores.get(k, 0.0))
            if normalized_scores and max(normalized_scores.values()) > 0
            else None
        )

        return {
            "primary": primary,
            "scores": normalized_scores,
        }

    async def _assess_syndromic_features(self, phenotype_ids: set[str]) -> dict:
        """
        Assess syndromic features with sub-category scoring.
        Matches R implementation: checks ALL phenotypes and calculates per-category scores.
        """
        logger.sync_debug(f"Assessing syndromic features for {len(phenotype_ids)} phenotypes")

        # Get descendants for syndromic indicator terms (cached)
        syndromic_descendants = await self.get_classification_term_descendants(
            "syndromic_indicators"
        )

        # Log what we got
        logger.sync_debug(
            "Syndromic descendants loaded",
            categories=list(syndromic_descendants.keys()),
            sizes={k: len(v) for k, v in syndromic_descendants.items()},
        )

        # Calculate matches and scores for each category
        category_matches = {}
        category_scores = {}
        total_phenotypes = len(phenotype_ids)

        if total_phenotypes == 0:
            logger.sync_debug("No phenotypes to assess, returning default")
            return {
                "is_syndromic": False,
                "syndromic_score": 0.0,
                "category_scores": {},
                "extra_renal_categories": [],
                "extra_renal_term_counts": {},
            }

        # Check ALL phenotypes against each syndromic category
        for category, descendant_terms in syndromic_descendants.items():
            if not descendant_terms:
                logger.sync_warning(f"No descendant terms for category {category}")
                continue

            matches = phenotype_ids.intersection(descendant_terms)
            if matches:
                category_matches[category] = matches
                # Calculate proportional score for this category
                category_scores[category] = round(len(matches) / total_phenotypes, 3)
                logger.sync_debug(
                    f"Category {category}: {len(matches)} matches, score {category_scores[category]}"
                )

        # Calculate overall syndromic score
        syndromic_score = sum(category_scores.values())

        # Determine if syndromic (30% threshold)
        is_syndromic = syndromic_score >= 0.3

        result = {
            "is_syndromic": is_syndromic,
            "syndromic_score": round(syndromic_score, 3),
            "category_scores": category_scores,  # Sub-category scores like R
            "extra_renal_categories": list(category_matches.keys()),
            "extra_renal_term_counts": {k: len(v) for k, v in category_matches.items()},
        }

        logger.sync_debug(
            "Syndromic assessment complete",
            is_syndromic=is_syndromic,
            score=syndromic_score,
            categories_matched=len(category_matches),
        )

        return result

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
                    "classification": {},
                    "classification_confidence": "none",
                    "last_updated": datetime.now(timezone.utc).isoformat(),
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

            # Step 4: Classify phenotypes
            classification = {}

            if phenotypes:
                classification = await self.classify_gene_phenotypes(phenotypes)

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
                "classification": classification,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.sync_error(f"Error fetching HPO annotation for {gene.approved_symbol}: {str(e)}")
            return None

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Batch fetch annotations for multiple genes.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene_id to annotation data
        """
        results: dict[int, dict[str, Any]] = {}

        # Process genes in parallel (limit concurrency)
        batch_size = 10  # HPO API can handle moderate concurrency

        for i in range(0, len(genes), batch_size):
            batch = genes[i : i + batch_size]

            # Create tasks for this batch
            tasks = [self.fetch_annotation(gene) for gene in batch]

            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results - only store successful results
            for gene, result in zip(batch, batch_results, strict=False):
                if isinstance(result, Exception):
                    logger.sync_error(f"Failed to fetch HPO for {gene.approved_symbol}: {result}")
                    # Skip failed results to match parent return type
                elif isinstance(result, dict):
                    results[gene.id] = result
                # Skip None results to match parent return type

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
            "has_kidney_phenotype",
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
            "kidney_phenotype_count": "(annotations->>'kidney_phenotype_count')::INTEGER",
        }
