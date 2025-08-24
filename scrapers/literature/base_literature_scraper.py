"""Base class for literature scraping."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
import yaml

from schemas import GeneEntry
from utils import get_hgnc_normalizer


class BaseLiteratureScraper:
    """Base class for literature scraping with common functionality."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the base scraper.
        
        Args:
            config: Optional configuration dictionary
        """
        # Load configuration
        self.config = self._load_config(config)
        
        # Setup directories
        self.base_dir = Path(__file__).parent
        self.data_dir = self.base_dir / self.config.get("data_dir", "data")
        self.output_dir = self.base_dir / self.config.get("output_dir", "output")
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Load publications metadata
        self.publications_metadata = self._load_publications_metadata()
        
        # Initialize HGNC normalizer
        self.hgnc_normalizer = get_hgnc_normalizer()
        
        self.logger.info(f"Initialized literature scraper with {len(self.publications_metadata)} publications")
    
    def _load_config(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Load configuration from file or use provided config.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            Configuration dictionary
        """
        if config:
            return config
            
        config_file = Path(__file__).parent / "config" / "config.yaml"
        if config_file.exists():
            with open(config_file, "r") as f:
                return yaml.safe_load(f) or {}
        
        # Default configuration
        return {
            "data_dir": "data",
            "output_dir": "output",
            "logging": {"level": "INFO"},
            "processing": {"normalize_genes": True, "batch_size": 50}
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration.
        
        Returns:
            Logger instance
        """
        # Create logs directory
        log_dir = self.base_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Configure logger
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(self.config.get("logging", {}).get("level", "INFO"))
        
        # Remove existing handlers
        logger.handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"literature_scraper_{timestamp}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _load_publications_metadata(self) -> List[Dict[str, Any]]:
        """Load publications metadata from Excel file.
        
        Returns:
            List of publication metadata dictionaries
        """
        excel_file = self.data_dir / "230220_Kidney_Genes_Publication_List.xlsx"
        
        if not excel_file.exists():
            self.logger.error(f"Excel file not found: {excel_file}")
            return []
        
        try:
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active
            
            # Find header row (contains "PMID")
            header_row = None
            headers = []
            for row_idx in range(1, 20):
                row = [cell.value for cell in sheet[row_idx]]
                if any("PMID" in str(cell) for cell in row if cell):
                    header_row = row_idx
                    headers = row
                    break
            
            if not header_row:
                self.logger.error("Could not find header row with PMID")
                return []
            
            # Extract data rows
            publications = []
            for row_idx in range(header_row + 1, sheet.max_row + 1):
                row = [cell.value for cell in sheet[row_idx]]
                
                # Skip empty rows
                if not any(row):
                    continue
                
                # Create publication dict
                pub_data = {}
                for idx, header in enumerate(headers):
                    if header and idx < len(row):
                        pub_data[header] = row[idx]
                
                # Only include if has PMID
                if pub_data.get("PMID"):
                    publications.append(pub_data)
            
            self.logger.info(f"Loaded {len(publications)} publications from Excel")
            return publications
            
        except Exception as e:
            self.logger.error(f"Error loading Excel file: {e}")
            return []
    
    def normalize_genes(self, gene_entries: List[GeneEntry]) -> List[GeneEntry]:
        """Normalize gene symbols using HGNC.
        
        Args:
            gene_entries: List of gene entries to normalize
            
        Returns:
            List of normalized gene entries
        """
        if not self.config.get("processing", {}).get("normalize_genes", True):
            return gene_entries
        
        normalized_entries = []
        
        for entry in gene_entries:
            # Normalize the symbol
            result = self.hgnc_normalizer.normalize_symbol(entry.symbol)
            
            if result.get("found"):
                # Update entry with HGNC data
                entry.hgnc_id = result.get("hgnc_id")
                entry.approved_symbol = result.get("approved_symbol")
                entry.reported_symbol = entry.symbol  # Save original
                entry.symbol = result.get("approved_symbol")  # Use approved symbol
            else:
                # Keep original symbol if not found
                entry.reported_symbol = entry.symbol
                self.logger.debug(f"Gene symbol not found in HGNC: {entry.symbol}")
            
            normalized_entries.append(entry)
        
        return normalized_entries
    
    def save_output(self, data: Any, filename: str = None):
        """Save output data to JSON file.
        
        Args:
            data: Data to save (must have model_dump() method or be JSON serializable)
            filename: Optional filename (defaults to date-based name)
        """
        # Create output directory
        date_dir = self.output_dir / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine filename
        if not filename:
            filename = f"literature_{datetime.now().strftime('%H%M%S')}.json"
        
        output_file = date_dir / filename
        
        # Convert data to dict if needed
        if hasattr(data, "model_dump"):
            data_dict = data.model_dump()
        else:
            data_dict = data
        
        # Save to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, indent=2, default=str)
        
        self.logger.info(f"Saved output to {output_file}")
    
    def run(self):
        """Run the scraper. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement run() method")