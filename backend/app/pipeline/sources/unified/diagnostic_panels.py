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
from app.core.datasource_config import get_source_parameter
from app.core.logging import get_logger
from app.models.gene import Gene, GeneEvidence
from app.pipeline.sources.unified.base import UnifiedDataSource
from app.pipeline.sources.unified.filtering_utils import (
    apply_memory_filter,
    validate_threshold_config,
)

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
        **kwargs: Any,
    ) -> None:
        """Initialize diagnostic panels source."""
        super().__init__(cache_service, http_client, db_session, **kwargs)

        # Load filtering configuration
        raw_threshold = get_source_parameter("DiagnosticPanels", "min_panels", 1)
        self.min_panels = validate_threshold_config(raw_threshold, "panels", self.source_name)
        self.filtering_enabled = get_source_parameter(
            "DiagnosticPanels", "min_panels_enabled", False
        )

        logger.sync_info(
            f"{self.source_name} initialized with filtering",
            min_panels=self.min_panels,
            filtering_enabled=self.filtering_enabled,
        )

    def _get_default_ttl(self) -> int:
        """Get default TTL - manual uploads don't expire."""
        return 86400 * 365  # 1 year

    async def fetch_raw_data(
        self, tracker: "ProgressTracker | None" = None, mode: str = "smart"
    ) -> Any:
        """
        Not used for DiagnosticPanels - use parse_uploaded_file instead.

        This source receives file uploads rather than fetching from an API.
        """
        raise NotImplementedError(
            "DiagnosticPanels source uses parse_uploaded_file() for file uploads"
        )

    async def parse_uploaded_file(
        self,
        file_content: bytes,
        file_type: str,
        provider_name: str,
        tracker: "ProgressTracker | None" = None,
    ) -> pd.DataFrame:
        """
        Parse uploaded file and return DataFrame with provider metadata.

        Note: This method has a different signature from the base class
        fetch_raw_data because diagnostic panels are uploaded rather than
        fetched from an API.

        Args:
            file_content: Raw file bytes
            file_type: File extension (json, csv, tsv, xlsx, xls)
            provider_name: Name of the diagnostic provider
            tracker: Optional progress tracker

        Returns:
            DataFrame with gene panel data
        """
        logger.sync_info(
            "DiagnosticPanels.parse_uploaded_file START",
            file_type=file_type,
            provider_name=provider_name,
            content_size=len(file_content),
        )

        try:
            logger.sync_debug(f"Parsing {file_type} file")

            if file_type == "json":
                df = self._parse_json(file_content)
            elif file_type in ["csv", "tsv"]:
                df = self._parse_csv(file_content, file_type)
            elif file_type in ["xlsx", "xls"]:
                df = self._parse_excel(file_content)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            logger.sync_debug(
                "File parsed successfully",
                row_count=len(df),
                column_count=len(df.columns),
                columns=list(df.columns),
            )

            # Add provider metadata to each row
            df["provider"] = provider_name

            logger.sync_info(
                "DiagnosticPanels.parse_uploaded_file COMPLETE",
                entry_count=len(df),
                provider_name=provider_name,
            )
            return df

        except Exception as e:
            logger.sync_error(
                "Failed to parse file", provider_name=provider_name, error_detail=str(e)
            )
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
        logger.sync_info(
            "DiagnosticPanels.process_data START",
            row_count=len(df),
            has_provider=("provider" in df.columns),
        )

        gene_data: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: {"panels": set(), "providers": set(), "hgnc_ids": set()}
        )

        for idx, row in df.iterrows():
            try:
                # Extract gene symbol (handle multiple field names)
                symbol = self._extract_gene_symbol(row)
                if not symbol:
                    logger.sync_debug(f"No symbol found in row {idx}")
                    continue

                logger.sync_debug(f"Processing row {idx}", symbol=symbol)

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
                logger.sync_warning("Error processing row", row_index=idx, error_detail=str(e))
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

        total_panels = 0
        for d in result.values():
            panels_val = d["panels"]
            if isinstance(panels_val, list):
                total_panels += len(panels_val)
        all_providers: set[str] = set()
        for d in result.values():
            providers_val = d.get("providers", [])
            if isinstance(providers_val, list):
                all_providers.update(providers_val)
        logger.sync_info(
            "DiagnosticPanels.process_data COMPLETE",
            unique_gene_count=len(result),
            total_panels=total_panels,
            total_providers=len(all_providers),
        )
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
        self,
        db: Session,
        gene_data: dict[str, Any],
        source_detail: str | None = None,
        file_hash: str | None = None,
        original_filename: str | None = None,
        uploaded_by: int | None = None,
        mode: str = "merge",
    ) -> dict[str, Any]:
        """Store evidence with MERGE semantics and filtering for diagnostic panels."""

        logger.sync_info(
            "DiagnosticPanels.store_evidence START",
            gene_count=len(gene_data) if gene_data else 0,
            source_detail=source_detail,
            file_hash=file_hash,
            uploaded_by=uploaded_by,
            mode=mode,
        )

        if not gene_data:
            logger.sync_warning("No gene data provided to store_evidence")
            return {"merged": 0, "created": 0, "failed": 0, "filtered": 0}

        # Create upload record if tracking parameters provided
        from app.models.static_sources import StaticEvidenceUpload, StaticSource

        upload_record = None
        if file_hash:
            static_source = (
                db.query(StaticSource).filter(StaticSource.source_name == self.source_name).first()
            )

            if static_source:
                upload_record = StaticEvidenceUpload(
                    source_id=static_source.id,
                    file_name=original_filename or "unknown",
                    file_path=f"uploads/{self.source_name}/{original_filename or 'unknown'}",
                    evidence_name=source_detail or "unknown",
                    file_hash=file_hash,
                    original_filename=original_filename,
                    upload_status="processing",
                    uploaded_by=uploaded_by,
                    upload_metadata={"mode": mode},
                )
                db.add(upload_record)
                db.flush()  # Get upload.id

                logger.sync_info(
                    "Upload record created",
                    upload_id=upload_record.id,
                    provider=source_detail,
                )

        stats = {"merged": 0, "created": 0, "failed": 0, "filtered": 0}

        # Get gene IDs for all symbols
        gene_symbols = list(gene_data.keys())
        gene_map = {}

        logger.sync_debug(
            "Fetching gene IDs from database",
            symbol_count=len(gene_symbols),
            first_symbols=gene_symbols[:5] if gene_symbols else [],
        )

        # Batch fetch genes
        stmt = select(Gene).where(Gene.approved_symbol.in_(gene_symbols))
        genes = db.execute(stmt).scalars().all()
        gene_map = {g.approved_symbol: g.id for g in genes}

        logger.sync_debug(
            "Gene IDs fetched",
            found_count=len(gene_map),
            missing_count=len(gene_symbols) - len(gene_map),
        )

        # Get existing evidence for these genes
        gene_ids = list(gene_map.values())

        logger.sync_debug(
            "Fetching existing evidence", gene_id_count=len(gene_ids), source_name=self.source_name
        )

        stmt = select(GeneEvidence).where(
            GeneEvidence.gene_id.in_(gene_ids), GeneEvidence.source_name == self.source_name
        )
        existing_evidence = db.execute(stmt).scalars().all()
        existing_map = {e.gene_id: e for e in existing_evidence}

        logger.sync_debug(
            "Existing evidence fetched",
            existing_count=len(existing_map),
            new_count=len(gene_ids) - len(existing_map),
        )

        # Current provider from source_detail
        current_provider = source_detail or "unknown"

        # First pass: merge data in memory
        merged_gene_data = {}

        logger.sync_debug("Starting memory merge pass", total_genes=len(gene_data))

        for symbol, data in gene_data.items():
            gene_id = gene_map.get(symbol)
            if not gene_id:
                logger.sync_warning("Gene not found in database", symbol=symbol)
                stats["failed"] += 1
                continue

            if gene_id in existing_map:
                # MERGE: Prepare merged data
                record = existing_map[gene_id]
                current_data = record.evidence_data or {}

                # Merge panels and providers
                existing_panels = set(current_data.get("panels", []))
                new_panels = set(data["panels"])
                merged_panels = sorted(existing_panels | new_panels)

                existing_providers = set(current_data.get("providers", []))
                new_providers = {current_provider}
                merged_providers = sorted(existing_providers | new_providers)

                existing_hgnc = set(current_data.get("hgnc_ids", []))
                new_hgnc = set(data.get("hgnc_ids", []))
                merged_hgnc = sorted(existing_hgnc | new_hgnc)

                merged_data = {
                    "panels": merged_panels,
                    "providers": merged_providers,
                    "hgnc_ids": merged_hgnc,
                    "panel_count": len(merged_panels),
                    "provider_count": len(merged_providers),
                }

                merged_gene_data[symbol] = {
                    "gene_id": gene_id,
                    "data": merged_data,
                    "record": record,
                    "is_new": False,
                }

                logger.sync_debug(
                    "Merged existing gene",
                    symbol=symbol,
                    old_panels=len(existing_panels),
                    new_panels=len(new_panels),
                    total_panels=len(merged_panels),
                )
            else:
                # NEW: Prepare new data
                new_data = {
                    "panels": data["panels"],
                    "providers": [current_provider],
                    "hgnc_ids": data.get("hgnc_ids", []),
                    "panel_count": data["panel_count"],
                    "provider_count": 1,
                }

                merged_gene_data[symbol] = {
                    "gene_id": gene_id,
                    "data": new_data,
                    "record": None,
                    "is_new": True,
                }

                logger.sync_debug("Added new gene", symbol=symbol, panel_count=data["panel_count"])

        logger.sync_info(
            "Memory merge complete",
            total_genes=len(merged_gene_data),
            new_genes=sum(1 for info in merged_gene_data.values() if info["is_new"]),
            existing_genes=sum(1 for info in merged_gene_data.values() if not info["is_new"]),
        )

        # Apply filtering if enabled
        if self.filtering_enabled and self.min_panels > 1:
            logger.sync_info(
                "Applying filter",
                min_panels=self.min_panels,
                genes_before_filter=len(merged_gene_data),
            )
            # Extract data for filtering
            data_to_filter = {symbol: info["data"] for symbol, info in merged_gene_data.items()}

            filtered_data, filter_stats = apply_memory_filter(
                data_dict=data_to_filter,
                count_field="provider_count",
                min_threshold=self.min_panels,
                entity_name="providers",
                source_name=self.source_name,
                enabled=self.filtering_enabled,
            )

            # Handle filtered genes
            genes_to_remove = []
            for symbol, info in merged_gene_data.items():
                if symbol not in filtered_data:
                    if not info["is_new"] and info["record"]:
                        # Delete existing record that now fails filter
                        db.delete(info["record"])
                        logger.sync_info(
                            "Removing gene below threshold",
                            symbol=symbol,
                            provider_count=info["data"]["provider_count"],
                            threshold=self.min_panels,
                        )
                    genes_to_remove.append(symbol)
                    stats["filtered"] += 1

            # Remove filtered genes from processing
            for symbol in genes_to_remove:
                del merged_gene_data[symbol]

            logger.sync_info(
                "Filter applied",
                removed_count=len(genes_to_remove),
                remaining_count=len(merged_gene_data),
            )

            # Log filter statistics (metadata storage removed - method doesn't exist)
            logger.sync_info(
                "Filter statistics",
                source=self.source_name,
                filtered_count=filter_stats.filtered_count,
                filter_rate=f"{filter_stats.filter_rate:.1f}%",
            )

        # Process remaining genes (after filtering)
        logger.sync_info("Starting database updates", genes_to_process=len(merged_gene_data))

        for symbol, info in merged_gene_data.items():
            if info["is_new"]:
                # CREATE: New evidence record
                record = GeneEvidence(
                    gene_id=info["gene_id"],
                    source_name=self.source_name,
                    source_detail=self._get_source_detail(info["data"]),
                    evidence_data=info["data"],
                    evidence_date=datetime.now(timezone.utc).date(),
                )
                db.add(record)

                logger.sync_debug(
                    "Created evidence",
                    symbol=symbol,
                    panel_count=info["data"]["panel_count"],
                    provider=current_provider,
                )
                stats["created"] += 1
            else:
                # UPDATE: Existing record
                record = info["record"]
                record.evidence_data = info["data"]
                record.source_detail = self._get_source_detail(info["data"])
                record.evidence_date = datetime.now(timezone.utc).date()

                logger.sync_debug(
                    "Merged evidence",
                    symbol=symbol,
                    panel_count=info["data"]["panel_count"],
                    provider_count=info["data"]["provider_count"],
                )
                stats["merged"] += 1

        # Update upload record on completion
        if upload_record:
            upload_record.upload_status = "completed"
            upload_record.gene_count = len(gene_data)
            upload_record.genes_normalized = stats["created"] + stats["merged"]
            upload_record.genes_failed = stats["failed"]
            upload_record.processed_at = datetime.now(timezone.utc)

            logger.sync_info(
                "Upload record updated",
                upload_id=upload_record.id,
                stats=stats,
            )

        logger.sync_info(
            "DiagnosticPanels.store_evidence COMPLETE",
            created=stats["created"],
            merged=stats["merged"],
            failed=stats["failed"],
            filtered=stats["filtered"],
            total_processed=stats["created"] + stats["merged"],
        )

        return stats

    def _extract_panels(self, row: pd.Series) -> set[str]:
        """Extract panel names from row."""
        panels: set[str] = set()

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
