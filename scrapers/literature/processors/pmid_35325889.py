"""Processor for PMID 35325889 - DOCX file."""

import logging
import re
from pathlib import Path
from typing import List

from extractors.docx_extractor import DocxExtractor
from utils import clean_gene_symbol


class PMID35325889Processor:
    """Process PMID 35325889: Genetic Etiologies for Chronic Kidney Disease."""

    def __init__(self):
        self.pmid = "35325889"
        self.logger = logging.getLogger(self.__class__.__name__)
        self.extractor = DocxExtractor()

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from PMID 35325889 DOCX file.

        Based on R script logic:
        - Find paragraph containing "ABCC6"
        - Split by ", " separator
        - Return unique gene list

        Args:
            file_path: Path to DOCX file

        Returns:
            List of gene symbols
        """
        try:
            # Extract content
            content = self.extractor.extract(file_path)

            if not content.get("success"):
                self.logger.error(f"Failed to extract content: {content.get('error')}")
                return []

            genes = set()

            # Search in paragraphs
            for paragraph in content.get("paragraphs", []):
                # Look for paragraph containing ABCC6 (marker gene)
                if "ABCC6" in paragraph:
                    # Split by comma and space
                    potential_genes = paragraph.split(", ")

                    for item in potential_genes:
                        # Clean and validate gene symbol
                        gene = clean_gene_symbol(item)
                        if gene and self._is_valid_gene_symbol(gene):
                            genes.add(gene)

            # Also check tables in case genes are there
            for table in content.get("tables", []):
                for row in table:
                    for cell in row:
                        # Look for cells with gene-like content
                        if cell and "ABCC6" in cell:
                            # Found the gene list
                            potential_genes = cell.split(", ")
                            for item in potential_genes:
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
        """Check if string is a valid gene symbol.

        Args:
            symbol: Potential gene symbol

        Returns:
            True if valid gene symbol
        """
        # Basic validation rules
        if not symbol:
            return False

        # Length check (2-15 characters is reasonable)
        if len(symbol) < 2 or len(symbol) > 15:
            return False

        # Should start with letter
        if not symbol[0].isalpha():
            return False

        # Should be mostly uppercase letters and numbers
        if not re.match(r"^[A-Z][A-Z0-9\-]*[A-Z0-9]?$", symbol):
            return False

        # Filter out common false positives
        excluded = {"TABLE", "FIGURE", "SUPPLEMENTARY", "TABLE1", "GENE", "PANEL"}
        if symbol.upper() in excluded:
            return False

        return True
