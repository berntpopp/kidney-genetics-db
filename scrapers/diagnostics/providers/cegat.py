"""
CeGaT scraper - CeGaT Kidney disease panel.
"""

import logging
import os
import sys
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import GeneEntry, ProviderData

logger = logging.getLogger(__name__)

class CegatScraper(BaseDiagnosticScraper):
    """Scraper for CeGaT - Kidney disease panel"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config, provider_id="cegat")
        self.provider_name = "CeGaT"
        self.provider_type = "single_panel"
        self.logger.debug(f"Initialized CeGaT scraper with URL: {self.url}")

    def extract_genes(self, content: str) -> List[str]:
        """Return the comma-separated <em> list under the "Gene Directory" heading.

        Only that element is read: free page text produced false symbols (ACMG, ENDE, II).
        """
        soup = BeautifulSoup(content, 'html.parser')
        heading = soup.find(
            ['h1', 'h2', 'h3', 'h4'], string=lambda s: s and s.strip().startswith('Gene Directory')
        )
        gene_list = heading.find_next('em') if heading else None
        if not gene_list:
            return []
        symbols = (s.strip() for s in gene_list.get_text(' ').split(','))
        return list(dict.fromkeys(s for s in symbols if s))

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

            # Create filtered gene entries
            gene_entries = self.create_filtered_gene_entries(
                gene_symbols=genes,
                panel_names=["Kidney Disease Panel"]
            )

            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)

        except Exception as e:
            logger.error(f"Error scraping CeGaT: {e}")
            errors.append(str(e))

        # Create provider data
        provider_data = ProviderData(
            id=self.provider_id,
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
                'scraper_version': '1.1.0'
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
