"""
University of Chicago Genetic Services scraper - panels in the public Nephrology category.
"""

import logging
import os
import sys
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import GeneEntry, ProviderData, SubPanel

logger = logging.getLogger(__name__)


class UChicagoGeneticsScraper(BaseDiagnosticScraper):
    """Scraper for UChicago Genetic Services - every panel listed under Nephrology."""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config, provider_id="uchicago_genetics")
        self.provider_name = "University of Chicago Genetic Services"
        self.provider_type = "multi_panel"
        # robots.txt asks for Crawl-delay: 10
        self.rate_limit = self.scraper_config.get("rate_limit", self.rate_limit)

    def extract_panel_links(self, content: str) -> List[Dict[str, str]]:
        """Return {name, url} for each /tests/ link on the Nephrology category page."""
        soup = BeautifulSoup(content, "html.parser")
        panels = {}
        for link in soup.select('a[href^="/tests/"]'):
            panels.setdefault(urljoin(self.url, link["href"]), " ".join(link.get_text().split()))
        return [{"name": name, "url": url} for url, name in panels.items()]

    def extract_genes_from_panel(self, content: str) -> List[str]:
        """Return gene symbols from the linked /gene/ entries of a panel page."""
        soup = BeautifulSoup(content, "html.parser")
        genes = [a.get_text(strip=True) for a in soup.select('a[href^="/gene/"]')]
        return self.filter_genes(list(dict.fromkeys(g for g in genes if g)))

    def run(self) -> ProviderData:
        """Scrape the category page, then each listed panel."""
        logger.info(f"Starting UChicago Genetic Services scraper: {self.url}")
        sub_panels: List[SubPanel] = []
        all_genes: Dict[str, List[str]] = {}
        errors: List[str] = []

        try:
            panels = self.extract_panel_links(self.fetch_content(self.url))
        except Exception as e:
            logger.error(f"Error fetching category page: {e}")
            panels, errors = [], [f"category page: {e}"]
        if not panels and not errors:
            errors.append("category page: no panel links found")

        for panel in panels:
            self.sleep()
            try:
                genes = self.extract_genes_from_panel(self.fetch_content(panel["url"]))
            except Exception as e:
                logger.error(f"Error scraping {panel['name']}: {e}")
                errors.append(f"{panel['name']}: {e}")
                continue
            if not genes:
                errors.append(f"{panel['name']}: no genes found")
                continue
            sub_panels.append(SubPanel(name=panel["name"], url=panel["url"], gene_count=len(genes)))
            for gene in genes:
                all_genes.setdefault(gene, []).append(panel["name"])
            logger.info(f"{panel['name']}: {len(genes)} genes")

        gene_entries = self.normalize_genes(
            [
                GeneEntry(symbol=symbol, panels=names, occurrence_count=len(names))
                for symbol, names in all_genes.items()
            ]
        )

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
                "scraper_version": "1.0.0",
                "panel_type": "multi_panel",
                "scope": "Nephrology test category",
            },
            errors=errors or None,
        )
        self.save_output(provider_data)
        logger.info(
            f"UChicago Genetic Services complete: {len(gene_entries)} genes "
            f"from {len(sub_panels)} panels"
        )
        return provider_data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = UChicagoGeneticsScraper().run()
    print(f"Scraped {result.total_unique_genes} genes from {result.total_panels} panels")
