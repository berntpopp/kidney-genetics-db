"""
HGNC annotation source for gene annotations.

Supports bulk JSON download of the complete HGNC dataset for fast batch
processing, with REST API fallback for individual lookups.
"""

import json
from pathlib import Path
from typing import Any, cast

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

logger = get_logger(__name__)


class HGNCAnnotationSource(BulkDataSourceMixin, BaseAnnotationSource):
    """
    HGNC (HUGO Gene Nomenclature Committee) annotation source.

    Uses bulk JSON download of the complete HGNC dataset for fast batch
    processing. Falls back to REST API for individual lookups.
    """

    source_name = "hgnc"
    display_name = "HGNC"
    version = "2024.01"

    # API configuration (fallback)
    base_url = "https://rest.genenames.org"
    headers = {"Accept": "application/json", "User-Agent": "KidneyGeneticsDB/1.0"}

    # Cache configuration
    cache_ttl_days = 90

    # Bulk download configuration
    bulk_file_url = (
        "https://storage.googleapis.com/public-download-files"
        "/hgnc/json/json/hgnc_complete_set.json"
    )
    bulk_cache_ttl_hours = 168  # 7 days
    bulk_file_format = "json"

    def parse_bulk_file(self, path: Path) -> dict[str, dict[str, Any]]:
        """Parse HGNC complete set JSON into gene-keyed dict.

        Uses ``_extract_annotations()`` to produce identical field names
        as the REST API path, ensuring data parity.
        """
        with open(path) as f:
            raw = json.load(f)

        docs = raw.get("response", {}).get("docs", [])
        data: dict[str, dict[str, Any]] = {}

        for doc in docs:
            symbol = doc.get("symbol", "").strip()
            if not symbol:
                continue
            data[symbol] = self._extract_annotations(doc)

        return data

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch HGNC annotation for a single gene.

        Tries bulk data first, then falls back to REST API.
        """
        # Try bulk lookup by symbol
        if self._bulk_data is not None and gene.approved_symbol:
            bulk_result = self.lookup_gene(gene.approved_symbol)
            if bulk_result is not None:
                return bulk_result

        # Fall back to REST API
        return await self._fetch_via_api(gene)

    async def _fetch_via_api(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch HGNC data via REST API (original implementation)."""
        hgnc_data = None

        if gene.hgnc_id:
            hgnc_data = await self._fetch_by_hgnc_id(gene.hgnc_id)

        if not hgnc_data and gene.approved_symbol:
            hgnc_data = await self._fetch_by_symbol(gene.approved_symbol)

        if not hgnc_data:
            logger.sync_warning(
                "No HGNC data found for gene",
                gene_symbol=gene.approved_symbol,
                hgnc_id=gene.hgnc_id,
            )
            return None

        return self._extract_annotations(hgnc_data)

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def _fetch_by_hgnc_id(self, hgnc_id: str) -> dict[str, Any] | None:
        """Fetch HGNC data by HGNC ID."""
        clean_id = hgnc_id.replace("HGNC:", "")

        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            response = await client.get(
                f"{self.base_url}/fetch/hgnc_id/{clean_id}", headers=self.headers, timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("response", {}).get("docs"):
                    return cast(dict[str, Any], data["response"]["docs"][0])

        except Exception as e:
            logger.sync_error(f"Error fetching HGNC by ID: {str(e)}", hgnc_id=hgnc_id)
            raise

        return None

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def _fetch_by_symbol(self, symbol: str) -> dict[str, Any] | None:
        """Fetch HGNC data by gene symbol."""
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            response = await client.get(
                f"{self.base_url}/fetch/symbol/{symbol}", headers=self.headers, timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("response", {}).get("docs"):
                    return cast(dict[str, Any], data["response"]["docs"][0])

        except Exception as e:
            logger.sync_error(f"Error fetching HGNC by symbol: {str(e)}", symbol=symbol)
            raise

        return None

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def _fetch_by_ensembl_id(self, ensembl_id: str) -> dict[str, Any] | None:
        """Fetch HGNC data by Ensembl gene ID."""
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            response = await client.get(
                f"{self.base_url}/fetch/ensembl_gene_id/{ensembl_id}",
                headers=self.headers,
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("response", {}).get("docs"):
                    return cast(dict[str, Any], data["response"]["docs"][0])

        except Exception as e:
            logger.sync_error(f"Error fetching HGNC by Ensembl ID: {str(e)}", ensembl_id=ensembl_id)
            raise

        return None

    def _extract_annotations(self, hgnc_data: dict) -> dict[str, Any]:
        """Extract relevant annotations from HGNC data (API or bulk)."""
        annotations = {
            "hgnc_id": hgnc_data.get("hgnc_id"),
            "symbol": hgnc_data.get("symbol"),
            "name": hgnc_data.get("name"),
            "status": hgnc_data.get("status"),
            "ncbi_gene_id": hgnc_data.get("entrez_id"),
            "ensembl_gene_id": hgnc_data.get("ensembl_gene_id"),
            "omim_ids": hgnc_data.get("omim_id", []),
            "orphanet_id": hgnc_data.get("orphanet"),
            "cosmic_id": hgnc_data.get("cosmic"),
            "refseq_accession": hgnc_data.get("refseq_accession", []),
            "mane_select": self._parse_mane_select(hgnc_data.get("mane_select", [])),
            "locus_type": hgnc_data.get("locus_type"),
            "locus_group": hgnc_data.get("locus_group"),
            "location": hgnc_data.get("location"),
            "location_sortable": hgnc_data.get("location_sortable"),
            "alias_symbol": hgnc_data.get("alias_symbol", []),
            "alias_name": hgnc_data.get("alias_name", []),
            "prev_symbol": hgnc_data.get("prev_symbol", []),
            "prev_name": hgnc_data.get("prev_name", []),
            "gene_family": hgnc_data.get("gene_family", []),
            "gene_family_id": hgnc_data.get("gene_family_id", []),
            "pubmed_ids": hgnc_data.get("pubmed_id", []),
            "date_approved_reserved": hgnc_data.get("date_approved_reserved"),
            "date_modified": hgnc_data.get("date_modified"),
            "date_name_changed": hgnc_data.get("date_name_changed"),
            "date_symbol_changed": hgnc_data.get("date_symbol_changed"),
            "uuid": hgnc_data.get("uuid"),
            "_version_": hgnc_data.get("_version_"),
        }

        return {k: v for k, v in annotations.items() if v is not None}

    def _parse_mane_select(self, mane_select_list: list) -> dict | None:
        """Parse MANE Select transcript information."""
        if not mane_select_list or len(mane_select_list) < 2:
            return None

        ensembl_transcript = None
        refseq_transcript = None

        for item in mane_select_list:
            if item.startswith("ENST"):
                ensembl_transcript = item
            elif item.startswith("NM_") or item.startswith("NR_"):
                refseq_transcript = item

        if ensembl_transcript or refseq_transcript:
            return {
                "ensembl_transcript_id": ensembl_transcript,
                "refseq_transcript_id": refseq_transcript,
            }

        return None

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """Fetch annotations for multiple genes.

        Loads bulk data once, then does fast local lookups. Falls back to
        REST API for genes not found in the bulk file.
        """
        import asyncio

        # Load bulk data if not already loaded
        try:
            await self.ensure_bulk_data_loaded()
        except Exception as e:
            logger.sync_warning(
                f"Failed to load HGNC bulk data, falling back to API: {e}",
            )

        results: dict[int, dict[str, Any]] = {}
        api_fallback_genes: list[Gene] = []

        # Fast bulk lookups
        for gene in genes:
            if self._bulk_data is not None and gene.approved_symbol:
                bulk_result = self.lookup_gene(gene.approved_symbol)
                if bulk_result is not None:
                    results[gene.id] = bulk_result
                    continue
            api_fallback_genes.append(gene)

        if api_fallback_genes:
            logger.sync_info(
                "HGNC bulk miss, falling back to API",
                bulk_hits=len(results),
                api_fallback=len(api_fallback_genes),
            )

            # API fallback with async parallelism
            tasks = [self._fetch_via_api(gene) for gene in api_fallback_genes]
            annotations = await asyncio.gather(*tasks, return_exceptions=True)

            for gene, annotation in zip(api_fallback_genes, annotations, strict=False):
                if annotation and not isinstance(annotation, BaseException):
                    results[gene.id] = annotation
                elif isinstance(annotation, BaseException):
                    logger.sync_error(
                        "Error fetching annotation for gene",
                        gene_symbol=gene.approved_symbol,
                        error=str(annotation),
                    )

        return results

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def search_genes(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for genes in HGNC by query string."""
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            response = await client.get(
                f"{self.base_url}/search/{query}",
                headers=self.headers,
                params={"rows": limit},
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                docs = data.get("response", {}).get("docs", [])
                return cast(list[dict[str, Any]], docs)

        except Exception as e:
            logger.sync_error(f"Error searching HGNC: {str(e)}", query=query)
            raise

        return []
