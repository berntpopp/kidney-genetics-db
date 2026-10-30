"""
MGZ München scraper - every test in the Nephrologie specialty area.
"""

import json
import logging
import os
import re
import sys
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import GeneEntry, ProviderData, SubPanel

logger = logging.getLogger(__name__)

class MGZMuenchenScraper(BaseDiagnosticScraper):
    """Scraper for MGZ München - Nephrologie und Elektrolytstörungen area"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config, provider_id="mgz_muenchen")
        self.provider_name = "MGZ München"
        self.provider_type = "multi_panel"

    def extract_panels(self, content: str) -> List[Dict[str, str]]:
        """Return {name, url, endpoint} for each test in the configured specialty area."""
        soup = BeautifulSoup(content, 'html.parser')
        area = soup.select_one(f'[data-area-panel="{self.scraper_config.get("area", "")}"]')
        panels = []
        for link in area.select('a.mgz-service-spectrum__details') if area else []:
            actions = link.find_parent(class_='mgz-service-spectrum__actions')
            toggle = actions.select_one('[data-endpoint]') if actions else None
            if toggle:
                name = re.sub(r'^Details zu ', '', link.get('aria-label', ''))
                panels.append(
                    {'name': name, 'url': link['href'], 'endpoint': toggle['data-endpoint']}
                )
        return panels

    def run(self) -> ProviderData:
        """Run MGZ München scraper: the area listing, then each test's gene endpoint."""
        logger.info("Starting MGZ München scraper")

        errors = []
        sub_panels: List[SubPanel] = []
        all_genes: Dict[str, List[str]] = {}

        try:
            panels = self.extract_panels(self.fetch_content(self.url))
        except Exception as e:
            logger.error(f"Error scraping MGZ München: {e}")
            panels, errors = [], [str(e)]
        if not panels and not errors:
            errors.append("no panels found in the configured area")

        for panel in panels:
            self.sleep()
            try:
                genes = self.filter_genes(
                    json.loads(self.fetch_content(panel['endpoint'])).get('genes', [])
                )
            except Exception as e:
                logger.error(f"Error scraping {panel['name']}: {e}")
                errors.append(f"{panel['name']}: {e}")
                continue
            if not genes:
                errors.append(f"{panel['name']}: no genes found")
                continue
            genes = list(dict.fromkeys(genes))
            sub_panels.append(SubPanel(name=panel['name'], url=panel['url'], gene_count=len(genes)))
            for gene in genes:
                all_genes.setdefault(gene, []).append(panel['name'])

        gene_entries = self.normalize_genes(
            [
                GeneEntry(symbol=symbol, panels=names, occurrence_count=len(names))
                for symbol, names in all_genes.items()
            ]
        )

        # Create provider data
        provider_data = ProviderData(
            id=self.provider_id,
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_type=self.provider_type,
            main_url=self.url,
            total_panels=len(sub_panels),
            sub_panels=sub_panels,
            total_unique_genes=len(gene_entries),
            genes=gene_entries,
            metadata={
                'panel_name': 'Nephrologie und Elektrolytstörungen',
                'language': 'de',
                'scraper_version': '2.0.0'
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
