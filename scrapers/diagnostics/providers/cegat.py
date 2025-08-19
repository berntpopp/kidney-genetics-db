"""
CeGaT scraper - CeGaT Kidney disease panel.
"""

from bs4 import BeautifulSoup
import re
from typing import List, Optional, Dict
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import GeneEntry, ProviderData
from utils import clean_gene_symbol

logger = logging.getLogger(__name__)


class CegatScraper(BaseDiagnosticScraper):
    """Scraper for CeGaT - Kidney disease panel"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.provider_id = "cegat"
        self.provider_name = "CeGaT"
        self.provider_type = "single_panel"
        self.url = "https://cegat.com/diagnostics/rare-diseases/kidney-diseases/"
        
    def extract_genes(self, content: str) -> List[str]:
        """Extract genes from CeGaT page"""
        soup = BeautifulSoup(content, 'html.parser')
        genes = []
        
        # CeGaT typically lists genes in a structured format
        # Try to find gene table or list
        selectors = [
            'div.gene-panel-content',
            'div.panel-body',
            'table.gene-table',
            'div.genes',
            'div[class*="gene-list"]',
            'ul.gene-list li'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements:
                    text = elem.get_text()
                    # Look for gene symbols (typically uppercase, alphanumeric)
                    potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                    for gene in potential_genes:
                        if 2 <= len(gene) <= 15:
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)
        
        # If no structured data, look for genes in paragraphs
        if not genes:
            # Look for content sections that might contain gene lists
            for element in soup.find_all(['p', 'div']):
                text = element.get_text()
                # CeGaT often lists genes separated by commas or in parentheses
                if ',' in text or '(' in text:
                    # Extract potential gene symbols
                    potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                    for gene in potential_genes:
                        if 2 <= len(gene) <= 15 and not gene.startswith(('HTTP', 'DNA', 'RNA')):
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)
        
        return list(set(genes))
    
    def run(self) -> ProviderData:
        """Run CeGaT scraper"""
        logger.info("Starting CeGaT scraper")
        
        errors = []
        gene_entries = []
        
        try:
            # Fetch content
            content = self.fetch_content(self.url)
            
            # Extract genes
            genes = self.extract_genes(content)
            
            if not genes:
                logger.warning("No genes found for CeGaT Kidney disease panel")
            
            # Create gene entries
            gene_entries = [
                GeneEntry(
                    symbol=gene,
                    panels=["Kidney Disease Panel"],
                    occurrence_count=1,
                    confidence="high"
                )
                for gene in genes
            ]
            
            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)
            
        except Exception as e:
            logger.error(f"Error scraping CeGaT: {e}")
            errors.append(str(e))
        
        # Create provider data
        provider_data = ProviderData(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_type=self.provider_type,
            main_url=self.url,
            total_panels=1,
            sub_panels=None,
            total_unique_genes=len(gene_entries),
            genes=gene_entries,
            metadata={
                'panel_name': 'Kidney Disease Panel',
                'scraper_version': '1.0.0'
            },
            errors=errors if errors else None
        )
        
        # Save output
        self.save_output(provider_data)
        
        logger.info(f"CeGaT scraping complete: {len(gene_entries)} genes")
        return provider_data


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = CegatScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes")