"""Excel file extractor."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl


class ExcelExtractor:
    """Extract content from Excel files."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract(
        self, file_path: Path, sheet_name: Optional[str] = None, skip_rows: int = 0
    ) -> Dict[str, Any]:
        """Extract content from Excel file.

        Args:
            file_path: Path to Excel file
            sheet_name: Name of sheet to extract (default: active sheet)
            skip_rows: Number of rows to skip from top

        Returns:
            Dictionary with extracted content
        """
        try:
            wb = openpyxl.load_workbook(file_path)

            if sheet_name:
                ws = wb[sheet_name]
            else:
                ws = wb.active

            # Extract all data
            data = []
            headers = []

            for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                if row_idx < skip_rows:
                    continue

                # First non-skipped row as headers if present
                if row_idx == skip_rows and any(row):
                    headers = [str(cell) if cell else "" for cell in row]
                else:
                    row_data = [cell for cell in row]
                    data.append(row_data)

            return {
                "headers": headers,
                "data": data,
                "sheet_name": ws.title,
                "success": True,
            }

        except Exception as e:
            self.logger.error(f"Error extracting Excel {file_path}: {e}")
            return {"success": False, "error": str(e)}

    def extract_column(
        self,
        file_path: Path,
        column: Any,
        skip_rows: int = 0,
        sheet_name: Optional[str] = None,
    ) -> List[str]:
        """Extract specific column from Excel file.

        Args:
            file_path: Path to Excel file
            column: Column identifier (letter like 'A' or index like 0 or header name)
            skip_rows: Number of rows to skip
            sheet_name: Sheet name (default: active)

        Returns:
            List of values from the column
        """
        try:
            result = self.extract(file_path, sheet_name, skip_rows)

            if not result.get("success"):
                return []

            data = result.get("data", [])
            headers = result.get("headers", [])

            # Determine column index
            col_idx = None

            if isinstance(column, int):
                col_idx = column
            elif isinstance(column, str):
                # Check if it's a header name
                if column in headers:
                    col_idx = headers.index(column)
                # Check if it's a column letter
                elif len(column) <= 2 and column.isalpha():
                    col_idx = openpyxl.utils.column_index_from_string(column) - 1

            if col_idx is None:
                self.logger.warning(f"Could not find column {column}")
                return []

            # Extract column values
            values = []
            for row in data:
                if col_idx < len(row) and row[col_idx] is not None:
                    values.append(str(row[col_idx]))

            return values

        except Exception as e:
            self.logger.error(f"Error extracting column from Excel {file_path}: {e}")
            return []
