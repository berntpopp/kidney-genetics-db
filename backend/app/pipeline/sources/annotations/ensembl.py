"""
Ensembl Annotation Source

Fetches gene structure data including exons, transcripts, and genomic coordinates
by parsing Ensembl's GTF bulk file.  Uses the MANE summary file to resolve
Ensembl transcript IDs to RefSeq NM_ accessions.

Zero REST API dependency — all data comes from two bulk files:
1. Ensembl GTF (gene structure, exons, transcripts)
2. NCBI MANE summary (Ensembl→RefSeq mapping)
"""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

logger = get_logger(__name__)


def _parse_gtf_attributes(attr_str: str) -> tuple[dict[str, str], set[str]]:
    """Parse the GTF attribute column into key-value pairs and tags.

    GTF format: ``key "value"; key "value";``
    The ``tag`` key can appear multiple times, so tags are collected
    into a separate set.

    Args:
        attr_str: The 9th column of a GTF line.

    Returns:
        Tuple of (attributes dict, tags set).
    """
    attrs: dict[str, str] = {}
    tags: set[str] = set()
    for field in attr_str.strip().rstrip(";").split("; "):
        parts = field.split(" ", 1)
        if len(parts) != 2:
            continue
        key = parts[0]
        value = parts[1].strip('"')
        if key == "tag":
            tags.add(value)
        else:
            attrs[key] = value
    return attrs, tags


class EnsemblAnnotationSource(BulkDataSourceMixin, BaseAnnotationSource):
    """
    Ensembl gene structure annotation source.

    Parses the Ensembl GTF file for exon/intron structure, transcripts,
    and genomic coordinates.  Uses the MANE summary file for
    Ensembl→RefSeq transcript mapping.

    No REST API calls — everything comes from bulk files.
    """

    source_name = "ensembl"
    display_name = "Ensembl"
    version = "2.0"

    # GTF bulk file (replaces REST API)
    bulk_file_url = (
        "https://ftp.ensembl.org/pub/current_gtf/homo_sapiens/"
        "Homo_sapiens.GRCh38.115.chr.gtf.gz"
    )
    bulk_cache_ttl_hours = 168  # 7 days
    bulk_file_format = "gtf.gz"
    bulk_file_min_size_bytes = 80_000_000  # ~99 MB compressed expected

    # MANE summary file for Ensembl→RefSeq transcript mapping
    mane_file_url = (
        "https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/"
        "current/MANE.GRCh38.v1.5.summary.txt.gz"
    )

    # Batch size for fetch_batch (dict lookups, so can be large)
    batch_size = 1000

    def __init__(self, session: Session) -> None:
        """Initialize the Ensembl annotation source."""
        super().__init__(session)

        # Load configuration
        from app.core.datasource_config import get_annotation_config

        config = get_annotation_config("ensembl") or {}
        self.batch_size = config.get("batch_size", 1000)

        # MANE data dict (separate from _bulk_data which holds GTF data)
        self._mane_data: dict[str, dict[str, Any]] | None = None

        # Update source configuration
        if self.source_record:
            self.source_record.update_frequency = "monthly"
            self.source_record.description = (
                "Gene structure data from Ensembl GTF - exons, transcripts, coordinates"
            )
            self.source_record.base_url = "https://ftp.ensembl.org"
            self.session.commit()

    # ------------------------------------------------------------------
    # Bulk file parsing
    # ------------------------------------------------------------------

    def parse_bulk_file(self, path: Path) -> dict[str, dict[str, Any]]:
        """Parse the Ensembl GTF file into a gene-keyed annotation dict.

        Streams the GTF line-by-line, collecting gene, transcript, and
        exon features.  Selects a canonical transcript per gene using:
        1. MANE_Select tag
        2. Ensembl_canonical tag
        3. Longest protein-coding transcript

        Args:
            path: Path to the decompressed GTF file.

        Returns:
            Dict keyed by gene symbol → annotation data.
        """
        # Intermediate storage during parsing
        genes: dict[str, dict[str, Any]] = {}  # gene_name → gene info
        transcripts: dict[str, dict[str, Any]] = {}  # transcript_id → transcript info
        transcript_exons: dict[str, list[dict[str, Any]]] = {}  # transcript_id → exon list
        gene_transcripts: dict[str, list[str]] = {}  # gene_name → [transcript_ids]

        line_count = 0
        with open(path) as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                line_count += 1

                parts = line.rstrip("\n").split("\t", 8)
                if len(parts) < 9:
                    continue

                chrom, _source, feature, start, end, _score, strand, _frame, attr_str = parts
                attrs, tags = _parse_gtf_attributes(attr_str)

                if feature == "gene":
                    gene_name = attrs.get("gene_name", "")
                    if not gene_name:
                        continue
                    genes[gene_name] = {
                        "chromosome": chrom,
                        "start": int(start),
                        "end": int(end),
                        "strand": "+" if strand == "+" else "-",
                        "gene_id": attrs.get("gene_id", ""),
                        "biotype": attrs.get("gene_biotype", ""),
                    }
                    if gene_name not in gene_transcripts:
                        gene_transcripts[gene_name] = []

                elif feature == "transcript":
                    gene_name = attrs.get("gene_name", "")
                    transcript_id = attrs.get("transcript_id", "")
                    if not gene_name or not transcript_id:
                        continue

                    is_mane_select = "MANE_Select" in tags
                    is_canonical = "Ensembl_canonical" in tags

                    transcripts[transcript_id] = {
                        "transcript_id": transcript_id,
                        "gene_name": gene_name,
                        "biotype": attrs.get("transcript_biotype", ""),
                        "start": int(start),
                        "end": int(end),
                        "display_name": attrs.get("transcript_name", ""),
                        "is_mane_select": is_mane_select,
                        "is_canonical": is_canonical,
                        "length": int(end) - int(start) + 1,
                    }

                    if gene_name not in gene_transcripts:
                        gene_transcripts[gene_name] = []
                    gene_transcripts[gene_name].append(transcript_id)

                elif feature == "exon":
                    transcript_id = attrs.get("transcript_id", "")
                    if not transcript_id:
                        continue
                    exon_data = {
                        "exon_id": attrs.get("exon_id", ""),
                        "exon_number": int(attrs.get("exon_number", "0")),
                        "start": int(start),
                        "end": int(end),
                        "length": int(end) - int(start) + 1,
                    }
                    if transcript_id not in transcript_exons:
                        transcript_exons[transcript_id] = []
                    transcript_exons[transcript_id].append(exon_data)

        logger.sync_info(
            "GTF file parsed",
            lines_processed=line_count,
            gene_count=len(genes),
            transcript_count=len(transcripts),
        )

        # Build final annotation dict keyed by gene symbol
        result: dict[str, dict[str, Any]] = {}
        for gene_name, gene_info in genes.items():
            tx_ids = gene_transcripts.get(gene_name, [])
            if not tx_ids:
                continue

            # Select canonical transcript
            canonical_id = self._select_canonical_transcript(tx_ids, transcripts)
            if not canonical_id:
                continue

            canonical = transcripts[canonical_id]
            exons = transcript_exons.get(canonical_id, [])

            # Sort exons by start position and re-number
            exons_sorted = sorted(exons, key=lambda e: e["start"])
            for i, exon in enumerate(exons_sorted):
                exon["exon_number"] = i + 1

            gene_length = gene_info["end"] - gene_info["start"] + 1

            result[gene_name] = {
                "gene_id": gene_info["gene_id"],
                "gene_symbol": gene_name,
                "display_name": gene_name,
                "description": None,
                "biotype": gene_info["biotype"],
                "chromosome": gene_info["chromosome"],
                "start": gene_info["start"],
                "end": gene_info["end"],
                "strand": gene_info["strand"],
                "gene_length": gene_length,
                "assembly": "GRCh38",
                "canonical_transcript": {
                    "transcript_id": canonical["transcript_id"],
                    "display_name": canonical["display_name"],
                    "biotype": canonical["biotype"],
                    "is_canonical": canonical["is_canonical"] or canonical["is_mane_select"],
                    "start": canonical["start"],
                    "end": canonical["end"],
                    "exon_count": len(exons_sorted),
                    "exons": exons_sorted,
                    "refseq_transcript_id": None,  # Filled in by MANE cross-reference
                },
                "transcript_count": len(tx_ids),
                "exon_count": len(exons_sorted),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        logger.sync_info(
            "GTF annotation dict built",
            genes_with_annotations=len(result),
        )
        return result

    @staticmethod
    def _select_canonical_transcript(
        transcript_ids: list[str],
        transcripts: dict[str, dict[str, Any]],
    ) -> str | None:
        """Select the canonical transcript from a list of transcript IDs.

        Priority:
        1. MANE_Select tagged transcript
        2. Ensembl_canonical tagged transcript
        3. Longest protein-coding transcript
        4. First transcript

        Args:
            transcript_ids: List of transcript IDs for a gene.
            transcripts: Full transcript dict (transcript_id → info).

        Returns:
            The selected transcript ID, or None.
        """
        if not transcript_ids:
            return None

        # Priority 1: MANE_Select
        for tx_id in transcript_ids:
            tx = transcripts.get(tx_id)
            if tx and tx.get("is_mane_select"):
                return tx_id

        # Priority 2: Ensembl_canonical
        for tx_id in transcript_ids:
            tx = transcripts.get(tx_id)
            if tx and tx.get("is_canonical"):
                return tx_id

        # Priority 3: Longest protein-coding
        protein_coding = []
        for tx_id in transcript_ids:
            tx = transcripts.get(tx_id)
            if tx and tx.get("biotype") == "protein_coding":
                protein_coding.append((tx_id, tx.get("length", 0)))
        if protein_coding:
            return max(protein_coding, key=lambda x: x[1])[0]

        # Priority 4: First transcript
        return transcript_ids[0]

    # ------------------------------------------------------------------
    # MANE parsing
    # ------------------------------------------------------------------

    def parse_mane_file(self, path: Path) -> dict[str, dict[str, Any]]:
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

    # ------------------------------------------------------------------
    # Bulk data loading (two files)
    # ------------------------------------------------------------------

    async def ensure_bulk_data_loaded(self, force: bool = False) -> None:
        """Download, decompress, parse, and cache both bulk files.

        Loads:
        1. Ensembl GTF → ``self._bulk_data`` (gene structure, keyed by symbol)
        2. MANE summary → ``self._mane_data`` (RefSeq mapping, keyed by ENST)

        Then cross-references: for each gene's canonical transcript, looks
        up RefSeq ID from the MANE data.

        Args:
            force: Force re-download and re-parse.
        """
        if self._bulk_data is not None and self._mane_data is not None and not force:
            return

        # 1. Download and parse GTF (use streaming — file is ~99 MB compressed)
        saved_url = self.bulk_file_url
        gtf_path = await self.download_bulk_file_streaming(force=force)

        # Decompress GTF if gzipped
        gtf_parse_path = gtf_path
        if gtf_path.suffix == ".gz":
            decompressed = gtf_path.with_suffix("")
            if not decompressed.exists() or force:
                import gzip as _gzip
                import shutil

                logger.sync_info(
                    "Decompressing GTF file",
                    src=str(gtf_path),
                    dest=str(decompressed),
                )
                with _gzip.open(gtf_path, "rb") as f_in:
                    with open(decompressed, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            gtf_parse_path = decompressed

        self._bulk_data = self.parse_bulk_file(gtf_parse_path)
        logger.sync_info(
            "GTF bulk data loaded",
            gene_count=len(self._bulk_data),
        )

        # 2. Download and parse MANE summary
        self.bulk_file_url = self.mane_file_url
        # Temporarily override format for MANE file
        saved_format = self.bulk_file_format
        self.bulk_file_format = "txt.gz"
        saved_min_size = self.bulk_file_min_size_bytes
        self.bulk_file_min_size_bytes = 0  # MANE file is much smaller

        try:
            mane_path = await self.download_bulk_file(force=force)

            # Decompress MANE if gzipped
            mane_parse_path = mane_path
            if mane_path.suffix == ".gz":
                decompressed_mane = mane_path.with_suffix("")
                if not decompressed_mane.exists() or force:
                    import gzip as _gzip
                    import shutil

                    logger.sync_info(
                        "Decompressing MANE file",
                        src=str(mane_path),
                        dest=str(decompressed_mane),
                    )
                    with _gzip.open(mane_path, "rb") as f_in:
                        with open(decompressed_mane, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                mane_parse_path = decompressed_mane

            self._mane_data = self.parse_mane_file(mane_parse_path)
        finally:
            # Restore original URL and format
            self.bulk_file_url = saved_url
            self.bulk_file_format = saved_format
            self.bulk_file_min_size_bytes = saved_min_size

        logger.sync_info(
            "MANE bulk data loaded",
            transcript_count=len(self._mane_data),
        )

        # 3. Cross-reference: attach RefSeq IDs to canonical transcripts
        refseq_matches = 0
        for _symbol, annotation in self._bulk_data.items():
            canonical = annotation.get("canonical_transcript")
            if not canonical:
                continue
            transcript_id = canonical.get("transcript_id", "")
            enst_unversioned = transcript_id.split(".")[0]
            mane_entry = self._mane_data.get(enst_unversioned)
            if mane_entry:
                canonical["refseq_transcript_id"] = mane_entry["refseq_nuc"]
                refseq_matches += 1

        logger.sync_info(
            "Cross-referenced GTF with MANE",
            total_genes=len(self._bulk_data),
            refseq_matches=refseq_matches,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Validate Ensembl annotation data."""
        if not super()._is_valid_annotation(annotation_data):
            return False

        required_fields = ["gene_id", "gene_symbol"]
        has_required = all(field in annotation_data for field in required_fields)

        if has_required and "canonical_transcript" in annotation_data:
            transcript: dict[str, Any] = annotation_data["canonical_transcript"]
            exon_count: int = int(transcript.get("exon_count", 0))
            return exon_count > 0

        return bool(has_required)

    # ------------------------------------------------------------------
    # Fetch methods (pure dict lookups, no API calls)
    # ------------------------------------------------------------------

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch Ensembl annotation for a single gene via GTF lookup.

        Args:
            gene: Gene object to fetch annotations for.

        Returns:
            Dictionary with annotation data or None if not found.
        """
        await self.ensure_bulk_data_loaded()

        annotation = self.lookup_gene(gene.approved_symbol)
        if not annotation:
            logger.sync_debug(
                "Gene not found in GTF data",
                gene_symbol=gene.approved_symbol,
            )
            return None

        logger.sync_debug(
            "Found Ensembl annotation from GTF",
            gene_symbol=gene.approved_symbol,
            gene_id=annotation.get("gene_id"),
            exon_count=annotation.get("exon_count"),
        )
        return annotation

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """Fetch annotations for multiple genes via GTF dict lookups.

        Args:
            genes: List of Gene objects.

        Returns:
            Dictionary mapping gene IDs to annotation data.
        """
        if not genes:
            return {}

        await self.ensure_bulk_data_loaded()

        results: dict[int, dict[str, Any]] = {}
        for gene in genes:
            annotation = self.lookup_gene(gene.approved_symbol)
            if annotation:
                results[gene.id] = annotation

        logger.sync_info(
            "Batch fetch completed (GTF lookup)",
            requested=len(genes),
            successful=len(results),
        )
        return results
