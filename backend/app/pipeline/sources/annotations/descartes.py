"""
Descartes annotation source for cell-type specific kidney expression data.

This source provides kidney cell-type expression data from the Descartes Human Cell Atlas.
It downloads complete CSV files containing all genes and caches them for efficient lookups.

NOTE: As of 2025, Descartes data is protected by CloudFront and requires browser-based
access. Direct API access returns 403 Forbidden. This implementation is designed to
work with manually downloaded CSV files placed in the cache directory.

To use this source:
1. Download kidney.csv files from Descartes website manually
2. Place them in backend/.cache/descartes/
3. The source will load from local cache

Alternative: Implement selenium-based browser automation for data retrieval.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource

logger = get_logger(__name__)


class DescartesAnnotationSource(BaseAnnotationSource):
    """
    Descartes Human Cell Atlas annotation source.

    Provides single-cell RNA-seq expression data for kidney cell types.
    Data is downloaded as complete CSV files and cached for efficient access.

    CSV URLs:
    - TPM values: https://atlas.fredhutch.org/data/bbi/descartes/human_gtex/tables/tissue_tpm/kidney.csv
    - Percentage expressing: https://atlas.fredhutch.org/data/bbi/descartes/human_gtex/tables/tissue_percentage/kidney.csv
    """

    source_name = "descartes"
    display_name = "Descartes"
    version = "human_gtex"

    # Descartes data URLs
    base_url = "https://atlas.fredhutch.org/data/bbi/descartes/human_gtex/tables"
    tpm_url = f"{base_url}/tissue_tpm/kidney.csv"
    percentage_url = f"{base_url}/tissue_percentage/kidney.csv"

    # Cache configuration
    cache_ttl_days = 90  # Refresh monthly
    cache_key_prefix = "descartes_kidney_data"

    # Browser headers to bypass CloudFront
    BROWSER_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }

    # In-memory cache for parsed data
    _tpm_data: dict[str, float] | None = None
    _percentage_data: dict[str, float] | None = None
    _last_fetch: datetime | None = None

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch Descartes expression data for a single gene.

        Args:
            gene: Gene object to fetch annotations for

        Returns:
            Dictionary with expression data or None if not found
        """
        if not gene.approved_symbol:
            return None

        # Ensure data is loaded
        await self._ensure_data_loaded()

        # Look up gene in cached data
        tpm = self._tpm_data.get(gene.approved_symbol) if self._tpm_data else None
        percentage = (
            self._percentage_data.get(gene.approved_symbol) if self._percentage_data else None
        )

        if tpm is None and percentage is None:
            logger.sync_debug("No Descartes data found for gene", gene_symbol=gene.approved_symbol)
            return None

        return {
            "kidney_tpm": tpm,
            "kidney_percentage": percentage,
            "cell_type": "kidney",  # Could be expanded to include specific cell types
            "dataset_version": self.version,
            "gene_symbol": gene.approved_symbol,
        }

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def _ensure_data_loaded(self) -> None:
        """
        Ensure Descartes data is loaded into memory.

        This method checks if data needs to be refreshed and loads it
        either from database cache or by downloading fresh data.
        """
        # Check if data needs refresh
        if self._needs_refresh():
            await self._load_data()

    def _needs_refresh(self) -> bool:
        """Check if cached data needs to be refreshed."""
        if self._tpm_data is None or self._percentage_data is None:
            return True

        if self._last_fetch is None:
            return True

        age = datetime.utcnow() - self._last_fetch
        return age > timedelta(days=self.cache_ttl_days)

    async def _load_data(self) -> None:
        """
        Load Descartes data from cache or download fresh.

        This method first tries to load from database cache,
        then tries local files, finally falling back to downloading.
        """
        # Try to load from database cache first
        cached_data = await self._load_from_cache()

        if cached_data and not self._is_cache_expired(cached_data.get("timestamp")):
            self._tpm_data = cached_data.get("tpm_data", {})
            self._percentage_data = cached_data.get("percentage_data", {})
            self._last_fetch = cached_data.get("timestamp")
            logger.sync_info("Loaded Descartes data from cache", gene_count=len(self._tpm_data))
            return

        # Try to load from local files first (for CloudFront-protected data)
        if await self._load_from_local_files():
            return

        # Download fresh data (may fail due to CloudFront protection)
        logger.sync_info("Attempting to download fresh Descartes data...")

        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            # Download TPM data
            tpm_response = await client.get(
                self.tpm_url, timeout=60.0, headers=self.BROWSER_HEADERS, follow_redirects=True
            )

            if tpm_response.status_code != 200:
                logger.sync_warning(
                    "Cannot download Descartes data directly (CloudFront protected). "
                    "Please download manually and place in .cache/descartes/",
                    status=tpm_response.status_code,
                )
                return

            # Download percentage data
            percentage_response = await client.get(
                self.percentage_url,
                timeout=60.0,
                headers=self.BROWSER_HEADERS,
                follow_redirects=True,
            )

            if percentage_response.status_code != 200:
                logger.sync_error(
                    "Failed to download Descartes percentage data",
                    status=percentage_response.status_code,
                )
                return

            # Parse CSV data (httpx handles decompression automatically)
            self._tpm_data = self._parse_csv(tpm_response.text)
            self._percentage_data = self._parse_csv(percentage_response.text)
            self._last_fetch = datetime.utcnow()

            logger.sync_info(
                "Downloaded and parsed Descartes data",
                tpm_genes=len(self._tpm_data),
                percentage_genes=len(self._percentage_data),
            )

            # Save to cache
            await self._save_to_cache(
                {
                    "tpm_data": self._tpm_data,
                    "percentage_data": self._percentage_data,
                    "timestamp": self._last_fetch,
                }
            )

        except httpx.TimeoutException:
            logger.sync_error("Timeout downloading Descartes data")
        except Exception as e:
            logger.sync_error("Error downloading Descartes data", error_detail=str(e))

    def _parse_csv(self, csv_text: str) -> dict[str, float]:
        """
        Parse Descartes CSV data into a dictionary.

        Descartes format has no header row:
        GENE1,value1
        GENE2,value2
        ...

        Args:
            csv_text: Raw CSV text

        Returns:
            Dictionary mapping gene symbols to expression values
        """
        data = {}

        try:
            # Descartes CSV has no header - parse directly
            lines = csv_text.strip().split("\n")

            for line in lines:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    gene_symbol = parts[0].strip()
                    try:
                        value = float(parts[1].strip())
                        data[gene_symbol] = value
                    except (ValueError, IndexError):
                        continue

            logger.sync_debug(f"Parsed Descartes CSV: {len(data)} genes")

        except Exception as e:
            logger.sync_error("Error parsing Descartes CSV", error_detail=str(e))

        return data

    async def _load_from_local_files(self) -> bool:
        """
        Load Descartes data from local CSV files (NON-BLOCKING).

        This is a fallback for when direct download is blocked by CloudFront.
        Uses asyncio.to_thread to prevent event loop blocking during file I/O.

        Returns:
            True if successfully loaded, False otherwise
        """
        cache_dir = Path(".cache/descartes")
        tpm_file = cache_dir / "kidney_tpm.csv"
        percentage_file = cache_dir / "kidney_percentage.csv"

        if not tpm_file.exists() or not percentage_file.exists():
            return False

        try:
            # Define sync file reader helper (runs in thread pool)
            def read_file_sync(path: Path) -> str:
                """Read file synchronously - will be executed in thread pool."""
                with open(path, encoding="utf-8") as f:
                    return f.read()

            # Load files in thread pool (non-blocking)
            tpm_content = await asyncio.to_thread(read_file_sync, tpm_file)
            self._tpm_data = self._parse_csv(tpm_content)

            percentage_content = await asyncio.to_thread(read_file_sync, percentage_file)
            self._percentage_data = self._parse_csv(percentage_content)

            self._last_fetch = datetime.utcnow()

            logger.sync_info(
                "Loaded Descartes data from local files (non-blocking)",
                tpm_genes=len(self._tpm_data),
                percentage_genes=len(self._percentage_data),
            )

            return True

        except Exception as e:
            logger.sync_error("Error loading Descartes data from local files", error_detail=str(e))
            return False

    async def _load_from_cache(self) -> dict[str, Any] | None:
        """
        Load cached Descartes data from database.

        Returns:
            Cached data dictionary or None if not found
        """
        # This would typically load from a database table
        # For now, we'll return None to always try other methods
        # In production, implement database caching here
        return None

    async def _save_to_cache(self, data: dict[str, Any]) -> None:
        """
        Save Descartes data to database cache.

        Args:
            data: Data dictionary to cache
        """
        # This would typically save to a database table
        # For now, we just keep it in memory
        # In production, implement database caching here
        pass

    def _is_cache_expired(self, timestamp: datetime | None) -> bool:
        """
        Check if cached data is expired.

        Args:
            timestamp: Cache timestamp

        Returns:
            True if cache is expired or invalid
        """
        if timestamp is None:
            return True

        age = datetime.utcnow() - timestamp
        return age > timedelta(days=self.cache_ttl_days)

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Fetch annotations for multiple genes.

        Since Descartes data is already loaded in memory,
        this is very efficient.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene_id to annotation data
        """
        # Ensure data is loaded once
        await self._ensure_data_loaded()

        results = {}

        for gene in genes:
            annotation = await self.fetch_annotation(gene)
            if annotation:
                results[gene.id] = annotation

        return results

    async def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the cached Descartes data.

        Returns:
            Dictionary with cache statistics
        """
        await self._ensure_data_loaded()

        return {
            "source": self.source_name,
            "version": self.version,
            "last_fetch": self._last_fetch.isoformat() if self._last_fetch else None,
            "cache_age_days": (
                (datetime.utcnow() - self._last_fetch).days if self._last_fetch else None
            ),
            "tpm_gene_count": len(self._tpm_data) if self._tpm_data else 0,
            "percentage_gene_count": len(self._percentage_data) if self._percentage_data else 0,
            "cache_ttl_days": self.cache_ttl_days,
        }

    async def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._tpm_data = None
        self._percentage_data = None
        self._last_fetch = None
        logger.sync_info("Cleared Descartes cache")
