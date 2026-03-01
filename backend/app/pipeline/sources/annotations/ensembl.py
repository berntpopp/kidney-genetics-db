"""
Ensembl Annotation Source

Fetches gene structure data including exons, transcripts, and genomic coordinates
from the Ensembl REST API.  Uses the MANE summary file to resolve Ensembl
transcript IDs to RefSeq NM_ accessions without per-transcript API calls.
"""

import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, SimpleRateLimiter, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

logger = get_logger(__name__)


class EnsemblAnnotationSource(BulkDataSourceMixin, BaseAnnotationSource):
    """
    Ensembl gene structure annotation source.

    Fetches exon/intron structure, transcripts, and genomic coordinates
    for visualization. Uses POST lookup/symbol endpoint for batch requests.

    Uses MANE summary file for Ensembl-to-RefSeq transcript mapping,
    replacing per-transcript xrefs API calls with a single bulk download.
    Falls back to the xrefs API for transcripts not in MANE.
    """

    source_name = "ensembl"
    display_name = "Ensembl"
    version = "1.0"

    # Base configuration
    base_url = "https://rest.ensembl.org"

    # Default values (overridden by config)
    batch_size = 500  # API limit is 1000

    # MANE bulk file for Ensembl→RefSeq transcript mapping
    bulk_file_url = (
        "https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/"
        "current/MANE.GRCh38.v1.5.summary.txt.gz"
    )
    bulk_cache_ttl_hours = 168  # 7 days
    bulk_file_format = "txt.gz"

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

    def parse_bulk_file(self, path: Path) -> dict[str, dict[str, Any]]:
        """Parse the MANE summary file into an Ensembl→RefSeq mapping.

        Builds a dict keyed by *unversioned* Ensembl transcript ID (e.g.
        ``ENST00000263100``) mapping to ``{"refseq_nuc": "NM_130786.4",
        "symbol": "A1BG", "mane_status": "MANE Select"}``.

        Args:
            path: Path to the decompressed MANE summary TSV.

        Returns:
            Mapping of unversioned ENST ID → metadata dict.
        """
        data: dict[str, dict[str, Any]] = {}
        with open(path, newline="") as fh:
            reader = csv.DictReader(
                (line for line in fh if not line.startswith("#")),
                fieldnames=[
                    "NCBI_GeneID",
                    "Ensembl_Gene",
                    "HGNC_ID",
                    "symbol",
                    "name",
                    "RefSeq_nuc",
                    "RefSeq_prot",
                    "Ensembl_nuc",
                    "Ensembl_prot",
                    "MANE_status",
                    "GRCh38_chr",
                    "chr_start",
                    "chr_end",
                    "chr_strand",
                ],
                delimiter="\t",
            )
            for row in reader:
                enst_versioned = row.get("Ensembl_nuc", "")
                refseq_nuc = row.get("RefSeq_nuc", "")
                if not enst_versioned or not refseq_nuc:
                    continue
                # Key by unversioned ENST so lookups match Ensembl API IDs
                enst_unversioned = enst_versioned.split(".")[0]
                data[enst_unversioned] = {
                    "refseq_nuc": refseq_nuc,
                    "symbol": row.get("symbol", ""),
                    "mane_status": row.get("MANE_status", ""),
                    "ensembl_nuc_versioned": enst_versioned,
                }
        logger.sync_info(
            "Parsed MANE summary file",
            transcript_count=len(data),
            path=str(path),
        )
        return data

    async def _resolve_refseq_id(self, transcript_id: str) -> str | None:
        """Resolve a RefSeq NM_ ID for an Ensembl transcript.

        Tries the MANE bulk lookup first (zero-cost).  Falls back to the
        Ensembl xrefs API when the transcript is not in MANE.

        Args:
            transcript_id: Ensembl transcript ID (e.g. ENST00000262304).

        Returns:
            RefSeq NM transcript ID or None.
        """
        if not transcript_id:
            return None

        # Strip version for MANE lookup
        enst_unversioned = transcript_id.split(".")[0]
        mane_entry = self.lookup_gene(enst_unversioned)
        if mane_entry:
            refseq: str = mane_entry["refseq_nuc"]
            return refseq

        # Fall back to Ensembl xrefs API
        return await self._fetch_refseq_id(transcript_id)

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Validate Ensembl annotation data."""
        if not super()._is_valid_annotation(annotation_data):
            return False

        # Ensembl specific: must have gene_id and at least basic structure
        required_fields = ["gene_id", "gene_symbol"]
        has_required = all(field in annotation_data for field in required_fields)

        # Must have at least one transcript with exons
        if has_required and "canonical_transcript" in annotation_data:
            transcript: dict[str, Any] = annotation_data["canonical_transcript"]
            exon_count: int = int(transcript.get("exon_count", 0))
            return exon_count > 0

        return bool(has_required)

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch Ensembl annotation for a single gene.

        Loads the MANE bulk file on first call so that RefSeq ID resolution
        uses a dict lookup instead of per-transcript API calls.

        Args:
            gene: Gene object to fetch annotations for

        Returns:
            Dictionary with annotation data or None if not found
        """
        # Ensure MANE data is loaded for RefSeq resolution
        await self.ensure_bulk_data_loaded()

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
            annotation = self._parse_gene_data(gene.approved_symbol, data)

            # Resolve RefSeq ID via MANE lookup (with API fallback)
            if annotation and annotation.get("canonical_transcript"):
                transcript_id = annotation["canonical_transcript"].get("transcript_id")
                if transcript_id:
                    refseq_id = await self._resolve_refseq_id(transcript_id)
                    if refseq_id:
                        annotation["canonical_transcript"]["refseq_transcript_id"] = refseq_id
                        logger.sync_debug(
                            "Found RefSeq ID",
                            gene_symbol=gene.approved_symbol,
                            ensembl_id=transcript_id,
                            refseq_id=refseq_id,
                        )

            return annotation

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
        Extract RefSeq transcript ID if available from transcript data.

        Note: This is a synchronous fallback. The async method _fetch_refseq_id
        should be used when possible to get accurate RefSeq mappings.

        Args:
            transcript: Transcript data

        Returns:
            RefSeq ID or None
        """
        # Check display name for NM_ prefix
        display_name: str = str(transcript.get("display_name", ""))
        if display_name and display_name.startswith("NM_"):
            return display_name

        # Check external references if available
        external_refs: str = str(transcript.get("external_name", ""))
        if external_refs and "NM_" in external_refs:
            return external_refs

        return None

    async def _fetch_refseq_id(self, transcript_id: str) -> str | None:
        """
        Fetch RefSeq transcript ID from Ensembl xrefs endpoint.

        Uses /xrefs/id/{id} to get cross-references including RefSeq NM_ IDs.

        Args:
            transcript_id: Ensembl transcript ID (e.g., ENST00000262304)

        Returns:
            RefSeq NM transcript ID or None
        """
        if not transcript_id:
            return None

        try:
            await self.rate_limiter.wait()
            client = await self.get_http_client()

            url = f"{self.base_url}/xrefs/id/{transcript_id}"
            # Filter for RefSeq mRNA only - returns versioned NM_ IDs
            params = {"external_db": "RefSeq_mRNA"}

            response = await client.get(
                url,
                params=params,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                return None

            xrefs: list[dict[str, Any]] = response.json()

            # Find the best RefSeq transcript ID (prefer NM_ with version)
            refseq_ids: list[str] = []
            for xref in xrefs:
                display_id: str = xref.get("display_id", "")
                if display_id.startswith("NM_"):
                    refseq_ids.append(display_id)

            # Return the one with version number if available
            versioned: list[str] = [r for r in refseq_ids if "." in r]
            if versioned:
                return versioned[0]
            if refseq_ids:
                return refseq_ids[0]

            return None

        except Exception as e:
            logger.sync_debug(
                "Could not fetch RefSeq xref",
                transcript_id=transcript_id,
                error=str(e),
            )
            return None

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Fetch annotations for multiple genes using POST lookup/symbol.

        Loads the MANE bulk file once so that RefSeq ID resolution for all
        genes uses dict lookups instead of per-transcript API calls.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene IDs to annotation data
        """
        if not genes:
            return {}

        # Ensure MANE data is loaded once for the entire batch
        await self.ensure_bulk_data_loaded()

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

            # Resolve RefSeq IDs via MANE lookup (with API fallback)
            for _gene_id, annotation in results.items():
                if annotation.get("canonical_transcript"):
                    transcript_id = annotation["canonical_transcript"].get("transcript_id")
                    if transcript_id:
                        refseq_id = await self._resolve_refseq_id(transcript_id)
                        if refseq_id:
                            annotation["canonical_transcript"]["refseq_transcript_id"] = refseq_id

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
