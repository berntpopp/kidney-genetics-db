"""
Invitae scraper - Comprehensive Renal Genes Panel.
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

class InvitaeScraper(BaseDiagnosticScraper):
    """Scraper for Invitae - Comprehensive Renal Genes Panel"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config, provider_id="invitae")
        self.provider_name = "Invitae"
        self.provider_type = "single_panel"
        self.use_browser = True  # Invitae often requires JavaScript
        self.logger.debug(f"Initialized Invitae scraper with URL: {self.url}")

    def extract_genes(self, content: str) -> List[str]:
        """Extract genes from Invitae page"""
        soup = BeautifulSoup(content, 'html.parser')
        genes = []

        # Save raw HTML for debugging
        self._save_raw_data(content, self.url, f"{self.provider_id}_page")
        self.logger.debug(f"Saved raw HTML, {len(content)} characters")

        # Primary method: Look for meta tag with genes list
        meta_genes = soup.find('meta', {'name': 'genes'})
        if meta_genes and meta_genes.get('content'):
            # Split comma-separated gene list
            gene_list = meta_genes['content'].split(',')
            for gene in gene_list:
                gene = gene.strip()
                if gene:
                    cleaned = clean_gene_symbol(gene)
                    if cleaned:
                        genes.append(cleaned)
                        self.logger.debug(f"Found gene from meta tag: {cleaned}")

            if genes:
                self.logger.info(f"Extracted {len(genes)} genes from meta tag")

        # Fallback: Look for table rows with gene data
        if not genes:
            self.logger.debug("No genes found in meta tag, trying table extraction")
            table_rows = soup.find_all('tr')
            for row in table_rows:
                cells = row.find_all('td')
                if cells and len(cells) >= 2:  # Ensure it's a data row
                    gene_text = cells[0].get_text().strip()
                    # Remove asterisks and other annotations
                    gene_text = gene_text.replace('*', '').strip()
                    # Validate it looks like a gene symbol
                    # Allow letters, numbers, and 'orf' (e.g., C8orf37, COL4A1, etc.)
                    if gene_text and re.match(r'^[A-Z][A-Za-z0-9\-]+$', gene_text) and 2 <= len(gene_text) <= 15:
                        cleaned = clean_gene_symbol(gene_text)
                        if cleaned:
                            genes.append(cleaned)
                            self.logger.debug(f"Found gene from table: {cleaned}")

        # Additional fallback: Try other selectors if no genes found
        if not genes:
            self.logger.debug("No genes found in table, trying other selectors")
            selectors = [
                'div.gene-list',
                'div[data-testid*="gene"]',
                'div.test-genes',
                'section.genes',
                'div.panel-genes',
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

        unique_genes = list(set(genes))
        self.logger.info(f"Extracted {len(unique_genes)} unique genes from Invitae")
        return unique_genes

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
                    occurrence_count=1
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
