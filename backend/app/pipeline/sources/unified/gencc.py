"""
Unified GenCC data source implementation.

This module replaces the previous three implementations (gencc.py, gencc_async.py,
gencc_cached.py) with a single, async-first implementation using the unified
data source architecture.
"""

import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import TYPE_CHECKING, Any

import pandas as pd
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.datasource_config import get_source_parameter
from app.pipeline.sources.unified.base import UnifiedDataSource

if TYPE_CHECKING:
    from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class GenCCUnifiedSource(UnifiedDataSource):
    """
    Unified GenCC client with intelligent caching and async processing.

    Features:
    - Async-first design
    - Persistent caching with ETags
    - Kidney-specific filtering
    - Comprehensive gene-disease relationship processing
    """

    @property
    def source_name(self) -> str:
        return "GenCC"

    @property
    def namespace(self) -> str:
        return "gencc"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | None = None,
        **kwargs,
    ):
        """Initialize GenCC client with caching and HTTP services."""
        super().__init__(cache_service, http_client, db_session, **kwargs)

        # GenCC configuration
        self.download_url = "https://search.thegencc.org/download/action/submissions-export-xlsx"

        # Kidney-related keywords for filtering
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

        # GenCC classification weights for evidence scoring
        self.classification_weights = {
            "Definitive": 1.0,
            "Strong": 0.8,
            "Moderate": 0.6,
            "Supportive": 0.5,
            "Limited": 0.3,
            "Disputed Evidence": 0.1,
            "No Known Disease Relationship": 0.0,
            "Refuted Evidence": 0.0,
        }

        logger.info(f"GenCCUnifiedSource initialized with TTL: {self.cache_ttl}s")

    def _get_default_ttl(self) -> int:
        """Get default TTL for GenCC data."""
        return get_source_parameter("GenCC", "cache_ttl", 43200)

    async def fetch_raw_data(self, tracker: "ProgressTracker" = None) -> pd.DataFrame:
        """
        Fetch GenCC submissions Excel file with intelligent caching.

        Uses unified caching with automatic retry logic.

        Returns:
            Pandas DataFrame with GenCC submissions
        """

        async def _fetch_gencc_data():
            """Internal function to fetch GenCC data."""
            logger.info(f"📥 Downloading GenCC submissions from: {self.download_url}")
            logger.info("🔄 Starting download... (this may take 30-60 seconds for ~3.6MB file)")

            # Use cached HTTP client for download
            response = await self.http_client.get(
                self.download_url,
                timeout=120,  # Longer timeout for large file
            )

            if response.status_code != 200:
                raise ValueError(f"HTTP {response.status_code}: Failed to download GenCC file")

            # Parse Excel file from response content
            df = pd.read_excel(BytesIO(response.content))
            logger.info(f"📊 Parsed GenCC Excel file: {len(df)} total submissions")

            # Log column structure for debugging
            logger.info(f"GenCC columns: {list(df.columns)[:10]}...")  # First 10 columns

            return df

        # Use unified caching pattern
        cache_key = "excel_file"
        df = await self.fetch_with_cache(
            cache_key=cache_key, fetch_func=_fetch_gencc_data, ttl=self.cache_ttl
        )

        logger.info(f"✅ GenCC data ready: {len(df)} submissions")
        return df

    async def process_data(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Process GenCC DataFrame into structured gene information.

        Args:
            df: Raw GenCC submissions DataFrame

        Returns:
            Dictionary mapping gene symbols to aggregated gene data
        """
        logger.info(f"🔄 Processing {len(df)} GenCC submissions...")

        gene_data_map = {}
        kidney_related_count = 0

        for idx, row in df.iterrows():
            # Filter for kidney-related submissions
            if not self.is_kidney_related(row):
                continue

            kidney_related_count += 1

            # Extract gene information
            gene_info = self._extract_gene_info(row)
            if not gene_info:
                logger.debug(f"⚠️ Failed to extract gene info from row {idx}")
                continue

            symbol = gene_info["symbol"]

            # Aggregate by gene symbol
            if symbol not in gene_data_map:
                gene_data_map[symbol] = {
                    "hgnc_id": gene_info["hgnc_id"],
                    "submissions": [],
                    "diseases": set(),
                    "classifications": set(),
                    "submitters": set(),
                    "modes_of_inheritance": set(),
                }

            # Add this submission to the gene's data
            gene_data_map[symbol]["submissions"].append(gene_info)
            gene_data_map[symbol]["diseases"].add(gene_info["disease_name"])
            gene_data_map[symbol]["classifications"].add(gene_info["classification"])
            gene_data_map[symbol]["submitters"].add(gene_info["submitter"])

            if gene_info["mode_of_inheritance"]:
                gene_data_map[symbol]["modes_of_inheritance"].add(gene_info["mode_of_inheritance"])

        # Convert sets to lists for JSON serialization
        for _symbol, data in gene_data_map.items():
            for key in ["diseases", "classifications", "submitters", "modes_of_inheritance"]:
                data[key] = list(data[key])

            # Add metadata
            data["submission_count"] = len(data["submissions"])
            data["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Calculate evidence score based on classifications
            data["evidence_score"] = self._calculate_evidence_score(data["classifications"])

        logger.info(
            f"🎯 GenCC processing complete: "
            f"{kidney_related_count} kidney-related submissions, "
            f"{len(gene_data_map)} unique genes"
        )

        return gene_data_map

    def is_kidney_related(self, row: pd.Series) -> bool:
        """
        Check if a GenCC submission is kidney-related.

        Args:
            row: DataFrame row with GenCC submission

        Returns:
            True if kidney-related
        """
        # Fields to check for kidney keywords
        text_fields = []

        # GenCC-specific field names for disease information
        disease_fields = [
            "disease_title",
            "disease_original_title",
            "submitted_as_disease_name",
            "disease_name",
            "condition",
            "disease",
            "phenotype",
            "disorder",
        ]

        for field in disease_fields:
            if field in row.index and pd.notna(row[field]):
                text_fields.append(str(row[field]).lower())

        # Also check description fields
        for field in row.index:
            if "description" in field.lower() and pd.notna(row[field]):
                text_fields.append(str(row[field]).lower())

        # Combine all text
        combined_text = " ".join(text_fields)

        # Check for kidney-related keywords
        return any(keyword in combined_text for keyword in self.kidney_keywords)

    def _extract_gene_info(self, row: pd.Series) -> dict[str, Any] | None:
        """
        Extract gene information from GenCC submission row.

        Args:
            row: DataFrame row with GenCC submission

        Returns:
            Gene information dictionary or None if invalid
        """
        try:
            # Extract gene symbol
            symbol = None
            gene_fields = [
                "gene_symbol",
                "submitted_as_hgnc_symbol",
                "symbol",
                "gene",
                "hgnc_symbol",
            ]
            for field in gene_fields:
                if field in row.index and pd.notna(row[field]):
                    symbol = str(row[field]).strip()
                    break

            if not symbol:
                return None

            # Extract HGNC ID
            hgnc_id = None
            hgnc_fields = ["submitted_as_hgnc_id", "hgnc_id", "hgnc"]
            for field in hgnc_fields:
                if field in row.index and pd.notna(row[field]):
                    hgnc_id = str(row[field]).strip()
                    break

            # Extract disease information
            disease_name = ""
            disease_fields = [
                "disease_title",
                "disease_original_title",
                "submitted_as_disease_name",
                "disease_name",
                "condition",
                "disease",
                "phenotype",
            ]
            for field in disease_fields:
                if field in row.index and pd.notna(row[field]):
                    disease_name = str(row[field]).strip()
                    break

            # Extract classification
            classification = ""
            classification_fields = [
                "classification_title",
                "submitted_as_classification_name",
                "classification",
                "validity",
                "confidence",
            ]
            for field in classification_fields:
                if field in row.index and pd.notna(row[field]):
                    classification = str(row[field]).strip()
                    break

            # Extract submitter
            submitter = ""
            submitter_fields = [
                "submitter_title",
                "submitted_as_submitter_name",
                "submitter",
                "source",
                "submitting_organization",
            ]
            for field in submitter_fields:
                if field in row.index and pd.notna(row[field]):
                    submitter = str(row[field]).strip()
                    break

            # Extract mode of inheritance
            mode_of_inheritance = ""
            moi_fields = [
                "moi_title",
                "submitted_as_moi_name",
                "mode_of_inheritance",
                "inheritance",
                "moi",
            ]
            for field in moi_fields:
                if field in row.index and pd.notna(row[field]):
                    mode_of_inheritance = str(row[field]).strip()
                    break

            # Extract submission date
            submission_date = ""
            date_fields = [
                "submitted_as_date",
                "submitted_run_date",
                "date",
                "submission_date",
                "last_updated",
            ]
            for field in date_fields:
                if field in row.index and pd.notna(row[field]):
                    submission_date = str(row[field]).strip()
                    break

            # Handle NaN values in raw data
            raw_data = row.to_dict()
            # Replace NaN values with None for JSON serialization
            for key, value in raw_data.items():
                if pd.isna(value):
                    raw_data[key] = None

            return {
                "symbol": symbol,
                "hgnc_id": hgnc_id,
                "disease_name": disease_name,
                "classification": classification,
                "submitter": submitter,
                "mode_of_inheritance": mode_of_inheritance,
                "submission_date": submission_date,
                "raw_data": raw_data,  # Store full record with NaN values replaced
            }

        except Exception as e:
            logger.error(f"Error extracting gene info from GenCC row: {e}")
            return None

    def _calculate_evidence_score(self, classifications: list) -> float:
        """
        Calculate evidence score based on classifications.

        Args:
            classifications: List of classification strings

        Returns:
            Weighted evidence score (0.0 to 1.0)
        """
        if not classifications:
            return 0.0

        scores = []
        for classification in classifications:
            score = self.classification_weights.get(classification, 0.0)
            scores.append(score)

        # Return the maximum score (best evidence)
        return max(scores) if scores else 0.0

    def _get_source_detail(self, evidence_data: dict[str, Any]) -> str:
        """Generate GenCC-specific source detail string."""
        submission_count = evidence_data.get("submission_count", 0)
        submitter_count = len(evidence_data.get("submitters", []))
        classifications = evidence_data.get("classifications", [])

        # Add classification summary
        if classifications:
            # Get unique classifications and sort by weight
            unique_classifications = sorted(
                set(classifications),
                key=lambda c: self.classification_weights.get(c, 0),
                reverse=True,
            )
            classification_str = f" ({', '.join(unique_classifications[:2])})"  # Show top 2
        else:
            classification_str = ""

        return (
            f"{submission_count} submissions from {submitter_count} submitters{classification_str}"
        )


def get_gencc_client(**kwargs) -> GenCCUnifiedSource:
    """
    Factory function for GenCC client.

    Returns:
        GenCCUnifiedSource instance
    """
    return GenCCUnifiedSource(**kwargs)


# Backwards compatibility function
async def update_gencc_async(db: Session, tracker) -> dict[str, Any]:
    """
    Backwards compatibility function for async GenCC updates.

    Args:
        db: Database session
        tracker: Progress tracker

    Returns:
        Update statistics
    """
    client = get_gencc_client(db_session=db)
    return await client.update_data(db, tracker)
