"""
GTEx annotation source for gene expression data.
"""

from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource

logger = get_logger(__name__)


class GTExAnnotationSource(BaseAnnotationSource):
    """
    GTEx (Genotype-Tissue Expression) annotation source.

    Fetches tissue-specific gene expression data (median TPM values) from GTEx Portal API.
    """

    source_name = "gtex"
    display_name = "GTEx"
    version = "v8"

    # API configuration
    base_url = "https://gtexportal.org/api/v2"
    headers = {"Accept": "application/json", "User-Agent": "KidneyGeneticsDB/1.0"}

    # Cache configuration
    cache_ttl_days = 30

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch GTEx expression data for a single gene.

        Args:
            gene: Gene object to fetch annotations for

        Returns:
            Dictionary of expression data or None if not found
        """
        if not gene.approved_symbol:
            return None

        expression_data = await self._fetch_by_symbol(gene.approved_symbol)

        if not expression_data:
            logger.sync_debug("No GTEx data found for gene", gene_symbol=gene.approved_symbol)
            return None

        return expression_data

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def _fetch_by_symbol(self, symbol: str) -> dict | None:
        """
        Fetch GTEx data using gene symbol.

        Args:
            symbol: Gene symbol to search for

        Returns:
            Dictionary with expression data or None
        """
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            # First, search for the gene to get its gencode ID
            search_response = await client.get(
                f"{self.base_url}/reference/geneSearch",
                params={"geneId": symbol, "limit": 1},
                headers=self.headers,
            )

            # Response validation handled by retry logic

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

            # Response validation handled by retry logic

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
        """
        Fetch annotations for multiple genes.

        GTEx doesn't have a batch endpoint, so we fetch individually
        with rate limiting.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene_id to annotation data
        """
        import asyncio

        results = {}

        # Process in batches to avoid overwhelming the API
        batch_size = 10

        for i in range(0, len(genes), batch_size):
            batch = genes[i : i + batch_size]

            tasks = []
            for gene in batch:
                tasks.append(self.fetch_annotation(gene))

            annotations = await asyncio.gather(*tasks, return_exceptions=True)

            for gene, annotation in zip(batch, annotations, strict=False):
                if annotation and not isinstance(annotation, Exception):
                    results[gene.id] = annotation
                elif isinstance(annotation, Exception):
                    logger.sync_error(
                        "Error fetching GTEx for gene",
                        gene_symbol=gene.approved_symbol,
                        error=str(annotation),
                    )

            # Rate limiting between batches
            if i + batch_size < len(genes):
                await asyncio.sleep(1)

        return results
