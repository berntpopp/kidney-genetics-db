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

        Based on R script logic:
        - Extract all text from PDF
        - Skip first 15 lines
        - Apply complex filtering rules
        - Remove specific strings and patterns

        Args:
            file_path: Path to PDF file

        Returns:
            List of gene symbols
        """
        try:
            # Extract lines from PDF
            lines = self.extractor.extract_lines(file_path, skip_lines=15)

            if not lines:
                self.logger.error("No lines extracted from PDF")
                return []

            genes = set()

            # Noise words to filter out (from R script)
            noise_patterns = [
                "Panel",
                "Gene",
                "ADTKD",
                "aHUS",
                "C3",
                "GN",
                "Alport",
                "syndrome",
                "ARPKD",
                "BORS",
                "CAKUT",
                "Cystinosis",
                "Nephronophthisis",
                "&",
                "related",
                "ciliopathies",
                "Nephrotic",
                "Tubulopathies",
                "list",
                "23",
                "PLG",
                "removed",
                "EVC",
                "Supplementary",
                "Figure",
                "Distribution",
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
                "ACMG",
                "guidelines",
                "Abbreviated",
                "are",
                "as",
                "follows",
                "CNV",
                "copy",
                "number",
                "variation",
                "indels",
                "insertions",
                "deletions",
                "or",
            ]

            # Process each line
            for line in lines:
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

                    # Remove underscore suffixes (e.g., GENE_1 -> GENE)
                    if "_" in item:
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

        # Should start with letter
        if not symbol[0].isalpha():
            return False

        # Should be uppercase alphanumeric
        if not re.match(r"^[A-Z][A-Z0-9\-]*[A-Z0-9]?$", symbol):
            return False

        # Additional filters for this specific paper
        if symbol in ["CNV", "VOUS", "ACMG", "ADTKD", "ARPKD", "CAKUT", "BORS"]:
            return False

        return True
