"""
Unified Diagnostic Panels data source implementation.

This module provides a hybrid source that accepts file uploads for commercial
diagnostic panel data and properly aggregates evidence across multiple providers.
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from typing import TYPE_CHECKING, Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.logging import get_logger
from app.models.gene import Gene, GeneEvidence
from app.pipeline.sources.unified.base import UnifiedDataSource

if TYPE_CHECKING:
    from app.core.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class DiagnosticPanelsSource(UnifiedDataSource):
    """
    Hybrid data source for commercial diagnostic panels.

    This source accepts file uploads (JSON, CSV, Excel) containing diagnostic
    panel information and properly aggregates data across multiple providers.

    Key features:
    - Supports multiple file formats
    - Aggregates panels and providers per gene
    - Merges evidence on re-upload (no duplicates)
    - Tracks confidence scores
    """

    @property
    def source_name(self) -> str:
        return "DiagnosticPanels"

    @property
    def namespace(self) -> str:
        return "diagnosticpanels"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | None = None,
        **kwargs,
    ):
        """Initialize diagnostic panels source."""
        super().__init__(cache_service, http_client, db_session, **kwargs)
        logger.sync_info("DiagnosticPanelsSource initialized")

    def _get_default_ttl(self) -> int:
        """Get default TTL - manual uploads don't expire."""
        return 86400 * 365  # 1 year

    async def fetch_raw_data(
        self,
        file_content: bytes,
        file_type: str,
        provider_name: str,
        tracker: "ProgressTracker" = None,
    ) -> pd.DataFrame:
        """
        Parse uploaded file and return DataFrame with provider metadata.

        Args:
            file_content: Raw file bytes
            file_type: File extension (json, csv, tsv, xlsx, xls)
            provider_name: Name of the diagnostic provider
            tracker: Optional progress tracker

        Returns:
            DataFrame with gene panel data
        """
        logger.sync_info(
            "Processing file from provider", file_type=file_type, provider_name=provider_name
        )

        try:
            if file_type == "json":
                df = self._parse_json(file_content)
            elif file_type in ["csv", "tsv"]:
                df = self._parse_csv(file_content, file_type)
            elif file_type in ["xlsx", "xls"]:
                df = self._parse_excel(file_content)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Add provider metadata to each row
            df["provider"] = provider_name

            logger.sync_info(
                "Parsed gene entries", entry_count=len(df), provider_name=provider_name
            )
            return df

        except Exception as e:
            logger.sync_error("Failed to parse file", provider_name=provider_name, error=str(e))
            raise

    def _parse_json(self, content: bytes) -> pd.DataFrame:
        """Parse JSON file format (handles scraper output)."""
        data = json.loads(content)

        # Handle different JSON structures
        if isinstance(data, dict):
            # Scraper output format
            if "genes" in data:
                gene_list = data["genes"]
            elif "data" in data:
                gene_list = data["data"]
            elif "results" in data:
                gene_list = data["results"]
            else:
                # Try to extract any list from the dict
                for _key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        gene_list = value
                        break
                else:
                    raise ValueError("Cannot find gene array in JSON structure")
        elif isinstance(data, list):
            gene_list = data
        else:
            raise ValueError(f"Invalid JSON structure: expected dict or list, got {type(data)}")

        return pd.DataFrame(gene_list)

    def _parse_csv(self, content: bytes, file_type: str) -> pd.DataFrame:
        """Parse CSV or TSV file."""
        sep = "\t" if file_type == "tsv" else ","
        return pd.read_csv(BytesIO(content), sep=sep)

    def _parse_excel(self, content: bytes) -> pd.DataFrame:
        """Parse Excel file."""
        return pd.read_excel(BytesIO(content))

    async def process_data(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Process DataFrame and aggregate panel/provider data by gene.

        Args:
            df: DataFrame with gene panel data

        Returns:
            Dictionary mapping gene symbols to aggregated evidence
        """
        gene_data = defaultdict(lambda: {"panels": set(), "providers": set(), "hgnc_ids": set()})

        for idx, row in df.iterrows():
            try:
                # Extract gene symbol (handle multiple field names)
                symbol = self._extract_gene_symbol(row)
                if not symbol:
                    continue

                # Aggregate panels
                panels = self._extract_panels(row)
                gene_data[symbol]["panels"].update(panels)

                # Track provider - check for scalar value
                if "provider" in row.index:
                    provider_val = row["provider"]
                    if provider_val is not None and not isinstance(provider_val, list | dict):
                        gene_data[symbol]["providers"].add(str(provider_val))

                # Track HGNC ID if available - check for scalar value
                if "hgnc_id" in row.index:
                    hgnc_val = row["hgnc_id"]
                    if hgnc_val is not None and not isinstance(hgnc_val, list | dict):
                        gene_data[symbol]["hgnc_ids"].add(str(hgnc_val))

            except Exception as e:
                logger.sync_warning("Error processing row", row_index=idx, error=str(e))
                continue

        # Convert to serializable format
        result = {}
        for symbol, data in gene_data.items():
            result[symbol] = {
                "panels": sorted(data["panels"]),
                "providers": sorted(data["providers"]),
                "panel_count": len(data["panels"]),
                "provider_count": len(data["providers"]),
                "hgnc_ids": sorted(data["hgnc_ids"]),  # Keep for reference
            }

        logger.sync_info("Processed unique genes", unique_gene_count=len(result))
        return result

    def _extract_gene_symbol(self, row: pd.Series) -> str | None:
        """Extract gene symbol from various possible field names."""
        field_names = [
            "symbol",
            "gene_symbol",
            "gene",
            "Gene",
            "GENE",
            "approved_symbol",
            "reported_as",
            "gene_name",
            "geneName",
            "SYMBOL",
            "Symbol",
        ]

        for field in field_names:
            if field in row.index:
                field_value = row[field]
                # Skip None and arrays/lists/dicts
                if field_value is None or isinstance(field_value, list | tuple | dict):
                    continue
                # Check for pandas null (only for scalar values)
                try:
                    if pd.isna(field_value):
                        continue
                except (TypeError, ValueError):
                    # pd.isna() failed, likely due to non-scalar type
                    continue

                value = str(field_value).strip().upper()
                # Skip invalid values
                if value and value not in ["NA", "NULL", "NONE", "", "N/A", "UNKNOWN"]:
                    return value
        return None

    def _get_source_detail(self, evidence_data: dict[str, Any]) -> str:
        """Generate source detail string for diagnostic panels evidence."""
        panel_count = evidence_data.get("panel_count", 0)
        provider_count = evidence_data.get("provider_count", 0)
        providers = evidence_data.get("providers", [])

        if providers:
            provider_str = ", ".join(providers[:3])
            if len(providers) > 3:
                provider_str += f" (+{len(providers) - 3} more)"
            return f"DiagnosticPanels: {panel_count} panels from {provider_str}"

        return f"DiagnosticPanels: {panel_count} panels, {provider_count} providers"

    async def store_evidence(
        self, db: Session, gene_data: dict[str, Any], source_detail: str | None = None
    ) -> dict[str, Any]:
        """Store evidence with MERGE semantics for diagnostic panels."""

        if not gene_data:
            return {"merged": 0, "created": 0, "failed": 0}

        stats = {"merged": 0, "created": 0, "failed": 0}

        # Get gene IDs for all symbols
        gene_symbols = list(gene_data.keys())
        gene_map = {}

        # Batch fetch genes
        stmt = select(Gene).where(Gene.approved_symbol.in_(gene_symbols))
        genes = db.execute(stmt).scalars().all()
        gene_map = {g.approved_symbol: g.id for g in genes}

        # Get existing evidence for these genes
        gene_ids = list(gene_map.values())
        stmt = select(GeneEvidence).where(
            GeneEvidence.gene_id.in_(gene_ids), GeneEvidence.source_name == self.source_name
        )
        existing_evidence = db.execute(stmt).scalars().all()
        existing_map = {e.gene_id: e for e in existing_evidence}

        # Process each gene
        for symbol, data in gene_data.items():
            gene_id = gene_map.get(symbol)
            if not gene_id:
                logger.sync_warning("Gene not found in database", symbol=symbol)
                stats["failed"] += 1
                continue

            # Current provider from source_detail
            current_provider = source_detail or "unknown"

            if gene_id in existing_map:
                # MERGE: Update existing evidence
                record = existing_map[gene_id]
                current_data = record.evidence_data or {}

                # Merge panels and providers
                existing_panels = set(current_data.get("panels", []))
                new_panels = set(data["panels"])
                merged_panels = list(existing_panels | new_panels)

                existing_providers = set(current_data.get("providers", []))
                new_providers = {current_provider}
                merged_providers = list(existing_providers | new_providers)

                existing_hgnc = set(current_data.get("hgnc_ids", []))
                new_hgnc = set(data.get("hgnc_ids", []))
                merged_hgnc = list(existing_hgnc | new_hgnc)

                # Update evidence with merged data
                record.evidence_data = {
                    "panels": merged_panels,
                    "providers": merged_providers,
                    "hgnc_ids": merged_hgnc,
                    "panel_count": len(merged_panels),
                    "provider_count": len(merged_providers),
                    "evidence_score": len(merged_panels) * 10.0,  # 10 points per panel
                }
                record.source_detail = self._get_source_detail(record.evidence_data)
                record.evidence_date = datetime.now(timezone.utc).date()

                logger.sync_debug(
                    "Merged evidence",
                    symbol=symbol,
                    panel_count=len(merged_panels),
                    provider_count=len(merged_providers),
                )
                stats["merged"] += 1

            else:
                # CREATE: New evidence record
                record = GeneEvidence(
                    gene_id=gene_id,
                    source_name=self.source_name,
                    source_detail=self._get_source_detail(data),
                    evidence_data={
                        "panels": data["panels"],
                        "providers": [current_provider],
                        "hgnc_ids": data.get("hgnc_ids", []),
                        "panel_count": data["panel_count"],
                        "provider_count": 1,
                        "evidence_score": data["panel_count"] * 10.0,  # 10 points per panel
                    },
                    evidence_date=datetime.now(timezone.utc).date(),
                )
                db.add(record)

                logger.sync_debug(
                    "Created evidence",
                    symbol=symbol,
                    panel_count=data["panel_count"],
                    provider=current_provider,
                )
                stats["created"] += 1

        return stats

    def _extract_panels(self, row: pd.Series) -> set[str]:
        """Extract panel names from row."""
        panels = set()

        if "panels" in row.index and row["panels"] is not None:
            panel_data = row["panels"]

            # Handle different panel data formats
            if isinstance(panel_data, str):
                # Single panel or comma-separated
                panels.update(p.strip() for p in panel_data.split(",") if p.strip())
            elif isinstance(panel_data, list):
                panels.update(str(p).strip() for p in panel_data if p)
            elif pd.notna(panel_data):  # Check for non-null scalar values
                panels.add(str(panel_data).strip())

        # Also check for panel_name field
        if "panel_name" in row.index and row["panel_name"] is not None:
            panels.add(str(row["panel_name"]).strip())

        return panels

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        """All manually uploaded diagnostic panel data is considered kidney-related."""
        return True
