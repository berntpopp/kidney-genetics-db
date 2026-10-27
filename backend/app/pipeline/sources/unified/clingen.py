"""
Unified ClinGen data source implementation.

This module replaces the previous ClinGen implementation with a single,
async-first implementation using the unified data source architecture.

Downloads the bulk gene-validity CSV (1 request) and filters it locally.
"""

import csv
import io
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.datasource_config import get_source_parameter, matches_kidney_keyword
from app.core.logging import get_logger
from app.pipeline.sources.unified.base import UnifiedDataSource

if TYPE_CHECKING:
    from app.core.progress_tracker import ProgressTracker

logger = get_logger(__name__)


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
        **kwargs: Any,
    ) -> None:
        """Initialize ClinGen client with gene validity assessment capabilities."""
        super().__init__(cache_service, http_client, db_session, **kwargs)

        # ClinGen configuration
        self.csv_url = "https://search.clinicalgenome.org/kb/gene-validity/download"

        # Kidney panel GCEP names (for CSV filtering)
        self.kidney_panel_names = {
            "Kidney Cystic and Ciliopathy Disorders Gene Curation Expert Panel",
            "Glomerulopathy Gene Curation Expert Panel",
            "Tubulopathy Gene Curation Expert Panel",
            "Complement-Mediated Kidney Diseases Gene Curation Expert Panel",
            "Congenital Anomalies of the Kidney and Urinary Tract Gene Curation Expert Panel",
        }

        # Classification scoring weights - read from config
        self.classification_weights = get_source_parameter(
            "ClinGen",
            "classification_weights",
            {  # Fallback if config missing
                "Definitive": 1.0,
                "Strong": 0.8,
                "Moderate": 0.6,
                "Limited": 0.3,
                "Disputed": 0.1,
                "Refuted": 0.0,
                "No Evidence": 0.0,
                "No Known Disease Relationship": 0.0,
            },
        )

        logger.sync_info(
            "ClinGenUnifiedSource initialized", kidney_panels=len(self.kidney_panel_names)
        )

    def _get_default_ttl(self) -> int:
        """Get default TTL for ClinGen data."""
        return cast(int, get_source_parameter("ClinGen", "cache_ttl", 86400))

    async def fetch_raw_data(
        self, tracker: "ProgressTracker | None" = None, mode: str = "smart"
    ) -> dict[str, Any]:
        """
        Download the full ClinGen gene-disease validity CSV and filter it to
        kidney expert panels and kidney diseases from other panels.

        Errors propagate. There is no per-panel fallback: it only saw the five kidney
        panels, so a full refresh on its result pruned cross-panel genes such as HNF1B.
        A failed download fails the run and keeps the existing evidence.
        """
        logger.sync_info("Fetching ClinGen gene validity assessments")
        if self.http_client is None:
            raise RuntimeError("HTTP client not initialized")

        response = await self.http_client.get(self.csv_url, timeout=60)
        response.raise_for_status()
        reader = csv.reader(io.StringIO(response.text))

        # Skip header rows (4 metadata lines + 1 column header)
        header_row = None
        for i, row in enumerate(reader):
            if i == 4:
                header_row = row
                break
        if not header_row or header_row[0].strip() != "GENE SYMBOL":
            raise ValueError(f"ClinGen CSV has unexpected format: header {header_row!r}")

        # CSV columns: GENE SYMBOL, GENE ID (HGNC), DISEASE LABEL,
        #   DISEASE ID (MONDO), MOI, SOP, CLASSIFICATION,
        #   ONLINE REPORT, CLASSIFICATION DATE, GCEP
        all_validities: list[dict[str, Any]] = []
        panel_stats: dict[str, int] = {}

        for row in reader:
            if len(row) < 10:
                continue

            gcep = row[9].strip()
            disease = row[2].strip().lower()
            is_kidney_panel = gcep in self.kidney_panel_names
            # Also include entries from non-kidney panels if disease is kidney-related
            is_kidney_disease = matches_kidney_keyword(disease)

            if not is_kidney_panel and not is_kidney_disease:
                continue

            all_validities.append(
                {
                    "symbol": row[0].strip(),
                    "hgnc_id": row[1].strip(),
                    "disease_name": row[2].strip(),
                    "mondo": row[3].strip(),
                    "moi": row[4].strip(),
                    "classification": row[6].strip(),
                    "id": row[7].strip(),  # Online report URL as submission ID
                    "released": row[8].strip(),
                    "ep": gcep,
                }
            )
            panel_stats[gcep] = panel_stats.get(gcep, 0) + 1

        logger.sync_info(
            "ClinGen CSV parsed",
            total_kidney_records=len(all_validities),
            panels=len(panel_stats),
        )

        return {
            "validities": all_validities,
            "panel_stats": panel_stats,
            "total_records": len(all_validities),
            "fetch_date": datetime.now(timezone.utc).isoformat(),
        }

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

        logger.sync_info(
            "Processing ClinGen validity assessments", assessment_count=len(raw_data["validities"])
        )

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

        logger.sync_info(
            "ClinGen processing complete",
            kidney_related_assessments=kidney_related,
            unique_genes=len(gene_data_map),
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
        is_kidney = matches_kidney_keyword(combined_text)

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
            else diseases[0]
            if diseases
            else ""
        )

        # Combine details
        if class_str and disease_str:
            return f"ClinGen: {validity_count} assessments ({class_str} for {disease_str})"
        elif class_str:
            return f"ClinGen: {validity_count} assessments ({class_str})"
        else:
            return f"ClinGen: {validity_count} validity assessments"
