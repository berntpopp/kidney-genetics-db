"""PDF file extractor."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pdfplumber


class PdfExtractor:
    """Extract content from PDF files."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract(self, file_path: Path, pages: Optional[List[int]] = None) -> Dict[str, Any]:
        """Extract text content from PDF file.

        Args:
            file_path: Path to PDF file
            pages: List of page numbers to extract (1-indexed), None for all

        Returns:
            Dictionary with extracted content
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                text_pages = []

                # Determine which pages to extract
                if pages:
                    page_indices = [p - 1 for p in pages if 0 <= p - 1 < len(pdf.pages)]
                else:
                    page_indices = range(len(pdf.pages))

                for page_idx in page_indices:
                    page = pdf.pages[page_idx]
                    text = page.extract_text()
                    if text:
                        text_pages.append(text)

                # Combine all pages
                full_text = "\n".join(text_pages)

                return {
                    "text": full_text,
                    "pages": text_pages,
                    "page_count": len(pdf.pages),
                    "success": True,
                }

        except Exception as e:
            self.logger.error(f"Error extracting PDF {file_path}: {e}")
            return {"success": False, "error": str(e)}

    def extract_lines(
        self, file_path: Path, pages: Optional[List[int]] = None, skip_lines: int = 0
    ) -> List[str]:
        """Extract text as lines from PDF file.

        Args:
            file_path: Path to PDF file
            pages: Page numbers to extract (1-indexed)
            skip_lines: Number of lines to skip from beginning

        Returns:
            List of text lines
        """
        result = self.extract(file_path, pages)

        if not result.get("success"):
            return []

        text = result.get("text", "")
        lines = text.split("\n")

        # Skip lines and clean
        lines = [line.strip() for line in lines[skip_lines:] if line.strip()]

        return lines

    def extract_tables(
        self, file_path: Path, pages: Optional[List[int]] = None
    ) -> List[List[List[str]]]:
        """Extract tables from PDF file.

        Args:
            file_path: Path to PDF file
            pages: Page numbers to extract tables from

        Returns:
            List of tables (each table is a list of rows)
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                all_tables = []

                # Determine which pages to extract
                if pages:
                    page_indices = [p - 1 for p in pages if 0 <= p - 1 < len(pdf.pages)]
                else:
                    page_indices = range(len(pdf.pages))

                for page_idx in page_indices:
                    page = pdf.pages[page_idx]
                    tables = page.extract_tables()

                    for table in tables:
                        if table:
                            # Clean table data
                            cleaned_table = []
                            for row in table:
                                cleaned_row = [str(cell) if cell else "" for cell in row]
                                cleaned_table.append(cleaned_row)
                            all_tables.append(cleaned_table)

                return all_tables

        except Exception as e:
            self.logger.error(f"Error extracting tables from PDF {file_path}: {e}")
            return []
