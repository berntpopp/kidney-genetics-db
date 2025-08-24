"""
Centogene scraper - CentoNephro panel.
"""

import logging
import os
import re
import sys
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import GeneEntry, ProviderData
from utils import clean_gene_symbol

logger = logging.getLogger(__name__)

class CentogeneScraper(BaseDiagnosticScraper):
    """Scraper for Centogene - CentoNephro panel"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config, provider_id="centogene")
        self.provider_name = "Centogene"
        self.provider_type = "single_panel"
        self.use_browser = True  # JavaScript-heavy page
        self.logger.debug(f"Initialized Centogene scraper with URL: {self.url}")

    def extract_genes(self, content: str) -> List[str]:
        """Extract genes from Centogene page"""
        soup = BeautifulSoup(content, 'html.parser')
        genes = []

        # Look for gene list in various contexts
        # Try to find gene table or list
        selectors = [
            'table.genes-table',
            'div.gene-list',
            'div.panel-genes',
            'div.test-genes',
            'table tbody tr',
            'div[class*="gene"]'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements:
                    text = elem.get_text()
                    # Look for gene symbols
                    potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                    for gene in potential_genes:
                        if 2 <= len(gene) <= 15 and not gene.startswith('HTTP'):
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)

        # If no structured data found, search for gene patterns in text
        if not genes:
            # Look for sections mentioning genes
            for element in soup.find_all(['p', 'div', 'span', 'li']):
                text = element.get_text()
                if any(keyword in text.lower() for keyword in ['gene', 'panel', 'includes', 'covers']):
                    potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                    for gene in potential_genes:
                        if 2 <= len(gene) <= 15 and not gene.startswith(('HTTP', 'DNA', 'RNA', 'NGS')):
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)

        return list(set(genes))

    def run(self) -> ProviderData:
        """Run Centogene scraper"""
        logger.info("Starting Centogene scraper")

        errors = []
        gene_entries = []

        try:
            # Fetch content
            content = self.fetch_content(self.url)

            # Extract genes
            genes = self.extract_genes(content)

            if not genes:
                logger.warning("No genes found for Centogene CentoNephro panel")

            # Create gene entries
            gene_entries = [
                GeneEntry(
                    symbol=gene,
                    panels=["CentoNephro"],
                    occurrence_count=1
                )
                for gene in genes
            ]

            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)

        except Exception as e:
            logger.error(f"Error scraping Centogene: {e}")
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
                'panel_name': 'CentoNephro',
                'scraper_version': '1.0.0'
            },
            errors=errors if errors else None
        )

        # Save output
        self.save_output(provider_data)

        logger.info(f"Centogene scraping complete: {len(gene_entries)} genes")
        return provider_data

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = CentogeneScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes")
