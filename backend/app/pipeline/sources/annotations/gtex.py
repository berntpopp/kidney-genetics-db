"""
GTEx annotation source for gene expression data.

Supports bulk GCT download of median gene expression for fast batch
processing, with GTEx Portal API fallback for genes not in the bulk file.
"""

import csv
from pathlib import Path
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

logger = get_logger(__name__)


class GTExAnnotationSource(BulkDataSourceMixin, BaseAnnotationSource):
    """
    GTEx (Genotype-Tissue Expression) annotation source.

    Uses bulk GCT download of median gene expression for fast batch processing.
    Falls back to GTEx Portal API for genes not found in the bulk file.
    """

    source_name = "gtex"
    display_name = "GTEx"
    version = "v8"

    # API configuration (fallback)
    base_url = "https://gtexportal.org/api/v2"
    headers = {"Accept": "application/json", "User-Agent": "KidneyGeneticsDB/1.0"}

    # Cache configuration
    cache_ttl_days = 90

    # Bulk download configuration
    # GTEx v8 median gene-level TPM across all tissues (~7 MB gzipped)
    bulk_file_url = (
        "https://storage.googleapis.com/adult-gtex/bulk-gex/v8/rna-seq"
        "/GTEx_Analysis_2017-06-05_v8_RNASeQCv1.1.9_gene_median_tpm.gct.gz"
    )
    bulk_cache_ttl_hours = 168  # 7 days
    bulk_file_format = "gct.gz"

    def parse_bulk_file(self, path: Path) -> dict[str, dict[str, Any]]:
        """Parse GTEx median gene expression GCT into gene-keyed dict.

        GCT v1.2 format:
          Line 1: #1.2
          Line 2: num_genes<tab>num_tissues
          Line 3: Name<tab>Description<tab>tissue1<tab>tissue2<tab>...
          Line 4+: gencode_id<tab>gene_symbol<tab>tpm1<tab>tpm2<tab>...

        Field names match the output of ``_fetch_by_symbol()`` for data parity.
        """
        data: dict[str, dict[str, Any]] = {}

        with open(path, newline="") as f:
            # Skip GCT header lines
            line1 = f.readline().strip()
            if not line1.startswith("#1."):
                logger.sync_warning("Unexpected GCT version line", line=line1)
                return data

            f.readline()  # dimensions line (num_genes\tnum_tissues)

            # Read the column header to get tissue IDs
            reader = csv.reader(f, delimiter="\t")
            header = next(reader)
            # Columns: Name, Description, tissue1, tissue2, ...
            tissue_ids = header[2:]

            for row in reader:
                if len(row) < 3:
                    continue

                gencode_id = row[0].strip()
                gene_symbol = row[1].strip()
                if not gene_symbol:
                    continue

                # Build tissue expression map (same structure as API path)
                tissues: dict[str, dict[str, Any]] = {}
                for i, tissue_id in enumerate(tissue_ids):
                    val = row[i + 2] if i + 2 < len(row) else ""
                    if val and val != "NA":
                        try:
                            tissues[tissue_id] = {
                                "median_tpm": float(val),
                                "unit": "TPM",
                            }
                        except ValueError:
                            continue

                if tissues:
                    data[gene_symbol] = {
                        "tissues": tissues,
                        "dataset_version": "gtex_v8",
                        "gencode_id": gencode_id,
                        "gene_symbol": gene_symbol,
                    }

        return data

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch GTEx expression data for a single gene.

        Tries bulk data first, then falls back to GTEx Portal API.
        """
        if not gene.approved_symbol:
            return None

        # Try bulk lookup first
        if self._bulk_data is not None:
            bulk_result = self.lookup_gene(gene.approved_symbol)
            if bulk_result is not None:
                return bulk_result

        # Fall back to API
        return await self._fetch_via_api(gene)

    async def _fetch_via_api(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch GTEx data via Portal API (original implementation)."""
        if not gene.approved_symbol:
            return None

        expression_data = await self._fetch_by_symbol(gene.approved_symbol)

        if not expression_data:
            logger.sync_debug("No GTEx data found for gene", gene_symbol=gene.approved_symbol)
            return None

        result: dict[str, Any] = expression_data
        return result

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def _fetch_by_symbol(self, symbol: str) -> dict | None:
        """Fetch GTEx data using gene symbol via API."""
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            # First, search for the gene to get its gencode ID
            search_response = await client.get(
                f"{self.base_url}/reference/geneSearch",
                params={"geneId": symbol, "limit": 1},
                headers=self.headers,
            )

            search_data = search_response.json()
            if not search_data.get("data"):
                logger.sync_debug("Gene not found in GTEx", symbol=symbol)
                return None

            # Get the gencode ID from search results
            gene_info = search_data["data"][0]
            gencode_id = gene_info.get("gencodeId")
            if not gencode_id:
                logger.sync_warning("No gencode ID in GTEx response", symbol=symbol)
                return None

            # Now fetch expression data using the gencode ID
            expr_response = await client.get(
                f"{self.base_url}/expression/medianGeneExpression",
                params={"gencodeId": gencode_id, "datasetId": "gtex_v8", "format": "json"},
                headers=self.headers,
            )

            expr_data = expr_response.json()
            if not expr_data.get("data"):
                logger.sync_debug(
                    "No expression data in GTEx", symbol=symbol, gencode_id=gencode_id
                )
                return None

            # Build tissue expression map
            tissues = {}
            for expr in expr_data["data"]:
                tissue_id = expr.get("tissueSiteDetailId")
                if tissue_id:
                    tissues[tissue_id] = {
                        "median_tpm": expr.get("median", 0),
                        "unit": expr.get("unit", "TPM"),
                    }

            return {
                "tissues": tissues,
                "dataset_version": "gtex_v8",
                "gencode_id": gencode_id,
                "gene_symbol": symbol,
            }

        except httpx.HTTPStatusError as e:
            logger.sync_error("GTEx API error", symbol=symbol, status_code=e.response.status_code)
            raise
        except Exception as e:
            logger.sync_error(f"Error fetching GTEx data: {str(e)}", symbol=symbol)
            raise

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """Fetch annotations for multiple genes.

        Loads bulk data once, then does fast local lookups. Falls back to
        GTEx Portal API for genes not found in the bulk file.
        """
        # Load bulk data if not already loaded
        try:
            await self.ensure_bulk_data_loaded()
        except Exception as e:
            logger.sync_warning(
                f"Failed to load GTEx bulk data, falling back to API: {e}",
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
                "GTEx bulk miss, falling back to API",
                bulk_hits=len(results),
                api_fallback=len(api_fallback_genes),
            )

        # API fallback for misses
        for i, gene in enumerate(api_fallback_genes):
            try:
                if i % 10 == 0 and api_fallback_genes:
                    logger.sync_info(
                        "Processing GTEx API fallback",
                        progress=f"{i}/{len(api_fallback_genes)}",
                    )
                annotation = await self._fetch_via_api(gene)
                if annotation:
                    results[gene.id] = annotation
            except Exception as e:
                logger.sync_error(
                    f"Failed to fetch GTEx annotation for {gene.approved_symbol}",
                    error_detail=str(e),
                )
                if self.circuit_breaker and self.circuit_breaker.state == "open":
                    logger.sync_error(
                        "Circuit breaker open, stopping API fallback",
                    )
                    break

        return results
