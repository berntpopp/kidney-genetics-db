"""
HGNC annotation source for gene annotations.
"""

from typing import Any

import httpx

from app.core.logging import get_logger
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource

logger = get_logger(__name__)


class HGNCAnnotationSource(BaseAnnotationSource):
    """
    HGNC (HUGO Gene Nomenclature Committee) annotation source.

    Fetches gene information from the HGNC REST API including:
    - NCBI Gene ID (Entrez ID)
    - MANE Select transcripts
    - RefSeq accessions
    - OMIM IDs
    - PubMed IDs
    - Gene families
    - Previous symbols and aliases
    """

    source_name = "hgnc"
    display_name = "HGNC"
    version = "2024.01"

    # API configuration
    base_url = "https://rest.genenames.org"
    headers = {"Accept": "application/json", "User-Agent": "KidneyGeneticsDB/1.0"}

    # Cache configuration
    cache_ttl_days = 7

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch HGNC annotation for a single gene.

        Args:
            gene: Gene object to fetch annotations for

        Returns:
            Dictionary of annotation data or None if not found
        """
        # Try different identifiers
        hgnc_data = None

        # Try HGNC ID first
        if gene.hgnc_id:
            hgnc_data = await self._fetch_by_hgnc_id(gene.hgnc_id)

        # Fall back to gene symbol
        if not hgnc_data and gene.approved_symbol:
            hgnc_data = await self._fetch_by_symbol(gene.approved_symbol)

        # Fall back to Ensembl ID
        # if not hgnc_data and gene.ensembl_gene_id:
        #     hgnc_data = await self._fetch_by_ensembl_id(gene.ensembl_gene_id)

        if not hgnc_data:
            logger.sync_warning(
                "No HGNC data found for gene",
                gene_symbol=gene.approved_symbol,
                hgnc_id=gene.hgnc_id,
            )
            return None

        # Extract and structure the annotation data
        return self._extract_annotations(hgnc_data)

    async def _fetch_by_hgnc_id(self, hgnc_id: str) -> dict | None:
        """Fetch HGNC data by HGNC ID."""
        # Clean HGNC ID (remove "HGNC:" prefix if present)
        clean_id = hgnc_id.replace("HGNC:", "")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/fetch/hgnc_id/{clean_id}", headers=self.headers, timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("response", {}).get("docs"):
                        return data["response"]["docs"][0]

            except Exception as e:
                logger.sync_error(f"Error fetching HGNC by ID: {str(e)}", hgnc_id=hgnc_id)

        return None

    async def _fetch_by_symbol(self, symbol: str) -> dict | None:
        """Fetch HGNC data by gene symbol."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/fetch/symbol/{symbol}", headers=self.headers, timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("response", {}).get("docs"):
                        return data["response"]["docs"][0]

            except Exception as e:
                logger.sync_error(f"Error fetching HGNC by symbol: {str(e)}", symbol=symbol)

        return None

    async def _fetch_by_ensembl_id(self, ensembl_id: str) -> dict | None:
        """Fetch HGNC data by Ensembl gene ID."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/fetch/ensembl_gene_id/{ensembl_id}",
                    headers=self.headers,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("response", {}).get("docs"):
                        return data["response"]["docs"][0]

            except Exception as e:
                logger.sync_error(
                    f"Error fetching HGNC by Ensembl ID: {str(e)}", ensembl_id=ensembl_id
                )

        return None

    def _extract_annotations(self, hgnc_data: dict) -> dict[str, Any]:
        """
        Extract relevant annotations from HGNC API response.

        Args:
            hgnc_data: Raw HGNC API response

        Returns:
            Structured annotation dictionary
        """
        annotations = {
            # Core identifiers
            "hgnc_id": hgnc_data.get("hgnc_id"),
            "symbol": hgnc_data.get("symbol"),
            "name": hgnc_data.get("name"),
            "status": hgnc_data.get("status"),
            # External IDs
            "ncbi_gene_id": hgnc_data.get("entrez_id"),
            "ensembl_gene_id": hgnc_data.get("ensembl_gene_id"),
            "omim_ids": hgnc_data.get("omim_id", []),
            "orphanet_id": hgnc_data.get("orphanet"),
            "cosmic_id": hgnc_data.get("cosmic"),
            # RefSeq accessions
            "refseq_accession": hgnc_data.get("refseq_accession", []),
            # MANE Select - Parse from mane_select field
            "mane_select": self._parse_mane_select(hgnc_data.get("mane_select", [])),
            # Gene information
            "locus_type": hgnc_data.get("locus_type"),
            "locus_group": hgnc_data.get("locus_group"),
            "location": hgnc_data.get("location"),
            "location_sortable": hgnc_data.get("location_sortable"),
            # Aliases and previous symbols
            "alias_symbol": hgnc_data.get("alias_symbol", []),
            "alias_name": hgnc_data.get("alias_name", []),
            "prev_symbol": hgnc_data.get("prev_symbol", []),
            "prev_name": hgnc_data.get("prev_name", []),
            # Gene families
            "gene_family": hgnc_data.get("gene_family", []),
            "gene_family_id": hgnc_data.get("gene_family_id", []),
            # Publications
            "pubmed_ids": hgnc_data.get("pubmed_id", []),
            # Dates
            "date_approved_reserved": hgnc_data.get("date_approved_reserved"),
            "date_modified": hgnc_data.get("date_modified"),
            "date_name_changed": hgnc_data.get("date_name_changed"),
            "date_symbol_changed": hgnc_data.get("date_symbol_changed"),
            # Additional fields
            "uuid": hgnc_data.get("uuid"),
            "_version_": hgnc_data.get("_version_"),
        }

        # Remove None values to save space
        return {k: v for k, v in annotations.items() if v is not None}

    def _parse_mane_select(self, mane_select_list: list) -> dict | None:
        """
        Parse MANE Select transcript information.

        HGNC provides MANE Select as a list like:
        ["ENST00000356175.9", "NM_000546.6"]

        Returns:
            Dictionary with ensembl and refseq transcript IDs
        """
        if not mane_select_list or len(mane_select_list) < 2:
            return None

        # Usually first is Ensembl, second is RefSeq
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
        """
        Fetch annotations for multiple genes.

        Note: HGNC doesn't have a batch endpoint, so we fetch individually
        but use async to parallelize requests.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene_id to annotation data
        """
        import asyncio

        results = {}

        # Create tasks for all genes
        tasks = []
        for gene in genes:
            tasks.append(self.fetch_annotation(gene))

        # Execute all tasks concurrently
        annotations = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results back to gene IDs
        for gene, annotation in zip(genes, annotations, strict=False):
            if annotation and not isinstance(annotation, Exception):
                results[gene.id] = annotation
            elif isinstance(annotation, Exception):
                logger.sync_error(
                    "Error fetching annotation for gene",
                    gene_symbol=gene.approved_symbol,
                    error=str(annotation),
                )

        return results

    async def search_genes(self, query: str, limit: int = 10) -> list[dict]:
        """
        Search for genes in HGNC by query string.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of gene data dictionaries
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/search/{query}",
                    headers=self.headers,
                    params={"rows": limit},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", {}).get("docs", [])

            except Exception as e:
                logger.sync_error(f"Error searching HGNC: {str(e)}", query=query)

        return []
