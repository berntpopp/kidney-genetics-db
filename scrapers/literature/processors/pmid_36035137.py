"""Processor for PMID 36035137 - Excel file."""

import logging
from pathlib import Path
from typing import List

from extractors.excel_extractor import ExcelExtractor
from utils import clean_gene_symbol


class PMID36035137Processor:
    """Process PMID 36035137: Analysis of chronic kidney disease patients."""

    def __init__(self):
        self.pmid = "36035137"
        self.logger = logging.getLogger(self.__class__.__name__)
        self.extractor = ExcelExtractor()

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from PMID 36035137 Excel file.

        Based on R script logic:
        - Read Excel with skip=1
        - Extract "Gene" column
        - Return unique sorted list

        Args:
            file_path: Path to Excel file

        Returns:
            List of gene symbols
        """
        try:
            # Extract with skip_rows=1 as per R script
            content = self.extractor.extract(file_path, skip_rows=1)

            if not content.get("success"):
                self.logger.error(f"Failed to extract content: {content.get('error')}")
                return []

            genes = set()
            headers = content.get("headers", [])
            data = content.get("data", [])

            # Find Gene column index
            gene_col_idx = None
            for idx, header in enumerate(headers):
                if header and "Gene" in str(header):
                    gene_col_idx = idx
                    break

            if gene_col_idx is None:
                # Try first column if no Gene header found
                self.logger.warning("Gene column not found by header, trying first column")
                gene_col_idx = 0

            # Extract genes from column
            for row in data:
                if gene_col_idx < len(row) and row[gene_col_idx]:
                    gene = clean_gene_symbol(str(row[gene_col_idx]))
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

        # Should be mostly uppercase letters and numbers
        if not symbol[0].isalpha():
            return False

        # Filter out common headers/noise
        excluded = {"GENE", "NAME", "SYMBOL", "ID", "TOTAL", "NA", "NULL"}
        if symbol.upper() in excluded:
            return False

        return True
