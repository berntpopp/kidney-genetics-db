"""
GTEx annotation source for gene expression data.

Uses bulk GCT download of median gene expression for fast batch processing.
No per-gene API calls — the GCT file covers all genes measured by GTEx.
"""

import csv
import re
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

logger = get_logger(__name__)

# Pre-compiled regex for parenthetical clean-up in tissue IDs
_PARENS_RE = re.compile(r"[()]")


def _normalise_tissue_id(raw: str) -> str:
    """Convert a GCT human-readable tissue name to GTEx API-style ID.

    Examples::

        "Kidney - Cortex"                        → "Kidney_Cortex"
        "Adipose - Visceral (Omentum)"           → "Adipose_Visceral_Omentum"
        "Brain - Anterior cingulate cortex (BA24)" → "Brain_Anterior_cingulate_cortex_BA24"
        "Brain - Spinal cord (cervical c-1)"     → "Brain_Spinal_cord_cervical_c-1"
        "Whole Blood"                            → "Whole_Blood"
    """
    # 1. Replace " - " separator with underscore
    s = raw.replace(" - ", "_")
    # 2. Strip parentheses (keep content)
    s = _PARENS_RE.sub("", s)
    # 3. Replace remaining spaces with underscores
    s = s.replace(" ", "_")
    # 4. Collapse any double underscores left from stripping
    while "__" in s:
        s = s.replace("__", "_")
    # 5. Strip trailing underscores
    return s.rstrip("_")


class GTExAnnotationSource(BulkDataSourceMixin, BaseAnnotationSource):
    """
    GTEx (Genotype-Tissue Expression) annotation source.

    Uses bulk GCT download of median gene expression for fast batch
    processing.  No per-gene API calls required.
    """

    source_name = "gtex"
    display_name = "GTEx"
    version = "v8"

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
                # GCT uses human-readable names ("Kidney - Cortex") but the
                # GTEx API / frontend expects tissueSiteDetailId format
                # ("Kidney_Cortex"), so normalise: strip, replace " - " / " "
                # with "_", then collapse parenthetical details.
                tissues: dict[str, dict[str, Any]] = {}
                for i, tissue_id in enumerate(tissue_ids):
                    val = row[i + 2] if i + 2 < len(row) else ""
                    if val and val != "NA":
                        try:
                            # Normalise GCT tissue name to API-style ID
                            norm_id = _normalise_tissue_id(tissue_id)
                            tissues[norm_id] = {
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
        """Fetch GTEx expression data for a single gene via bulk lookup."""
        if not gene.approved_symbol:
            return None

        if self._bulk_data is not None:
            return self.lookup_gene(gene.approved_symbol)
        return None

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """Fetch annotations for multiple genes via bulk data lookup.

        Loads the GCT bulk file once, then does fast local lookups by
        gene symbol. Genes not found in the GCT file simply have no
        GTEx expression data (the GCT covers all measured genes).
        """
        try:
            await self.ensure_bulk_data_loaded()
        except Exception as e:
            logger.sync_warning(f"Failed to load GTEx bulk data: {e}")
            return {}

        results: dict[int, dict[str, Any]] = {}
        misses = 0

        for gene in genes:
            if self._bulk_data is not None and gene.approved_symbol:
                bulk_result = self.lookup_gene(gene.approved_symbol)
                if bulk_result is not None:
                    results[gene.id] = bulk_result
                else:
                    misses += 1

        if misses:
            logger.sync_debug(
                "GTEx bulk lookup complete",
                hits=len(results),
                misses=misses,
            )

        return results
