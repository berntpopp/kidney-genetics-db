"""Processor for PMID 34264297 - ZIP file containing Excel files."""

import logging
import re
import tempfile
import zipfile
from pathlib import Path
from typing import List

import openpyxl

from processors.filters import clean_and_validate_symbol, should_exclude_symbol
from utils import clean_gene_symbol


class PMID34264297Processor:
    """Process PMID 34264297: Genetic testing in chronic kidney disease."""

    def __init__(self):
        self.pmid = "34264297"
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from PMID 34264297 ZIP file.

        Based on R script logic:
        - Unzip and read ALL Excel files
        - Skip 2 rows in each Excel
        - Extract Gene column from each
        - Apply specific cleaning rules
        - Combine all genes

        Args:
            file_path: Path to ZIP file

        Returns:
            List of gene symbols
        """
        try:
            genes = set()

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract ZIP contents
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall(temp_path)
                    self.logger.debug(
                        f"Extracted {len(zip_ref.namelist())} files from ZIP"
                    )

                # Process each Excel file
                for excel_file in temp_path.glob("*.xlsx"):
                    self.logger.debug(f"Processing {excel_file.name}")

                    try:
                        wb = openpyxl.load_workbook(excel_file)
                        ws = wb.active

                        # Process rows (skip first 2 as per R script)
                        gene_col_idx = None
                        for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                            if row_idx < 2:  # Skip first 2 rows
                                continue

                            # First row after skip should be headers
                            if row_idx == 2:
                                # Find Gene column index
                                for col_idx, cell in enumerate(row):
                                    if cell and "Gene" in str(cell):
                                        gene_col_idx = col_idx
                                        self.logger.debug(
                                            f"Found Gene column at index {gene_col_idx}"
                                        )
                                        break
                                continue

                            # Extract gene from identified column
                            if gene_col_idx is not None and gene_col_idx < len(row):
                                gene_raw = row[gene_col_idx]

                                if gene_raw and str(gene_raw).strip():
                                    gene_raw = str(gene_raw).strip()

                                    # Apply cleaning rules from R script
                                    # Remove text after space, slash, or parenthesis
                                    gene_raw = re.split(r"[\s\/\(\*]", gene_raw)[0]

                                    # Remove asterisks
                                    gene_raw = gene_raw.replace("*", "")
                                    
                                    # Replace orf with ORF (fixed regex - was \borf\b which doesn't match C8orf37)
                                    gene_raw = re.sub(
                                        r"orf", "ORF", gene_raw, flags=re.IGNORECASE
                                    )

                                    # Clean and validate
                                    gene = clean_gene_symbol(gene_raw)

                                    # Additional filters from R script
                                    if not gene or gene == "":
                                        continue
                                    if re.search(
                                        r"[:-]", gene
                                    ):  # Skip if contains : or -
                                        continue
                                    if re.search(
                                        r"[a-z,]", gene
                                    ):  # Skip if contains lowercase or comma (after orf->ORF fix)
                                        continue

                                    if self._is_valid_gene_symbol(gene):
                                        genes.add(gene)

                        wb.close()

                    except Exception as e:
                        self.logger.warning(f"Error processing {excel_file.name}: {e}")
                        continue

            gene_list = sorted(list(genes))
            self.logger.info(f"Extracted {len(gene_list)} genes from PMID {self.pmid}")

            return gene_list

        except Exception as e:
            self.logger.error(f"Error processing PMID {self.pmid}: {e}")
            return []

    def _is_valid_gene_symbol(self, symbol: str) -> bool:
        """Check if string is a valid gene symbol."""
        # First apply common filters
        cleaned = clean_and_validate_symbol(symbol)
        if not cleaned:
            return False

        # Check against exclusion list
        if should_exclude_symbol(cleaned):
            return False

        # Should be uppercase alphanumeric
        if not cleaned[0].isalpha():
            return False

        # No lowercase letters (as per R script filter)
        if any(c.islower() for c in cleaned):
            return False

        return True
