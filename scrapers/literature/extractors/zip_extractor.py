"""ZIP file extractor."""

import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List

from .excel_extractor import ExcelExtractor


class ZipExtractor:
    """Extract content from ZIP files."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.excel_extractor = ExcelExtractor()

    def extract(self, file_path: Path) -> Dict[str, Any]:
        """Extract and process files from ZIP archive.

        Args:
            file_path: Path to ZIP file

        Returns:
            Dictionary with extracted content from all files
        """
        try:
            results = []

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract ZIP contents
                with zipfile.ZipFile(file_path, "r") as zip_ref:
                    zip_ref.extractall(temp_path)
                    file_list = zip_ref.namelist()

                # Process each file
                for file_name in file_list:
                    extracted_file = temp_path / file_name

                    if not extracted_file.is_file():
                        continue

                    # Process based on file extension
                    if file_name.endswith((".xlsx", ".xls")):
                        result = self.excel_extractor.extract(extracted_file)
                        result["filename"] = file_name
                        results.append(result)
                    else:
                        self.logger.debug(f"Skipping unsupported file type: {file_name}")

                return {
                    "files": file_list,
                    "results": results,
                    "success": True,
                }

        except Exception as e:
            self.logger.error(f"Error extracting ZIP {file_path}: {e}")
            return {"success": False, "error": str(e)}

    def extract_excel_files(self, file_path: Path, skip_rows: int = 0) -> List[Dict[str, Any]]:
        """Extract all Excel files from ZIP archive.

        Args:
            file_path: Path to ZIP file
            skip_rows: Rows to skip in Excel files

        Returns:
            List of Excel extraction results
        """
        result = self.extract(file_path)

        if not result.get("success"):
            return []

        excel_results = []
        for file_result in result.get("results", []):
            if file_result.get("success"):
                excel_results.append(file_result)

        return excel_results
