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
        logger.sync_info("Processing literature file", file_type=file_type, publication_id=publication_id)

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

            logger.sync_info("Parsed gene entries", entry_count=len(df), publication_id=publication_id)
            return df

        except Exception as e:
            logger.sync_error("Failed to parse literature file", publication_id=publication_id, error=str(e))
            raise

    def _parse_json(self, content: bytes) -> pd.DataFrame:
        """Parse JSON file format (handles literature scraper output)."""
        data = json.loads(content)
        
        if isinstance(data, dict):
            # Literature scraper output format - extract publication metadata and genes
            if "genes" in data:
                # Create records with both gene and publication data
                records = []
                pub_metadata = {
                    k: v for k, v in data.items() 
                    if k not in ["genes"]
                }
                
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
        gene_data = defaultdict(lambda: {
            "publications": set(), 
            "publication_details": {}, 
            "hgnc_ids": set()
        })

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
                "doi": "doi"
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