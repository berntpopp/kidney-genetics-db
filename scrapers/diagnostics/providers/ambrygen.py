"""
AmbryGen scraper - RenalNext panel.
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


class AmbryGenScraper(BaseDiagnosticScraper):
    """Scraper for AmbryGen - RenalNext panel"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.provider_id = "ambrygen"
        self.provider_name = "AmbryGen"
        self.provider_type = "single_panel"
        self.url = "https://www.ambrygen.com/providers/genetic-testing/12/nephrology/renalnext"
        self.use_browser = False
        
    def extract_genes(self, content: str) -> List[str]:
        """Extract genes from AmbryGen page"""
        soup = BeautifulSoup(content, 'html.parser')
        genes = []
        
        # AmbryGen typically lists genes in specific sections
        selectors = [
            'div.gene-list',
            'div.panel-genes',
            'table.genes-table tbody tr td',
            'div[class*="gene"]',
            'ul.gene-list li',
            'div.test-genes'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements:
                    text = elem.get_text()
                    # Look for gene symbols
                    potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                    for gene in potential_genes:
                        if 2 <= len(gene) <= 15:
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)
        
        # Look for genes in paragraphs that mention "genes"
        for p in soup.find_all('p'):
            text = p.get_text()
            if 'gene' in text.lower() and ('panel' in text.lower() or 'test' in text.lower()):
                potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                for gene in potential_genes:
                    if 2 <= len(gene) <= 15 and not gene.startswith(('HTTP', 'DNA', 'RNA')):
                        cleaned = clean_gene_symbol(gene)
                        if cleaned:
                            genes.append(cleaned)
        
        return list(set(genes))
    
    def run(self) -> ProviderData:
        """Run AmbryGen scraper"""
        logger.info("Starting AmbryGen scraper")
        
        errors = []
        gene_entries = []
        
        try:
            # Fetch content
            content = self.fetch_content(self.url)
            
            # Extract genes
            genes = self.extract_genes(content)
            
            if not genes:
                logger.warning("No genes found for AmbryGen RenalNext panel")
            
            # Create gene entries
            gene_entries = [
                GeneEntry(
                    symbol=gene,
                    panels=["RenalNext"],
                    occurrence_count=1,
                    confidence="high"
                )
                for gene in genes
            ]
            
            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)
            
        except Exception as e:
            logger.error(f"Error scraping AmbryGen: {e}")
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
                'panel_name': 'RenalNext',
                'description': 'Comprehensive kidney disease gene panel',
                'scraper_version': '1.0.0'
            },
            errors=errors if errors else None
        )
        
        # Save output
        self.save_output(provider_data)
        
        logger.info(f"AmbryGen scraping complete: {len(gene_entries)} genes")
        return provider_data


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = AmbryGenScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes")