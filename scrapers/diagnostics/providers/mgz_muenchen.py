"""
MGZ München scraper - Molecular genetics kidney diseases panel.
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

class MGZMuenchenScraper(BaseDiagnosticScraper):
    """Scraper for MGZ München - Kidney diseases panel"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config, provider_id="mgz_muenchen")
        self.provider_name = "MGZ München"
        self.provider_type = "single_panel"

    def extract_genes(self, content: str) -> List[str]:
        """Extract genes from MGZ München page"""
        soup = BeautifulSoup(content, 'html.parser')
        genes = []

        # German site - look for gene lists in various formats
        # MGZ typically lists genes in tables or lists
        selectors = [
            'table.gene-panel',
            'div.gene-list',
            'div.panel-content',
            'table tbody tr',
            'ul.genes li',
            'div[class*="gen"]'
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

        # Look for genes in table cells specifically
        for td in soup.find_all('td'):
            text = td.get_text().strip()
            # German sites might have gene names in specific formats
            if re.match(r'^[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*$', text):
                cleaned = clean_gene_symbol(text)
                if cleaned and 2 <= len(cleaned) <= 15:
                    genes.append(cleaned)

        # Fallback: search in paragraphs and divs
        if not genes:
            for element in soup.find_all(['p', 'div', 'li']):
                text = element.get_text()
                # Look for gene symbols, avoiding German words
                if any(char.isdigit() for char in text) or ',' in text:
                    potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                    for gene in potential_genes:
                        # Filter out common German abbreviations
                        if (2 <= len(gene) <= 15 and
                            not gene.startswith(('HTTP', 'DNA', 'RNA', 'NGS', 'PDF', 'FAQ'))):
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)

        return list(set(genes))

    def run(self) -> ProviderData:
        """Run MGZ München scraper"""
        logger.info("Starting MGZ München scraper")

        errors = []
        gene_entries = []

        try:
            # Fetch content
            content = self.fetch_content(self.url)

            # Extract genes
            genes = self.extract_genes(content)

            if not genes:
                logger.warning("No genes found for MGZ München kidney panel")

            # Create gene entries
            gene_entries = [
                GeneEntry(
                    symbol=gene,
                    panels=["Nierenerkrankungen Panel"],
                    occurrence_count=1
                )
                for gene in genes
            ]

            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)

        except Exception as e:
            logger.error(f"Error scraping MGZ München: {e}")
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
                'panel_name': 'Molekulargenetik Nierenerkrankungen',
                'language': 'de',
                'scraper_version': '1.0.0'
            },
            errors=errors if errors else None
        )

        # Save output
        self.save_output(provider_data)

        logger.info(f"MGZ München scraping complete: {len(gene_entries)} genes")
        return provider_data

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = MGZMuenchenScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes")
