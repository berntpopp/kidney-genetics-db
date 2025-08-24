"""Remaining processors - placeholder implementations."""

from pathlib import Path
from typing import List

from extractors.docx_extractor import DocxExtractor
from extractors.excel_extractor import ExcelExtractor
from extractors.pdf_extractor import PdfExtractor
from processors.base_processor import BaseProcessor
from utils import clean_gene_symbol


class PMID30476936Processor(BaseProcessor):
    """Process PMID 30476936 - Excel file."""

    def __init__(self):
        super().__init__("30476936")
        self.extractor = ExcelExtractor()

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from Excel - Gene Name column."""
        try:
            genes = self.extractor.extract_column(file_path, "Gene Name")
            valid_genes = []
            for gene in genes:
                gene = clean_gene_symbol(gene)
                if gene and self._is_valid_gene_symbol(gene):
                    valid_genes.append(gene)
            return sorted(list(set(valid_genes)))
        except Exception as e:
            self.logger.error(f"Error processing PMID {self.pmid}: {e}")
            return []


class PMID31509055Processor(BaseProcessor):
    """Process PMID 31509055 - PDF file."""

    def __init__(self):
        super().__init__("31509055")
        self.extractor = PdfExtractor()

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from PDF."""
        try:
            lines = self.extractor.extract_lines(file_path)
            genes = set()
            for line in lines:
                # Filter noise
                if any(x in line for x in ["Supplementary", "Table", "List", "genes", "panel"]):
                    continue
                items = line.split()
                for item in items:
                    gene = clean_gene_symbol(item.split("_")[0])  # Remove underscore suffixes
                    if gene and self._is_valid_gene_symbol(gene):
                        genes.add(gene)
            return sorted(list(genes))
        except Exception as e:
            self.logger.error(f"Error processing PMID {self.pmid}: {e}")
            return []


class PMID31822006Processor(BaseProcessor):
    """Process PMID 31822006 - PDF file."""

    def __init__(self):
        super().__init__("31822006")
        self.extractor = PdfExtractor()

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from PDF pages 1-9, with special handling for page 3."""
        try:
            genes = set()

            # Extract from pages 1-2 with original skip
            lines_1_2 = self.extractor.extract_lines(file_path, pages=[1, 2], skip_lines=31)
            for line in lines_1_2:
                parts = line.split()
                if parts:
                    gene = clean_gene_symbol(parts[0])
                    if gene and self._is_valid_gene_symbol(gene) and not gene.isdigit():
                        genes.add(gene)

            # Extract from page 3 with minimal skip (genes start at line 4)
            lines_3 = self.extractor.extract_lines(file_path, pages=[3], skip_lines=3)
            for line in lines_3:
                parts = line.split()
                if parts:
                    gene = clean_gene_symbol(parts[0])
                    if gene and self._is_valid_gene_symbol(gene) and not gene.isdigit():
                        genes.add(gene)

            # Extract from pages 4-9 normally
            lines_4_9 = self.extractor.extract_lines(
                file_path, pages=list(range(4, 10)), skip_lines=0
            )
            for line in lines_4_9:
                parts = line.split()
                if parts:
                    gene = clean_gene_symbol(parts[0])
                    if gene and self._is_valid_gene_symbol(gene) and not gene.isdigit():
                        genes.add(gene)

            return sorted(list(genes))
        except Exception as e:
            self.logger.error(f"Error processing PMID {self.pmid}: {e}")
            return []


class PMID29801666Processor(BaseProcessor):
    """Process PMID 29801666 - DOCX file."""

    def __init__(self):
        super().__init__("29801666")
        self.extractor = DocxExtractor()

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from DOCX table cell_id=1."""
        try:
            tables = self.extractor.extract_tables_with_metadata(file_path)
            genes = set()
            for table in tables:
                for cell in table.get("cells", []):
                    if cell.get("cell_id") == 1 or cell.get("text") and cell.get("text") != "Gene":
                        gene = clean_gene_symbol(cell.get("text", ""))
                        if gene and self._is_valid_gene_symbol(gene):
                            genes.add(gene)
            return sorted(list(genes))
        except Exception as e:
            self.logger.error(f"Error processing PMID {self.pmid}: {e}")
            return []


class PMID31027891Processor(BaseProcessor):
    """Process PMID 31027891 - DOCX file."""

    def __init__(self):
        super().__init__("31027891")
        self.extractor = DocxExtractor()

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from DOCX table cell_id=8."""
        try:
            tables = self.extractor.extract_tables_with_metadata(file_path)
            genes = set()
            for table in tables:
                for cell in table.get("cells", []):
                    if cell.get("cell_id") == 8 or (
                        cell.get("text") and "GENE SYMBOL" not in cell.get("text", "")
                    ):
                        text = cell.get("text", "")
                        # Split by comma
                        for item in text.split(", "):
                            gene = clean_gene_symbol(item)
                            if gene and self._is_valid_gene_symbol(gene):
                                genes.add(gene)
            return sorted(list(genes))
        except Exception as e:
            self.logger.error(f"Error processing PMID {self.pmid}: {e}")
            return []


class PMID26862157Processor(BaseProcessor):
    """Process PMID 26862157 - PDF file."""

    def __init__(self):
        super().__init__("26862157")
        self.extractor = PdfExtractor()

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from PDF pages 1-4."""
        try:
            lines = self.extractor.extract_lines(
                file_path, pages=[1, 2, 3, 4], skip_lines=4  # Fixed: was 9, should be 4
            )
            genes = set()
            for line in lines:
                # Take first word
                parts = line.split()
                if parts:
                    gene = clean_gene_symbol(parts[0])
                    gene = gene.replace("orf", "ORF")  # Replace orf with ORF
                    if gene and self._is_valid_gene_symbol(gene) and not gene.isdigit():
                        genes.add(gene)
            return sorted(list(genes))
        except Exception as e:
            self.logger.error(f"Error processing PMID {self.pmid}: {e}")
            return []


class PMID33532864Processor(BaseProcessor):
    """Process PMID 33532864 - DOCX file."""

    def __init__(self):
        super().__init__("33532864")
        self.extractor = DocxExtractor()

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from DOCX table, first 316 entries."""
        try:
            tables = self.extractor.extract_tables_with_metadata(file_path)
            genes = []
            for table in tables:
                for cell in table.get("cells", []):
                    if cell.get("cell_id") == 1 or (
                        cell.get("text") and cell.get("text") != "Gene"
                    ):
                        text = cell.get("text", "")
                        for item in text.split(", "):
                            gene = clean_gene_symbol(item)
                            if gene and self._is_valid_gene_symbol(gene):
                                genes.append(gene)
                                if len(genes) >= 316:  # Take first 316 as per R script
                                    return genes
            return genes
        except Exception as e:
            self.logger.error(f"Error processing PMID {self.pmid}: {e}")
            return []


class PMID35005812Processor(BaseProcessor):
    """Process PMID 35005812 - Excel file."""

    def __init__(self):
        super().__init__("35005812")
        self.extractor = ExcelExtractor()

    def process(self, file_path: Path) -> List[str]:
        """Extract genes from Excel column 2."""
        try:
            result = self.extractor.extract(file_path, skip_rows=1)
            genes = set()
            for row in result.get("data", []):
                if len(row) > 1 and row[1]:  # Column 2 (index 1)
                    gene = str(row[1]).split("(")[0].strip()  # Remove parentheses content
                    gene = clean_gene_symbol(gene)
                    if gene and self._is_valid_gene_symbol(gene):
                        genes.add(gene)
            return sorted(list(genes))
        except Exception as e:
            self.logger.error(f"Error processing PMID {self.pmid}: {e}")
            return []
