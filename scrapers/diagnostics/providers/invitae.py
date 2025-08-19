"""
Invitae scraper - Comprehensive Renal Genes Panel.
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


class InvitaeScraper(BaseDiagnosticScraper):
    """Scraper for Invitae - Comprehensive Renal Genes Panel"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.provider_id = "invitae"
        self.provider_name = "Invitae"
        self.provider_type = "single_panel"
        self.url = "https://www.invitae.com/us/providers/test-catalog/test-633100"  # Expanded Renal Disease Panel
        self.use_browser = True  # Invitae often requires JavaScript
        
    def extract_genes(self, content: str) -> List[str]:
        """Extract genes from Invitae page"""
        soup = BeautifulSoup(content, 'html.parser')
        genes = []
        
        # Invitae typically shows genes in a dedicated section
        # Look for gene list containers
        selectors = [
            'div.gene-list',
            'div[data-testid*="gene"]',
            'div.test-genes',
            'section.genes',
            'div.panel-genes',
            'table.genes-table tbody tr',
            'ul.gene-list li'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements:
                    text = elem.get_text()
                    # Extract gene symbols
                    potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                    for gene in potential_genes:
                        if 2 <= len(gene) <= 15:
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)
        
        # Fallback: look for genes in text content
        if not genes:
            # Invitae often has genes in specific sections
            for element in soup.find_all(['div', 'p', 'span']):
                text = element.get_text()
                # Look for sections that mention genes
                if any(keyword in text.lower() for keyword in ['genes analyzed', 'gene list', 'includes']):
                    # Extract gene symbols
                    potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                    for gene in potential_genes:
                        if 2 <= len(gene) <= 15 and not gene.startswith(('HTTP', 'DNA', 'RNA', 'TEST')):
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)
        
        # Additional pattern: genes often appear in italics
        italic_elements = soup.find_all(['i', 'em'])
        for elem in italic_elements:
            text = elem.get_text().strip()
            cleaned = clean_gene_symbol(text)
            if cleaned and 2 <= len(cleaned) <= 15:
                genes.append(cleaned)
        
        return list(set(genes))
    
    def run(self) -> ProviderData:
        """Run Invitae scraper"""
        logger.info("Starting Invitae scraper")
        
        errors = []
        gene_entries = []
        
        try:
            # Fetch content (using browser due to JavaScript)
            content = self.fetch_content(self.url)
            
            # Extract genes
            genes = self.extract_genes(content)
            
            if not genes:
                logger.warning("No genes found for Invitae Comprehensive Renal Genes Panel")
            
            # Create gene entries
            gene_entries = [
                GeneEntry(
                    symbol=gene,
                    panels=["Comprehensive Renal Genes Panel"],
                    occurrence_count=1,
                    confidence="high"
                )
                for gene in genes
            ]
            
            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)
            
        except Exception as e:
            logger.error(f"Error scraping Invitae: {e}")
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
                'panel_name': 'Comprehensive Renal Genes Panel',
                'test_code': '03401',
                'scraper_version': '1.0.0'
            },
            errors=errors if errors else None
        )
        
        # Save output
        self.save_output(provider_data)
        
        logger.info(f"Invitae scraping complete: {len(gene_entries)} genes")
        return provider_data


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = InvitaeScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes")