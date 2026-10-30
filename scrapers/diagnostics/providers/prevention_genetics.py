"""
PreventionGenetics scraper - Comprehensive Kidney Disease Panel.
"""

import json
import logging
import os
import re
import sys
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import ProviderData

logger = logging.getLogger(__name__)

class PreventionGeneticsScraper(BaseDiagnosticScraper):
    """Scraper for PreventionGenetics - Comprehensive Kidney Disease Panel"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config, provider_id="prevention_genetics")
        self.provider_name = "PreventionGenetics"
        self.provider_type = "single_panel"
        self.use_browser = False  # gene list is embedded in the server-rendered page
        self.display_name = self.scraper_config.get("display_name", "")
        self.logger.debug(f"Initialized PreventionGenetics scraper with URL: {self.url}")

    def extract_genes(self, content: str) -> List[str]:
        """Return officialGeneSymbol of the geneList in the testHeaderBlock named display_name.

        The page embeds this test and its related tests as escaped Next.js flight data; each
        test carries a testHeaderBlock with displayName and geneList.
        """
        data = content.replace('\\"', '"')
        for block in re.finditer(r'"testHeaderBlock":\{', data):
            start = data.index('"geneList":', block.end())
            name = re.search(r'"displayName":"([^"]*)"', data[block.end():start])
            if name and name.group(1) == self.display_name:
                gene_list, _ = json.JSONDecoder().raw_decode(data, start + len('"geneList":'))
                return list(dict.fromkeys(g["officialGeneSymbol"] for g in gene_list))
        return []

    def run(self) -> ProviderData:
        """Run PreventionGenetics scraper"""
        logger.info("Starting PreventionGenetics scraper")

        errors = []
        gene_entries = []

        try:
            content = self.fetch_content(self.url)

            # Extract genes
            genes = self.extract_genes(content)

            if not genes:
                errors.append(f"no geneList found for test '{self.display_name}'")

            # Create filtered gene entries
            gene_entries = self.create_filtered_gene_entries(
                gene_symbols=genes,
                panel_names=["Comprehensive Kidney Disease Panel"]
            )

            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)

        except Exception as e:
            logger.error(f"Error scraping PreventionGenetics: {e}")
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
                'panel_name': 'Comprehensive Kidney Disease Panel',
                'scraper_version': '2.0.0'
            },
            errors=errors if errors else None
        )

        # Save output
        self.save_output(provider_data)

        logger.info(f"PreventionGenetics scraping complete: {len(gene_entries)} genes")
        return provider_data

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = PreventionGeneticsScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes")
