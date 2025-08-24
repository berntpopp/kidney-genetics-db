"""Processor for PMID 33664247 - PDF file."""

import logging
import re
from pathlib import Path
from typing import List

from extractors.pdf_extractor import PdfExtractor
from utils import clean_gene_symbol


class PMID33664247Processor:
    """Process PMID 33664247: Australia and New Zealand renal gene panel."""

    def __init__(self):
        self.pmid = "33664247"
        self.logger = logging.getLogger(self.__class__.__name__)
        self.extractor = PdfExtractor()

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from PMID 33664247 PDF file.

        The PDF contains gene panels starting at line 8:
        - ADTKD panel at line 8
        - aHUS/C3 GN panel at line 9-10
        - Multiple other panels through line ~45

        We need to extract from line 8 onwards to capture all genes.

        Args:
            file_path: Path to PDF file

        Returns:
            List of gene symbols
        """
        try:
            # Extract lines from PDF - start from line 8 where gene lists begin
            lines = self.extractor.extract_lines(file_path, skip_lines=8)

            if not lines:
                self.logger.error("No lines extracted from PDF")
                return []

            genes = set()

            # Noise words to filter out - be careful not to filter actual gene names
            noise_patterns = [
                # Panel names and descriptive words (not genes)
                "Panel",
                "Gene",
                "syndrome",
                "Cystinosis",  # This is a disease name, CTNS is the gene
                "Nephronophthisis",
                "&",
                "related",
                "ciliopathies",
                "Nephrotic",
                "Tubulopathies",
                "list",
                # Document structure words
                "Supplementary",
                "Figure",
                "Table",
                "Distribution",
                # Technical terms
                "mutation",
                "types",
                "of",
                "variants",
                "uncertain",
                "significance",
                "VOUS",
                "probands",
                "Variant",
                "classification",
                "was",
                "based",
                "2015",
                "guidelines",
                "Abbreviated",
                "are",
                "as",
                "follows",
                "copy",
                "number",
                "variation",
                "indels",
                "insertions",
                "deletions",
                "or",
                "removed",  # e.g., "(PLG removed)"
                "bold",
                "included",
                "prior",
                "April",
                "2018",
                "testing",
            ]

            # Process each line
            for line in lines:
                # Remove parenthetical content like "(PLG removed)"
                line = re.sub(r"\([^)]*removed[^)]*\)", "", line)
                line = re.sub(r"\([^)]*bold[^)]*\)", "", line)

                # Split by various separators
                items = re.split(r"[,\s]+", line)

                for item in items:
                    # Clean the item
                    item = item.strip()

                    # Skip empty items
                    if not item:
                        continue

                    # Skip numeric items (except those that are part of gene names)
                    if item.isdigit() and item in ["1", "2", "3", "552"]:
                        continue

                    # Skip noise patterns
                    if any(noise in item for noise in noise_patterns):
                        continue

                    # Handle special cases with underscores
                    # C5_ex21 -> C5 (exon notation)
                    # But keep other underscores that might be part of the gene name
                    if "_ex" in item:  # Handle exon notation like C5_ex21
                        item = item.split("_ex")[0]
                    elif "_" in item and item.split("_")[1].isdigit():
                        # Remove numeric suffixes like GENE_1
                        item = item.split("_")[0]

                    # Clean and validate
                    gene = clean_gene_symbol(item)
                    if gene and self._is_valid_gene_symbol(gene):
                        genes.add(gene)

            gene_list = sorted(list(genes))
            self.logger.info(f"Extracted {len(gene_list)} genes from PMID {self.pmid}")

            return gene_list

        except Exception as e:
            self.logger.error(f"Error processing PMID {self.pmid}: {e}")
            return []

    def _is_valid_gene_symbol(self, symbol: str) -> bool:
        """Check if string is a valid gene symbol."""
        if not symbol or len(symbol) < 2 or len(symbol) > 15:
            return False

        # Should start with letter (or number for some special cases like C3, C5)
        if not (
            symbol[0].isalpha() or (len(symbol) > 1 and symbol[0] in "C" and symbol[1].isdigit())
        ):
            return False

        # Should be uppercase alphanumeric (allow hyphens and underscores for special cases)
        if not re.match(r"^[A-Z0-9][A-Z0-9\-_]*[A-Z0-9]?$", symbol):
            return False

        # Filter out known non-gene abbreviations
        non_genes = [
            "CNV",
            "VOUS",
            "ACMG",  # Technical terms
            "ADTKD",
            "ARPKD",
            "CAKUT",
            "BORS",
            "GN",  # Disease/syndrome abbreviations
            "NA",
            "NULL",
            "NONE",  # Data placeholders
        ]
        if symbol in non_genes:
            return False

        return True
