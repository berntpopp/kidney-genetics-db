"""
Mixin for annotation sources that support bulk file downloads.

Provides download, caching, decompression, parsing, and gene lookup
for sources that distribute data as downloadable flat files (TSV, CSV,
etc.) rather than per-gene API calls.

Usage::

    class GnomADUnifiedSource(BulkDataSourceMixin, UnifiedDataSource):
        bulk_file_url = "https://example.com/gnomad.tsv.gz"
        bulk_cache_ttl_hours = 168

        def parse_bulk_file(self, path: Path) -> dict[str, dict]:
            ...
"""

import asyncio
import gzip
import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)


class BulkDataSourceMixin:
    """
    Mixin that adds bulk-file download and lookup to a data source.

    Class attributes (override in subclasses):
        bulk_file_url: Remote URL of the bulk data file.
        bulk_cache_dir: Local directory for cached downloads.
        bulk_cache_ttl_hours: Hours before a cached file is stale.
        bulk_file_format: File extension used for the cached file.
    """

    bulk_file_url: str = ""
    bulk_cache_dir: Path = Path("data/bulk_cache")
    bulk_cache_ttl_hours: int = 168  # 7 days
    bulk_file_format: str = "tsv"
    bulk_file_min_size_bytes: int = 0  # 0 = no minimum size check

    _bulk_data: dict[str, dict[str, Any]] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def download_bulk_file(self, force: bool = False) -> Path:
        """Download and locally cache a bulk file from *bulk_file_url*.

        Uses a SHA-256 hash of the URL as part of the cache filename so
        different URLs never collide.  Re-downloads only when the local
        copy is stale or *force* is ``True``.

        Args:
            force: Re-download even if the cache is fresh.

        Returns:
            Path to the locally cached file.
        """
        cache_path = self._bulk_cache_path()
        self.bulk_cache_dir.mkdir(parents=True, exist_ok=True)

        if not force and self._is_bulk_cache_fresh(cache_path):
            logger.sync_debug(
                "Bulk cache is fresh, skipping download",
                url=self.bulk_file_url,
                path=str(cache_path),
            )
            return cache_path

        logger.sync_info(
            "Downloading bulk file",
            url=self.bulk_file_url,
            dest=str(cache_path),
        )

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            response = await client.get(self.bulk_file_url)
            response.raise_for_status()
            cache_path.write_bytes(response.content)

        logger.sync_info(
            "Bulk file downloaded",
            url=self.bulk_file_url,
            size_bytes=cache_path.stat().st_size,
        )
        self._write_bulk_meta(cache_path)
        return cache_path

    # Maximum retries for streaming downloads
    bulk_download_max_retries: int = 3

    async def download_bulk_file_streaming(self, force: bool = False) -> Path:
        """Download a large bulk file using streaming to avoid loading it into memory.

        Same cache-freshness logic as :meth:`download_bulk_file` but writes
        chunks to disk instead of buffering the full response.  Suitable for
        files >100 MB (e.g. ClinVar variant_summary.txt.gz at ~414 MB).

        Includes retry logic and partial-file cleanup for robustness on
        unreliable connections.

        Args:
            force: Re-download even if the cache is fresh.

        Returns:
            Path to the locally cached file.
        """
        cache_path = self._bulk_cache_path()
        self.bulk_cache_dir.mkdir(parents=True, exist_ok=True)

        if not force and self._is_bulk_cache_fresh(cache_path):
            logger.sync_debug(
                "Bulk cache is fresh, skipping download",
                url=self.bulk_file_url,
                path=str(cache_path),
            )
            return cache_path

        # Use generous timeouts: short connect, long read for large files
        timeout = httpx.Timeout(connect=30.0, read=900.0, write=30.0, pool=30.0)
        tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
        last_error: Exception | None = None

        for attempt in range(1, self.bulk_download_max_retries + 1):
            logger.sync_info(
                "Streaming download of bulk file",
                url=self.bulk_file_url,
                dest=str(cache_path),
                attempt=attempt,
            )
            try:
                bytes_written = 0
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    async with client.stream("GET", self.bulk_file_url) as response:
                        response.raise_for_status()
                        expected_size = response.headers.get("content-length")
                        with open(tmp_path, "wb") as fh:
                            async for chunk in response.aiter_bytes(chunk_size=65536):
                                fh.write(chunk)
                                bytes_written += len(chunk)

                # Validate completeness when Content-Length was provided
                if expected_size is not None:
                    expected = int(expected_size)
                    if bytes_written < expected:
                        msg = f"Incomplete download: got {bytes_written} bytes, expected {expected}"
                        raise httpx.TransportError(msg)

                # Atomic rename: only replace cache once download is fully complete
                tmp_path.replace(cache_path)
                logger.sync_info(
                    "Bulk file downloaded (streaming)",
                    url=self.bulk_file_url,
                    size_bytes=cache_path.stat().st_size,
                )
                self._write_bulk_meta(cache_path)
                return cache_path

            except (httpx.TransportError, httpx.HTTPStatusError, OSError) as exc:
                last_error = exc
                # Clean up partial file
                if tmp_path.exists():
                    tmp_path.unlink()
                if attempt < self.bulk_download_max_retries:
                    wait = 2**attempt  # 2, 4 seconds
                    logger.sync_warning(
                        "Streaming download failed, retrying",
                        url=self.bulk_file_url,
                        attempt=attempt,
                        wait_seconds=wait,
                        error=str(exc),
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.sync_error(
                        "Streaming download failed after all retries",
                        url=self.bulk_file_url,
                        attempts=self.bulk_download_max_retries,
                        error=str(exc),
                    )

        raise last_error  # type: ignore[misc]

    def parse_bulk_file(self, path: Path) -> dict[str, dict]:
        """Parse a downloaded bulk file into a gene-keyed dict.

        Subclasses **must** override this method to handle their
        specific file format.

        Args:
            path: Path to the downloaded (and possibly decompressed)
                  bulk data file.

        Returns:
            Mapping of gene key (e.g. symbol or HGNC ID) to annotation
            dict.

        Raises:
            NotImplementedError: Always, unless overridden.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement parse_bulk_file()")

    async def ensure_bulk_data_loaded(self, force: bool = False) -> None:
        """Download, decompress, parse, and cache bulk data in memory.

        After this method returns, ``self._bulk_data`` contains the
        parsed gene dict and :meth:`lookup_gene` is ready to use.

        Args:
            force: Force re-download and re-parse.
        """
        if self._bulk_data is not None and not force:
            return

        raw_path = await self.download_bulk_file(force=force)

        # Decompress .gz files to a sibling path
        parse_path = raw_path
        if raw_path.suffix == ".gz":
            decompressed = raw_path.with_suffix("")
            logger.sync_info(
                "Decompressing bulk file",
                src=str(raw_path),
                dest=str(decompressed),
            )
            with gzip.open(raw_path, "rb") as f_in:
                with open(decompressed, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            parse_path = decompressed

        self._bulk_data = self.parse_bulk_file(parse_path)
        logger.sync_info(
            "Bulk data loaded",
            gene_count=len(self._bulk_data),
            source=getattr(self, "source_name", self.__class__.__name__),
        )

    def lookup_gene(self, gene_key: str) -> dict | None:
        """Return annotation data for *gene_key*, or ``None``.

        Args:
            gene_key: Gene symbol or identifier used as key in the
                      parsed bulk data.

        Returns:
            Annotation dict if found, else ``None``.
        """
        if self._bulk_data is None:
            return None
        return self._bulk_data.get(gene_key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_bulk_cache_fresh(self, cache_path: Path) -> bool:
        """Check whether *cache_path* exists, is younger than TTL, and is complete.

        Validates:
        1. File exists and is within TTL.
        2. File size matches the sidecar metadata (written after successful download).
        3. File size meets ``bulk_file_min_size_bytes`` if set.

        Args:
            cache_path: Path to the cached file.

        Returns:
            ``True`` if the file passes all checks.
        """
        if not cache_path.exists():
            return False

        file_size = cache_path.stat().st_size
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600.0

        if age_hours >= self.bulk_cache_ttl_hours:
            return False

        # Check minimum size guard
        if self.bulk_file_min_size_bytes > 0 and file_size < self.bulk_file_min_size_bytes:
            logger.sync_warning(
                "Cached bulk file below minimum expected size, treating as stale",
                path=str(cache_path),
                file_size=file_size,
                min_expected=self.bulk_file_min_size_bytes,
            )
            return False

        # Check sidecar metadata for exact size match
        meta_path = self._bulk_meta_path(cache_path)
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                expected_size = meta.get("size_bytes", 0)
                if expected_size and file_size != expected_size:
                    logger.sync_warning(
                        "Cached bulk file size mismatch (possible truncation), treating as stale",
                        path=str(cache_path),
                        file_size=file_size,
                        expected_size=expected_size,
                    )
                    return False
            except (json.JSONDecodeError, OSError):
                pass  # Corrupt meta file, ignore — other checks still apply

        return True

    def _write_bulk_meta(self, cache_path: Path) -> None:
        """Write a sidecar metadata file recording the size of a successful download."""
        meta_path = self._bulk_meta_path(cache_path)
        try:
            meta_path.write_text(
                json.dumps({"size_bytes": cache_path.stat().st_size, "ts": time.time()})
            )
        except OSError as exc:
            logger.sync_warning("Could not write bulk meta file", error=str(exc))

    @staticmethod
    def _bulk_meta_path(cache_path: Path) -> Path:
        return cache_path.with_suffix(cache_path.suffix + ".meta")

    def _bulk_cache_path(self) -> Path:
        """Derive the local cache file path from *bulk_file_url*.

        Uses a truncated SHA-256 of the URL so different URLs get
        different cache files.
        """
        url_hash = hashlib.sha256(self.bulk_file_url.encode()).hexdigest()[:16]
        filename = f"bulk_{url_hash}.{self.bulk_file_format}"
        return self.bulk_cache_dir / filename
