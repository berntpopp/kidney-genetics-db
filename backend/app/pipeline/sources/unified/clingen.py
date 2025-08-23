"""
Unified ClinGen data source implementation.

This module replaces the previous ClinGen implementation with a single,
async-first implementation using the unified data source architecture.
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.datasource_config import get_source_parameter
from app.pipeline.sources.unified.base import UnifiedDataSource

if TYPE_CHECKING:
    from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class ClinGenUnifiedSource(UnifiedDataSource):
    """
    Unified ClinGen client with intelligent caching and async processing.

    Features:
    - Async-first design with batch processing
    - Kidney expert panel gene validity assessments
    - Multiple expert panel integration
    - Gene-disease validity scoring
    - Mode of inheritance extraction
    """

    @property
    def source_name(self) -> str:
        return "ClinGen"

    @property
    def namespace(self) -> str:
        return "clingen"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | None = None,
        **kwargs,
    ):
        """Initialize ClinGen client with gene validity assessment capabilities."""
        super().__init__(cache_service, http_client, db_session, **kwargs)

        # ClinGen configuration
        self.base_url = "https://search.clinicalgenome.org/api"

        # Kidney-specific affiliate/expert panel IDs
        self.kidney_affiliate_ids = [
            40066,  # Kidney Cystic and Ciliopathy Disorders
            40068,  # Glomerulopathy
            40067,  # Tubulopathy
            40069,  # Complement-Mediated Kidney Diseases
            40070,  # Congenital Anomalies of the Kidney and Urinary Tract
        ]

        # Classification scoring weights
        self.classification_weights = {
            "Definitive": 1.0,
            "Strong": 0.8,
            "Moderate": 0.6,
            "Limited": 0.3,
            "Disputed": 0.1,
            "Refuted": 0.0,
            "No Evidence": 0.0,
            "No Known Disease Relationship": 0.0,
        }

        # Kidney disease keywords
        self.kidney_keywords = [
            "kidney",
            "renal",
            "nephro",
            "glomerul",
            "tubul",
            "polycystic",
            "alport",
            "nephritis",
            "cystic",
            "ciliopathy",
            "complement",
            "cakut",
        ]

        logger.info(
            f"ClinGenUnifiedSource initialized with {len(self.kidney_affiliate_ids)} kidney panels"
        )

    def _get_default_ttl(self) -> int:
        """Get default TTL for ClinGen data."""
        return get_source_parameter("ClinGen", "cache_ttl", 86400)

    async def fetch_raw_data(self, tracker: "ProgressTracker" = None) -> dict[str, Any]:
        """
        Fetch gene validity assessments from kidney expert panels.

        Returns:
            Dictionary with validity assessments from all panels
        """
        logger.info("📥 Fetching ClinGen gene validity assessments...")

        all_validities = []
        panel_stats = {}

        # Fetch data from each kidney expert panel
        for affiliate_id in self.kidney_affiliate_ids:
            panel_data = await self._fetch_affiliate_data(affiliate_id)

            if panel_data:
                all_validities.extend(panel_data)
                panel_stats[affiliate_id] = len(panel_data)
                logger.info(f"Fetched {len(panel_data)} records from affiliate {affiliate_id}")

        return {
            "validities": all_validities,
            "panel_stats": panel_stats,
            "total_records": len(all_validities),
            "fetch_date": datetime.now(timezone.utc).isoformat(),
        }

    async def _fetch_affiliate_data(self, affiliate_id: int) -> list[dict[str, Any]]:
        """
        Fetch gene validity data from a specific ClinGen affiliate.

        Args:
            affiliate_id: ClinGen affiliate/expert panel ID

        Returns:
            List of gene validity records
        """

        async def _fetch_panel():
            """Internal function to fetch panel data."""
            url = f"{self.base_url}/affiliates/{affiliate_id}"

            try:
                response = await self.http_client.get(url, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    return data.get("rows", [])
                else:
                    logger.error(
                        f"Failed to fetch affiliate {affiliate_id}: HTTP {response.status_code}"
                    )
                    return []

            except Exception as e:
                logger.error(f"Error fetching affiliate {affiliate_id}: {e}")
                return []

        # Use unified caching
        cache_key = f"affiliate:{affiliate_id}"
        validities = await self.fetch_with_cache(
            cache_key=cache_key, fetch_func=_fetch_panel, ttl=self.cache_ttl
        )

        return validities or []

    async def process_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process ClinGen validity assessments into structured gene information.

        Args:
            raw_data: Raw data with validity assessments

        Returns:
            Dictionary mapping gene symbols to aggregated data
        """
        if not raw_data or "validities" not in raw_data:
            return {}

        gene_data_map = {}
        total_validities = 0
        kidney_related = 0

        logger.info(f"🔄 Processing {len(raw_data['validities'])} ClinGen validity assessments...")

        for validity in raw_data["validities"]:
            # Check if kidney-related
            if not self.is_kidney_related(validity):
                continue

            kidney_related += 1
            total_validities += 1

            # Extract gene information
            gene_info = self._extract_gene_info(validity)
            if not gene_info:
                continue

            symbol = gene_info["symbol"]

            # Initialize gene entry if new
            if symbol not in gene_data_map:
                gene_data_map[symbol] = {
                    "hgnc_id": gene_info["hgnc_id"],
                    "validities": [],
                    "diseases": set(),
                    "classifications": set(),
                    "expert_panels": set(),
                    "modes_of_inheritance": set(),
                    "max_classification_score": 0.0,
                }

            # Add validity assessment
            gene_data_map[symbol]["validities"].append(gene_info)
            gene_data_map[symbol]["diseases"].add(gene_info["disease_name"])
            gene_data_map[symbol]["classifications"].add(gene_info["classification"])
            gene_data_map[symbol]["expert_panels"].add(gene_info["expert_panel"])

            if gene_info["mode_of_inheritance"]:
                gene_data_map[symbol]["modes_of_inheritance"].add(gene_info["mode_of_inheritance"])

            # Update max classification score
            score = self.classification_weights.get(gene_info["classification"], 0.0)
            if score > gene_data_map[symbol]["max_classification_score"]:
                gene_data_map[symbol]["max_classification_score"] = score

        # Convert sets to lists and calculate final scores
        for _symbol, data in gene_data_map.items():
            data["diseases"] = list(data["diseases"])
            data["classifications"] = list(data["classifications"])
            data["expert_panels"] = list(data["expert_panels"])
            data["modes_of_inheritance"] = list(data["modes_of_inheritance"])

            # Calculate evidence score (0-100 scale)
            data["evidence_score"] = data["max_classification_score"] * 100

            # Add metadata
            data["validity_count"] = len(data["validities"])
            data["last_updated"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"🎯 ClinGen processing complete: "
            f"{kidney_related} kidney-related assessments, "
            f"{len(gene_data_map)} unique genes"
        )

        return gene_data_map

    def is_kidney_related(self, validity: dict[str, Any]) -> bool:
        """
        Check if a gene validity assessment is kidney-related.

        Args:
            validity: Gene validity record

        Returns:
            True if kidney-related
        """
        # Extract disease and panel names
        disease_name = validity.get("disease_name", "").lower()
        expert_panel = validity.get("ep", "").lower()

        # Combine text for searching
        combined_text = f"{disease_name} {expert_panel}"

        # Check for kidney keywords
        is_kidney = any(keyword in combined_text for keyword in self.kidney_keywords)

        # Since these are from kidney-specific panels, be more permissive
        if not is_kidney and disease_name:
            # Exclude obviously non-kidney conditions
            excluded_terms = [
                "hearing",
                "intellectual",
                "developmental",
                "cardiac",
                "retinal",
                "ocular",
            ]
            has_excluded = any(term in combined_text for term in excluded_terms)

            if not has_excluded:
                # From kidney panel and no excluded terms
                is_kidney = True

        return is_kidney

    def _extract_gene_info(self, validity: dict[str, Any]) -> dict[str, Any] | None:
        """
        Extract gene information from validity record.

        Args:
            validity: Gene validity record

        Returns:
            Gene information dictionary or None
        """
        # Extract required fields
        symbol = validity.get("symbol", "").strip()
        if not symbol:
            return None

        return {
            "symbol": symbol,
            "hgnc_id": validity.get("hgnc_id", "").strip(),
            "disease_name": validity.get("disease_name", "").strip(),
            "classification": validity.get("classification", "").strip(),
            "mode_of_inheritance": validity.get("moi", "").strip(),
            "expert_panel": validity.get("ep", "").strip(),
            "mondo_id": validity.get("mondo", "").strip(),
            "release_date": validity.get("released", "").strip(),
            "submission_id": validity.get("id", ""),
        }

    def _get_source_detail(self, evidence_data: dict[str, Any]) -> str:
        """
        Generate source detail string for evidence.

        Args:
            evidence_data: Evidence data

        Returns:
            Source detail string
        """
        validity_count = evidence_data.get("validity_count", 0)
        classifications = evidence_data.get("classifications", [])
        diseases = evidence_data.get("diseases", [])

        # Build classification summary
        if classifications:
            # Sort by weight to show best classification first
            sorted_classifications = sorted(
                set(classifications),
                key=lambda c: self.classification_weights.get(c, 0),
                reverse=True,
            )
            class_str = sorted_classifications[0] if sorted_classifications else ""
        else:
            class_str = ""

        # Build disease summary (show first disease)
        disease_str = (
            diseases[0][:30] + "..."
            if diseases and len(diseases[0]) > 30
            else diseases[0] if diseases else ""
        )

        # Combine details
        if class_str and disease_str:
            return f"ClinGen: {validity_count} assessments ({class_str} for {disease_str})"
        elif class_str:
            return f"ClinGen: {validity_count} assessments ({class_str})"
        else:
            return f"ClinGen: {validity_count} validity assessments"
