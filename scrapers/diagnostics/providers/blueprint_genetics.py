"""
Blueprint Genetics scraper - handles all 24 kidney sub-panels.
"""

import logging
import os
import sys
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import GeneEntry, ProviderData, SubPanel
from utils import clean_gene_symbol

logger = logging.getLogger(__name__)

class BlueprintGeneticsScraper(BaseDiagnosticScraper):
    """Scraper for Blueprint Genetics - handles all 24 kidney sub-panels"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config, provider_id="blueprint_genetics")
        self.provider_name = "Blueprint Genetics"
        self.provider_type = "multi_panel"
        self.base_url = self.scraper_config.get("base_url", self.url)

    def get_sub_panels(self) -> List[Dict[str, str]]:
        """Return all Blueprint Genetics kidney sub-panel URLs from config"""
        panels_config = self.scraper_config.get("panels", [])
        if not panels_config:
            logger.warning("No panels configured for Blueprint Genetics")
            return []

        # Build full URLs from config
        panels = []
        base_url = self.scraper_config.get("base_url", self.base_url)
        for panel in panels_config:
            panels.append({
                "name": panel["name"],
                "url": f"{base_url}{panel['url_suffix']}"
            })

        return panels

    def extract_genes_from_panel(self, content: str) -> List[str]:
        """Extract gene symbols from a single Blueprint panel page"""
        self.logger.debug("Starting gene extraction from panel content")
        soup = BeautifulSoup(content, 'html.parser')
        genes = []

        # Try multiple selectors for Blueprint Genetics tables
        self.logger.debug("Trying to find gene table with selectors")
        selectors = [
            'table.table.mb-5',
            'table.table',
            'table[class*="table"]',
            'div.gene-list table',
            'div.panel-genes table'
        ]

        gene_table = None
        for selector in selectors:
            gene_table = soup.select_one(selector)
            if gene_table:
                self.logger.debug(f"Found gene table with selector: {selector}")
                break

        if gene_table:
            # Find all rows in the table
            rows = gene_table.find_all('tr')

            for row in rows[1:]:  # Skip header row
                # Try to find gene symbol in first column
                cols = row.find_all(['td', 'th'])
                if cols and len(cols) > 0:
                    gene_text = cols[0].get_text(strip=True)
                    gene_symbol = clean_gene_symbol(gene_text)
                    if gene_symbol:
                        genes.append(gene_symbol)
        else:
            # Fallback: look for gene symbols in various contexts
            # Try to find genes in lists or divs
            for element in soup.find_all(['div', 'span', 'p']):
                text = element.get_text()
                # Look for patterns like uppercase gene symbols
                import re
                potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                for gene in potential_genes:
                    if 2 <= len(gene) <= 15:  # Reasonable gene symbol length
                        genes.append(gene)

        return list(set(genes))  # Remove duplicates

    def run(self) -> ProviderData:
        """Scrape all Blueprint Genetics sub-panels"""
        logger.info("Starting Blueprint Genetics scraper for 24 sub-panels")
        logger.info(f"Base URL: {self.base_url}")

        sub_panels_data = []
        all_genes_dict = {}  # Track genes and which panels they appear in
        errors = []

        panels = self.get_sub_panels()
        logger.info(f"Total panels to scrape: {len(panels)}")

        for i, panel_info in enumerate(panels, 1):
            try:
                logger.info(f"[{i}/{len(panels)}] Scraping {panel_info['name']}...")
                logger.info(f"URL: {panel_info['url']}")

                # Fetch content
                logger.debug("About to fetch content...")
                content = self.fetch_content(panel_info['url'])
                logger.debug(f"Fetched {len(content)} characters")

                # Extract genes
                logger.debug("Extracting genes from content...")
                panel_genes = self.extract_genes_from_panel(content)
                logger.debug(f"Extraction complete, found {len(panel_genes)} genes")

                if not panel_genes:
                    logger.warning(f"No genes found for {panel_info['name']}")

                # Create sub-panel entry
                sub_panel = SubPanel(
                    name=panel_info['name'],
                    url=panel_info['url'],
                    gene_count=len(panel_genes)
                )
                sub_panels_data.append(sub_panel)

                # Track genes across panels
                for gene in panel_genes:
                    if gene not in all_genes_dict:
                        all_genes_dict[gene] = []
                    all_genes_dict[gene].append(panel_info['name'])

                logger.info(f"✓ Successfully scraped panel {i}/{len(panels)}: {panel_info['name']} - {len(panel_genes)} genes")

                # Rate limiting
                if i < len(panels):
                    logger.debug(f"Sleeping for {self.rate_limit} seconds...")
                    self.sleep()
                    logger.debug("Sleep complete")

            except Exception as e:
                logger.error(f"Error scraping {panel_info['name']}: {e}")
                errors.append(f"{panel_info['name']}: {str(e)}")

        # Create gene entries with panel information
        gene_entries = []
        for gene_symbol, panel_names in all_genes_dict.items():
            gene_entry = GeneEntry(
                symbol=gene_symbol,
                panels=panel_names,
                occurrence_count=len(panel_names),
            )
            gene_entries.append(gene_entry)

        # Normalize genes
        gene_entries = self.normalize_genes(gene_entries)

        # Sort genes by occurrence count
        gene_entries.sort(key=lambda x: x.occurrence_count, reverse=True)

        # Create provider data
        provider_data = ProviderData(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_type=self.provider_type,
            main_url=self.base_url,
            total_panels=len(sub_panels_data),
            sub_panels=sub_panels_data,
            total_unique_genes=len(gene_entries),
            genes=gene_entries,
            metadata={
                'scraper_version': '1.0.0',
                'panel_type': 'multi_panel',
                'total_panels': len(sub_panels_data)
            },
            errors=errors if errors else None
        )

        # Save output
        self.save_output(provider_data)

        logger.info(f"Blueprint Genetics scraping complete: {len(gene_entries)} unique genes from {len(sub_panels_data)} panels")

        return provider_data

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = BlueprintGeneticsScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes from {result.total_panels} panels")
