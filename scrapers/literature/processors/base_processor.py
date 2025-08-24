"""Base processor class for common functionality."""

import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from processors.filters import clean_and_validate_symbol, should_exclude_symbol


class BaseProcessor(ABC):
    """Base class for all publication processors."""

    def __init__(self, pmid: str):
        self.pmid = pmid
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def process(self, file_path: Path) -> List[str]:
        """Process publication file and extract genes."""
        pass

    def _is_valid_gene_symbol(self, symbol: str) -> bool:
        """Check if string is a valid gene symbol.

        Args:
            symbol: Potential gene symbol

        Returns:
            True if valid gene symbol
        """
        # First clean and validate using common filters
        cleaned = clean_and_validate_symbol(symbol)
        if not cleaned:
            return False

        # Additional validation - should be mostly uppercase alphanumeric
        if not re.match(r"^[A-Z][A-Z0-9\-]*[A-Z0-9]?$", cleaned):
            return False

        # Check against exclusion list
        if should_exclude_symbol(cleaned):
            return False

        return True
