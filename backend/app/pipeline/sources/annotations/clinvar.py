"""
ClinVar Annotation Source

Fetches variant counts and clinical significance data from ClinVar
using NCBI's eUtils API.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource

logger = get_logger(__name__)


class ClinVarAnnotationSource(BaseAnnotationSource):
    """
    ClinVar variant annotation source with proper rate limiting.

    Fetches pathogenic variant counts and classifications for genes.
    Uses a two-step process:
    1. Search for all variant IDs for a gene using esearch
    2. Fetch variant details in batches using esummary
    """

    source_name = "clinvar"
    display_name = "ClinVar"
    version = "1.0"

    # Cache configuration
    cache_ttl_days = 7  # ClinVar updates weekly

    # API configuration
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    batch_size = 200  # Reduced batch size to avoid URI too long errors
    search_batch_size = 10000  # Maximum for esearch

    # Review status confidence levels (from configuration)
    _review_confidence_levels = None

    def __init__(self, session):
        """Initialize the ClinVar annotation source."""
        super().__init__(session)

        # Update source configuration
        if self.source_record:
            self.source_record.update_frequency = "weekly"
            self.source_record.description = "Clinical variant data from ClinVar database"
            self.source_record.base_url = self.base_url
            self.session.commit()

    def _get_review_confidence_levels(self) -> dict[str, int]:
        """Get review status confidence levels from configuration."""
        if self._review_confidence_levels is None:
            from app.core.datasource_config import DATA_SOURCE_CONFIG

            config = DATA_SOURCE_CONFIG.get("ClinVar", {})
            self._review_confidence_levels = config.get(
                "review_confidence",
                {
                    "practice guideline": 4,
                    "reviewed by expert panel": 4,
                    "criteria provided, multiple submitters, no conflicts": 3,
                    "criteria provided, conflicting classifications": 2,
                    "criteria provided, single submitter": 2,
                    "no assertion for the individual variant": 1,
                    "no assertion criteria provided": 1,
                    "no classification provided": 0,
                },
            )
        return self._review_confidence_levels

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def _search_variants(self, gene_symbol: str) -> list[str]:
        """
        Search for ClinVar variants with retry logic.

        Args:
            gene_symbol: Gene symbol to search for

        Returns:
            List of ClinVar variant IDs
        """
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            search_url = f"{self.base_url}/esearch.fcgi"
            params = {
                "db": "clinvar",
                "term": f"{gene_symbol}[gene] AND single_gene[prop]",
                "retmax": self.search_batch_size,
                "retmode": "json",
            }

            response = await client.get(search_url, params=params)
            data = response.json()

            id_list = data.get("esearchresult", {}).get("idlist", [])

            logger.sync_debug(  # Changed from info to debug for less noise
                f"Found {len(id_list)} ClinVar variants", gene_symbol=gene_symbol
            )

            return id_list

        except httpx.HTTPStatusError as e:
            logger.sync_error(  # Changed from warning to error
                "Failed to search ClinVar variants",
                gene_symbol=gene_symbol,
                status_code=e.response.status_code,
                response=e.response.text[:200],
            )
            raise  # Let retry decorator handle it

        except Exception as e:
            logger.sync_error(
                "Error searching ClinVar variants", gene_symbol=gene_symbol, error=str(e)
            )
            raise

    def _parse_variant(self, variant_data: dict[str, Any]) -> dict[str, Any]:
        """
        Parse a single variant from ClinVar esummary response.

        Args:
            variant_data: Raw variant data from API

        Returns:
            Parsed variant dictionary
        """
        result = {
            "variant_id": variant_data.get("uid"),
            "accession": variant_data.get("accession"),
            "title": variant_data.get("title"),
            "variant_type": variant_data.get("obj_type"),
            "classification": "Not classified",
            "review_status": "No data",
            "traits": [],
        }

        # Extract germline classification
        if "germline_classification" in variant_data:
            gc = variant_data["germline_classification"]
            result["classification"] = gc.get("description", "Not provided")
            result["review_status"] = gc.get("review_status", "No assertion")

            # Parse associated conditions/traits
            if "trait_set" in gc:
                for trait in gc["trait_set"]:
                    trait_info = {
                        "name": trait.get("trait_name"),
                        "omim_id": None,
                        "medgen_id": None,
                    }
                    # Extract cross-references
                    if "trait_xrefs" in trait:
                        for xref in trait["trait_xrefs"]:
                            if xref["db_source"] == "OMIM":
                                trait_info["omim_id"] = xref["db_id"]
                            elif xref["db_source"] == "MedGen":
                                trait_info["medgen_id"] = xref["db_id"]
                    result["traits"].append(trait_info)

        # Extract variant details if available
        if "variation_set" in variant_data and variant_data["variation_set"]:
            var = variant_data["variation_set"][0]
            result["cdna_change"] = var.get("cdna_change", "")

            # Extract protein change from title
            import re

            protein_match = re.search(r"\(p\.(.*?)\)", result["title"])
            result["protein_change"] = protein_match.group(1) if protein_match else ""

        return result

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def _fetch_variant_batch(self, variant_ids: list[str]) -> list[dict[str, Any]]:
        """
        Fetch variant details with retry logic and rate limiting.

        Args:
            variant_ids: List of ClinVar variant IDs (max 200)

        Returns:
            List of parsed variant data
        """
        if not variant_ids:
            return []

        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            summary_url = f"{self.base_url}/esummary.fcgi"
            params = {"db": "clinvar", "id": ",".join(variant_ids), "retmode": "json"}

            response = await client.get(summary_url, params=params)
            data = response.json()

            result = data.get("result", {})

            # Parse each variant
            variants = []
            for uid in result.get("uids", []):
                if uid in result:
                    variant = self._parse_variant(result[uid])
                    variants.append(variant)

            return variants

        except httpx.HTTPStatusError as e:
            # Check rate limit headers
            if e.response.status_code == 429 or "X-RateLimit-Remaining" in e.response.headers:
                remaining = e.response.headers.get("X-RateLimit-Remaining", "unknown")
                logger.sync_error(
                    "ClinVar rate limit hit",
                    status_code=e.response.status_code,
                    remaining_requests=remaining,
                    batch_size=len(variant_ids),
                )
            else:
                logger.sync_error(  # Changed from warning to error
                    "Failed to fetch ClinVar variant details",
                    status_code=e.response.status_code,
                    batch_size=len(variant_ids),
                )
            raise

        except Exception as e:
            logger.sync_error(
                "Error fetching ClinVar variant batch", error=str(e), batch_size=len(variant_ids)
            )
            raise

    def _aggregate_variants(self, variants: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Aggregate variant data into summary statistics.

        Args:
            variants: List of parsed variant data

        Returns:
            Aggregated statistics dictionary
        """
        stats = {
            "total_count": len(variants),
            "pathogenic_count": 0,
            "likely_pathogenic_count": 0,
            "vus_count": 0,
            "benign_count": 0,
            "likely_benign_count": 0,
            "conflicting_count": 0,
            "not_provided_count": 0,
            "high_confidence_count": 0,
            "variant_type_counts": defaultdict(int),
            "traits_summary": defaultdict(int),
        }

        # Get confidence levels
        confidence_levels = self._get_review_confidence_levels()

        for variant in variants:
            classification = variant["classification"].lower()

            # Count by classification
            if "pathogenic" in classification:
                if "likely" in classification:
                    stats["likely_pathogenic_count"] += 1
                elif "/" not in classification:  # Exclude combined classifications
                    stats["pathogenic_count"] += 1
                # Handle combined "Pathogenic/Likely pathogenic"
                elif "pathogenic/likely pathogenic" in classification:
                    stats["pathogenic_count"] += 1
            elif "benign" in classification:
                if "likely" in classification:
                    stats["likely_benign_count"] += 1
                elif "/" not in classification:
                    stats["benign_count"] += 1
            elif "uncertain" in classification or "vus" in classification.lower():
                stats["vus_count"] += 1
            elif "conflicting" in classification:
                stats["conflicting_count"] += 1
            elif "not provided" in classification:
                stats["not_provided_count"] += 1

            # Count high confidence variants (level 3+)
            confidence = confidence_levels.get(variant["review_status"], 0)
            if confidence >= 3:
                stats["high_confidence_count"] += 1

            # Count variant types
            stats["variant_type_counts"][variant["variant_type"]] += 1

            # Aggregate traits
            for trait in variant["traits"]:
                if trait["name"]:
                    stats["traits_summary"][trait["name"]] += 1

        # Convert defaultdicts to regular dicts
        stats["variant_type_counts"] = dict(stats["variant_type_counts"])

        # Get top 5 traits
        top_traits = sorted(stats["traits_summary"].items(), key=lambda x: x[1], reverse=True)[:5]
        stats["top_traits"] = [{"trait": t[0], "count": t[1]} for t in top_traits]
        del stats["traits_summary"]

        # Calculate derived metrics
        if stats["total_count"] > 0:
            stats["high_confidence_percentage"] = round(
                (stats["high_confidence_count"] / stats["total_count"]) * 100, 1
            )
            stats["pathogenic_percentage"] = round(
                (
                    (stats["pathogenic_count"] + stats["likely_pathogenic_count"])
                    / stats["total_count"]
                )
                * 100,
                1,
            )
        else:
            stats["high_confidence_percentage"] = 0
            stats["pathogenic_percentage"] = 0

        # Add summary flags
        stats["has_pathogenic"] = (
            stats["pathogenic_count"] > 0 or stats["likely_pathogenic_count"] > 0
        )

        return stats

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch ClinVar annotation for a gene.

        Args:
            gene: Gene object to fetch annotations for

        Returns:
            Dictionary with annotation data or None if not found
        """
        try:
            # Step 1: Search for all variant IDs
            variant_ids = await self._search_variants(gene.approved_symbol)

            if not variant_ids:
                # No variants found
                return {
                    "gene_symbol": gene.approved_symbol,
                    "total_variants": 0,
                    "variant_summary": "No variants",
                    "pathogenic_count": 0,
                    "likely_pathogenic_count": 0,
                    "vus_count": 0,
                    "benign_count": 0,
                    "likely_benign_count": 0,
                    "conflicting_count": 0,
                    "has_pathogenic": False,
                    "pathogenic_percentage": 0,
                    "high_confidence_percentage": 0,
                    "top_traits": [],
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }

            # Step 2: Fetch variant details in batches with progress
            all_variants = []
            total_batches = (len(variant_ids) + self.batch_size - 1) // self.batch_size

            for batch_num, i in enumerate(range(0, len(variant_ids), self.batch_size)):
                batch_ids = variant_ids[i : i + self.batch_size]

                # Show progress
                if batch_num % 5 == 0:  # Log every 5th batch
                    logger.sync_debug(
                        "Fetching ClinVar variants",
                        gene_symbol=gene.approved_symbol,
                        batch=f"{batch_num + 1}/{total_batches}",
                        variants=f"{i}/{len(variant_ids)}",
                    )

                try:
                    batch_variants = await self._fetch_variant_batch(batch_ids)
                    all_variants.extend(batch_variants)
                except Exception as e:
                    logger.sync_error(
                        "Failed to fetch variant batch",
                        gene_symbol=gene.approved_symbol,
                        batch=batch_num,
                        error=str(e),
                    )
                    # Continue with partial data rather than failing completely
                    if self.circuit_breaker and self.circuit_breaker.state == "open":
                        logger.sync_error("Circuit breaker open, using partial data")
                        break

            # Step 3: Aggregate statistics
            stats = self._aggregate_variants(all_variants)

            # Build final annotation
            annotation = {
                "gene_symbol": gene.approved_symbol,
                "total_variants": stats["total_count"],
                "pathogenic_count": stats["pathogenic_count"],
                "likely_pathogenic_count": stats["likely_pathogenic_count"],
                "vus_count": stats["vus_count"],
                "benign_count": stats["benign_count"],
                "likely_benign_count": stats["likely_benign_count"],
                "conflicting_count": stats["conflicting_count"],
                "not_provided_count": stats.get("not_provided_count", 0),
                "has_pathogenic": stats["has_pathogenic"],
                "pathogenic_percentage": stats["pathogenic_percentage"],
                "high_confidence_count": stats["high_confidence_count"],
                "high_confidence_percentage": stats["high_confidence_percentage"],
                "variant_types": stats["variant_type_counts"],
                "top_traits": stats["top_traits"],
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            # Generate summary text
            if stats["has_pathogenic"]:
                p_count = stats["pathogenic_count"] + stats["likely_pathogenic_count"]
                annotation["variant_summary"] = f"{p_count} pathogenic/likely pathogenic variants"
            elif stats["vus_count"] > 0:
                annotation["variant_summary"] = f"{stats['vus_count']} VUS variants"
            else:
                annotation["variant_summary"] = "No pathogenic variants"

            logger.sync_info(
                "Successfully annotated gene with ClinVar data",
                gene_symbol=gene.approved_symbol,
                total_variants=stats["total_count"],
                pathogenic=stats["pathogenic_count"] + stats["likely_pathogenic_count"],
            )

            return annotation

        except Exception as e:
            logger.sync_error(
                "Error fetching ClinVar annotation", gene_symbol=gene.approved_symbol, error=str(e)
            )
            return None

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Validate ClinVar annotation data."""
        if not super()._is_valid_annotation(annotation_data):
            return False

        # ClinVar specific: must have variant counts and gene_symbol
        required_fields = ["total_variants", "gene_symbol"]
        has_required = all(field in annotation_data for field in required_fields)

        return has_required

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Fetch annotations for multiple genes.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene IDs to annotation data
        """
        results = {}

        # Process genes concurrently but with a limit
        semaphore = asyncio.Semaphore(3)  # Limit concurrent requests

        async def fetch_with_semaphore(gene):
            async with semaphore:
                annotation = await self.fetch_annotation(gene)
                if annotation:
                    results[gene.id] = annotation

        await asyncio.gather(*[fetch_with_semaphore(gene) for gene in genes])

        return results
