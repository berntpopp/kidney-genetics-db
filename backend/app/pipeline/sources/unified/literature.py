"""
Unified Literature data source implementation.

This module provides a hybrid source that accepts file uploads for literature-based
gene data and properly aggregates evidence across multiple publications.
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


class LiteratureSource(UnifiedDataSource):
    """
    Hybrid data source for literature-based gene data.

    This source accepts file uploads (JSON, CSV, Excel) containing literature
    gene information and properly aggregates data across multiple publications.

    Key features:
    - Supports multiple file formats
    - Aggregates publications per gene
    - Merges evidence on re-upload (no duplicates)
    - Stores publication metadata
    """

    @property
    def source_name(self) -> str:
        return "Literature"

    @property
    def namespace(self) -> str:
        return "literature"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | None = None,
        **kwargs,
    ):
        """Initialize literature source."""
        super().__init__(cache_service, http_client, db_session, **kwargs)
        logger.sync_info("LiteratureSource initialized")

    def _get_default_ttl(self) -> int:
        """Get default TTL - manual uploads don't expire."""
        return 86400 * 365  # 1 year

    async def fetch_raw_data(
        self,
        file_content: bytes,
        file_type: str,
        publication_id: str,
        tracker: "ProgressTracker" = None,
    ) -> pd.DataFrame:
        """
        Parse uploaded file and return DataFrame with publication metadata.

        Args:
            file_content: Raw file bytes
            file_type: File extension (json, csv, tsv, xlsx, xls)
            publication_id: Publication identifier (e.g., PMID)
            tracker: Optional progress tracker

        Returns:
            DataFrame with gene publication data
        """
        logger.sync_info(
            "Processing literature file", file_type=file_type, publication_id=publication_id
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

            # Add publication identifier to each row
            df["publication_id"] = publication_id

            logger.sync_info(
                "Parsed gene entries", entry_count=len(df), publication_id=publication_id
            )
            return df

        except Exception as e:
            logger.sync_error(
                "Failed to parse literature file", publication_id=publication_id, error=str(e)
            )
            raise

    def _parse_json(self, content: bytes) -> pd.DataFrame:
        """Parse JSON file format (handles literature scraper output)."""
        data = json.loads(content)

        if isinstance(data, dict):
            # Literature scraper output format - extract publication metadata and genes
            if "genes" in data:
                # Create records with both gene and publication data
                records = []
                pub_metadata = {k: v for k, v in data.items() if k not in ["genes"]}

                for gene in data["genes"]:
                    record = {**gene, **pub_metadata}
                    records.append(record)

                return pd.DataFrame(records)
            else:
                # Simple gene list
                return pd.DataFrame(data)
        elif isinstance(data, list):
            return pd.DataFrame(data)
        else:
            raise ValueError(f"Invalid JSON structure: expected dict or list, got {type(data)}")

    def _parse_csv(self, content: bytes, file_type: str) -> pd.DataFrame:
        """Parse CSV or TSV file."""
        sep = "\t" if file_type == "tsv" else ","
        return pd.read_csv(BytesIO(content), sep=sep)

    def _parse_excel(self, content: bytes) -> pd.DataFrame:
        """Parse Excel file."""
        return pd.read_excel(BytesIO(content))

    async def process_data(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Process DataFrame and aggregate publication data by gene.

        Args:
            df: DataFrame with gene publication data

        Returns:
            Dictionary mapping gene symbols to aggregated evidence
        """
        gene_data = defaultdict(
            lambda: {"publications": set(), "publication_details": {}, "hgnc_ids": set()}
        )

        for idx, row in df.iterrows():
            try:
                # Extract gene symbol
                symbol = self._extract_gene_symbol(row)
                if not symbol:
                    continue

                # Track publication ID
                if "publication_id" in row.index:
                    pub_id = str(row["publication_id"])
                    gene_data[symbol]["publications"].add(pub_id)

                # Extract and store publication metadata
                pub_details = self._extract_publication_metadata(row)
                if pub_details:
                    gene_data[symbol]["publication_details"].update(pub_details)

                # Track HGNC ID if available
                if "hgnc_id" in row.index:
                    hgnc_val = row["hgnc_id"]
                    if hgnc_val is not None and not isinstance(hgnc_val, list | dict):
                        gene_data[symbol]["hgnc_ids"].add(str(hgnc_val))

            except Exception as e:
                logger.sync_warning("Error processing literature row", row_index=idx, error=str(e))
                continue

        # Convert to serializable format
        result = {}
        for symbol, data in gene_data.items():
            result[symbol] = {
                "publications": sorted(data["publications"]),
                "publication_details": data["publication_details"],
                "publication_count": len(data["publications"]),
                "hgnc_ids": sorted(data["hgnc_ids"]),
            }

        logger.sync_info("Processed unique genes from literature", unique_gene_count=len(result))
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
        """Generate source detail string for literature evidence."""
        pub_count = evidence_data.get("publication_count", 0)
        publications = evidence_data.get("publications", [])

        if pub_count == 1 and publications:
            pub_id = publications[0]
            pub_details = evidence_data.get("publication_details", {})
            if pub_id in pub_details:
                title = pub_details[pub_id].get("title", "Unknown")
                journal = pub_details[pub_id].get("journal", "Unknown Journal")
                return f"Literature: {title[:50]}... ({journal})"

        return f"Literature: {pub_count} publications"

    async def store_evidence(
        self, db: Session, gene_data: dict[str, Any], source_detail: str | None = None
    ) -> dict[str, Any]:
        """Store evidence with MERGE semantics for literature sources."""

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

        # Current publication from source_detail
        current_publication = source_detail or "unknown"

        # Process each gene
        for symbol, data in gene_data.items():
            gene_id = gene_map.get(symbol)
            if not gene_id:
                logger.sync_warning("Gene not found in database", symbol=symbol)
                stats["failed"] += 1
                continue

            if gene_id in existing_map:
                # MERGE: Update existing evidence
                record = existing_map[gene_id]
                current_data = record.evidence_data or {}

                # Merge publications
                existing_pubs = set(current_data.get("publications", []))
                new_pubs = {current_publication}
                merged_pubs = list(existing_pubs | new_pubs)

                # Merge publication details
                existing_details = current_data.get("publication_details", {})
                new_details = data.get("publication_details", {})
                merged_details = {**existing_details, **new_details}

                # Merge HGNC IDs
                existing_hgnc = set(current_data.get("hgnc_ids", []))
                new_hgnc = set(data.get("hgnc_ids", []))
                merged_hgnc = list(existing_hgnc | new_hgnc)

                # Update evidence with merged data
                record.evidence_data = {
                    "publications": merged_pubs,
                    "publication_count": len(merged_pubs),
                    "publication_details": merged_details,
                    "hgnc_ids": merged_hgnc,
                    "evidence_score": len(merged_pubs) * 5.0,  # 5 points per publication
                }
                record.source_detail = self._get_source_detail(record.evidence_data)
                record.evidence_date = datetime.now(timezone.utc).date()

                logger.sync_debug(
                    "Merged literature evidence", symbol=symbol, publication_count=len(merged_pubs)
                )
                stats["merged"] += 1

            else:
                # CREATE: New evidence record
                record = GeneEvidence(
                    gene_id=gene_id,
                    source_name=self.source_name,
                    source_detail=self._get_source_detail(data),
                    evidence_data={
                        "publications": [current_publication],
                        "publication_count": 1,
                        "publication_details": data.get("publication_details", {}),
                        "hgnc_ids": data.get("hgnc_ids", []),
                        "evidence_score": 5.0,  # 5 points per publication
                    },
                    evidence_date=datetime.now(timezone.utc).date(),
                )
                db.add(record)

                logger.sync_debug(
                    "Created literature evidence", symbol=symbol, publication=current_publication
                )
                stats["created"] += 1

        return stats

    def _extract_publication_metadata(self, row: pd.Series) -> dict[str, dict]:
        """Extract publication metadata from row."""
        metadata = {}

        if "publication_id" in row.index and row["publication_id"] is not None:
            pub_id = str(row["publication_id"])

            # Extract available publication fields
            pub_data = {}
            pub_fields = {
                "pmid": "pmid",
                "title": "title",
                "authors": "authors",
                "journal": "journal",
                "publication_date": "publication_date",
                "url": "url",
                "doi": "doi",
            }

            for field_key, field_name in pub_fields.items():
                if field_name in row.index and row[field_name] is not None:
                    value = row[field_name]
                    # Handle authors list specially
                    if field_name == "authors" and isinstance(value, list):
                        pub_data[field_key] = value
                    elif not isinstance(value, list | dict):
                        pub_data[field_key] = str(value)

            if pub_data:
                metadata[pub_id] = pub_data

        return metadata

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        """All manually uploaded literature data is considered kidney-related."""
        return True
