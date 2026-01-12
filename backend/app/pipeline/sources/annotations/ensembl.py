"""
Ensembl Annotation Source

Fetches gene structure data including exons, transcripts, and genomic coordinates
from the Ensembl REST API.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, SimpleRateLimiter, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource

logger = get_logger(__name__)


class EnsemblAnnotationSource(BaseAnnotationSource):
    """
    Ensembl gene structure annotation source.

    Fetches exon/intron structure, transcripts, and genomic coordinates
    for visualization. Uses POST lookup/symbol endpoint for batch requests.
    """

    source_name = "ensembl"
    display_name = "Ensembl"
    version = "1.0"

    # Base configuration
    base_url = "https://rest.ensembl.org"

    # Default values (overridden by config)
    batch_size = 500  # API limit is 1000

    def __init__(self, session: Session) -> None:
        """Initialize the Ensembl annotation source."""
        super().__init__(session)

        # Load configuration
        from app.core.datasource_config import get_annotation_config

        config = get_annotation_config("ensembl") or {}

        # Apply Ensembl-specific configuration
        self.batch_size = config.get("batch_size", 500)

        # Initialize rate limiter (15 req/s for Ensembl)
        self.rate_limiter = SimpleRateLimiter(requests_per_second=self.requests_per_second)

        # Update source configuration
        if self.source_record:
            self.source_record.update_frequency = "monthly"
            self.source_record.description = (
                "Gene structure data from Ensembl - exons, transcripts, coordinates"
            )
            self.source_record.base_url = self.base_url
            self.session.commit()

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Validate Ensembl annotation data."""
        if not super()._is_valid_annotation(annotation_data):
            return False

        # Ensembl specific: must have gene_id and at least basic structure
        required_fields = ["gene_id", "gene_symbol"]
        has_required = all(field in annotation_data for field in required_fields)

        # Must have at least one transcript with exons
        if has_required and "canonical_transcript" in annotation_data:
            transcript = annotation_data["canonical_transcript"]
            has_exons = transcript.get("exon_count", 0) > 0
            return has_exons

        return has_required

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch Ensembl annotation for a single gene.

        Args:
            gene: Gene object to fetch annotations for

        Returns:
            Dictionary with annotation data or None if not found
        """
        await self.rate_limiter.wait()

        try:
            client = await self.get_http_client()

            # Use lookup endpoint for single gene
            url = f"{self.base_url}/lookup/symbol/homo_sapiens/{gene.approved_symbol}"
            params = {"expand": "1"}  # Include transcripts and exons

            response = await client.get(
                url,
                params=params,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

            if response.status_code == 404:
                logger.sync_debug("Gene not found in Ensembl", gene_symbol=gene.approved_symbol)
                return None

            if response.status_code != 200:
                logger.sync_warning(
                    "Unexpected status from Ensembl",
                    gene_symbol=gene.approved_symbol,
                    status_code=response.status_code,
                )
                return None

            data = response.json()
            return self._parse_gene_data(gene.approved_symbol, data)

        except httpx.HTTPStatusError as e:
            logger.sync_error(
                "HTTP error fetching Ensembl data",
                gene_symbol=gene.approved_symbol,
                status_code=e.response.status_code,
            )
            raise

        except Exception as e:
            logger.sync_error(
                "Error fetching Ensembl annotation",
                gene_symbol=gene.approved_symbol,
                error_detail=str(e),
            )
            return None

    def _parse_gene_data(self, gene_symbol: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Parse Ensembl API response into annotation format.

        Args:
            gene_symbol: Gene symbol for reference
            data: Raw API response

        Returns:
            Parsed annotation dictionary
        """
        if not data:
            return None

        # Find canonical transcript (MANE Select preferred)
        transcripts = data.get("Transcript", [])
        canonical = self._find_canonical_transcript(transcripts)

        if not canonical:
            logger.sync_debug(
                "No canonical transcript found",
                gene_symbol=gene_symbol,
                transcript_count=len(transcripts),
            )
            return None

        # Parse exons from canonical transcript
        exons = self._parse_exons(canonical)

        annotation = {
            "gene_id": data.get("id"),
            "gene_symbol": gene_symbol,
            "display_name": data.get("display_name"),
            "description": data.get("description"),
            "biotype": data.get("biotype"),
            "chromosome": data.get("seq_region_name"),
            "start": data.get("start"),
            "end": data.get("end"),
            "strand": "+" if data.get("strand", 1) == 1 else "-",
            "gene_length": data.get("end", 0) - data.get("start", 0) + 1,
            "assembly": data.get("assembly_name", "GRCh38"),
            "canonical_transcript": {
                "transcript_id": canonical.get("id"),
                "display_name": canonical.get("display_name"),
                "biotype": canonical.get("biotype"),
                "is_canonical": canonical.get("is_canonical", False),
                "start": canonical.get("start"),
                "end": canonical.get("end"),
                "exon_count": len(exons),
                "exons": exons,
                # Try to extract RefSeq ID from external names
                "refseq_transcript_id": self._find_refseq_id(canonical),
            },
            "transcript_count": len(transcripts),
            "exon_count": len(exons),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        logger.sync_debug(
            "Successfully parsed Ensembl data",
            gene_symbol=gene_symbol,
            gene_id=annotation["gene_id"],
            exon_count=annotation["exon_count"],
        )

        return annotation

    def _find_canonical_transcript(self, transcripts: list[dict]) -> dict[str, Any] | None:
        """
        Find canonical transcript, preferring MANE Select.

        Args:
            transcripts: List of transcript data from Ensembl

        Returns:
            Canonical transcript or None
        """
        if not transcripts:
            return None

        # Priority 1: Look for MANE Select
        for t in transcripts:
            if t.get("is_canonical") and "MANE_Select" in str(t.get("display_name", "")):
                return t

        # Priority 2: Use is_canonical flag
        for t in transcripts:
            if t.get("is_canonical"):
                return t

        # Priority 3: Return longest protein-coding transcript
        protein_coding = [t for t in transcripts if t.get("biotype") == "protein_coding"]
        if protein_coding:
            return max(protein_coding, key=lambda x: (x.get("end", 0) - x.get("start", 0)))

        # Fallback: Return first transcript
        return transcripts[0] if transcripts else None

    def _parse_exons(self, transcript: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse exon data from transcript.

        Args:
            transcript: Transcript data with exons

        Returns:
            List of parsed exon dictionaries
        """
        exons_raw = transcript.get("Exon", [])

        exons = []
        for i, exon in enumerate(sorted(exons_raw, key=lambda x: x.get("start", 0))):
            exon_data = {
                "exon_id": exon.get("id"),
                "exon_number": i + 1,
                "start": exon.get("start"),
                "end": exon.get("end"),
                "length": exon.get("end", 0) - exon.get("start", 0) + 1,
                "phase_start": exon.get("phase"),
                "phase_end": exon.get("end_phase"),
            }
            exons.append(exon_data)

        return exons

    def _find_refseq_id(self, transcript: dict[str, Any]) -> str | None:
        """
        Extract RefSeq transcript ID if available.

        Args:
            transcript: Transcript data

        Returns:
            RefSeq ID or None
        """
        # Check display name for NM_ prefix
        display_name = transcript.get("display_name", "")
        if display_name and display_name.startswith("NM_"):
            return display_name

        # Check external references if available
        external_refs = transcript.get("external_name", "")
        if external_refs and "NM_" in str(external_refs):
            return external_refs

        return None

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Fetch annotations for multiple genes using POST lookup/symbol.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene IDs to annotation data
        """
        if not genes:
            return {}

        results = {}

        # Process in chunks of batch_size
        for i in range(0, len(genes), self.batch_size):
            batch = genes[i : i + self.batch_size]
            batch_results = await self._fetch_batch_chunk(batch)
            results.update(batch_results)

            # Small delay between batches
            if i + self.batch_size < len(genes):
                await asyncio.sleep(0.5)

        return results

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def _fetch_batch_chunk(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Fetch a single batch of genes using POST endpoint.

        Args:
            genes: List of genes (max batch_size)

        Returns:
            Dictionary mapping gene IDs to annotations
        """
        await self.rate_limiter.wait()

        try:
            client = await self.get_http_client()

            # Build POST request body
            symbols = [g.approved_symbol for g in genes]
            url = f"{self.base_url}/lookup/symbol/homo_sapiens"

            response = await client.post(
                url,
                json={"symbols": symbols},
                params={"expand": "1"},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                logger.sync_warning(
                    "Batch request failed",
                    status_code=response.status_code,
                    batch_size=len(genes),
                )
                return {}

            data = response.json()

            # Parse results
            results = {}
            for gene in genes:
                symbol = gene.approved_symbol
                if symbol in data and data[symbol]:
                    annotation = self._parse_gene_data(symbol, data[symbol])
                    if annotation:
                        results[gene.id] = annotation

            logger.sync_info(
                "Batch fetch completed",
                requested=len(genes),
                successful=len(results),
            )

            return results

        except httpx.HTTPStatusError as e:
            logger.sync_error(
                "HTTP error in batch fetch",
                status_code=e.response.status_code,
                batch_size=len(genes),
            )
            raise

        except Exception as e:
            logger.sync_error(
                "Error in batch fetch",
                error_detail=str(e),
                batch_size=len(genes),
            )
            return {}
