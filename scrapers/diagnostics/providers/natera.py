"""Natera scraper - Renasight kidney gene panel."""

import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import GeneEntry, ProviderData
from utils import clean_gene_symbol

logger = logging.getLogger(__name__)


class NateraScraper(BaseDiagnosticScraper):
    """Scraper for Natera - Renasight panel."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize Natera scraper."""
        super().__init__(config)
        self.provider_id = "natera"
        self.provider_name = "Natera"
        self.provider_type = "single_panel"
        # URLs from config only - no hardcoding
        self.api_url = self.scraper_config.get("api_url", "")
        self.use_browser = False  # We'll use the API directly

    def fetch_all_genes_via_api(self) -> List[str]:
        """Fetch all genes from Natera API by iterating through pages."""
        genes = []
        page = 1
        max_pages = 45  # Safety limit - User confirmed 41 pages as of now

        self.logger.debug(f"Starting API fetch from: {self.api_url}")
        self.logger.debug(f"Using referer URL: {self.url}")

        # Headers for the API request
        headers = {
            "accept": "*/*",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": f"https://{urllib.parse.urlparse(self.api_url).netloc}" if self.api_url else "",
            "referer": self.url,
            "user-agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "x-requested-with": "XMLHttpRequest",
        }

        while page <= max_pages:
            # Prepare data for POST request
            data = {
                "action": "gene_screening_options",
                "panel": "",
                "page": str(page),
                "text": "",
                "letter": "",
                "nonce": "e362e71779",  # This might change, but we'll try with this
            }

            try:
                # Encode data for POST
                post_data = urllib.parse.urlencode(data).encode("utf-8")

                # Create request
                req = urllib.request.Request(self.api_url, data=post_data, headers=headers)

                # Make the API request
                with urllib.request.urlopen(req, timeout=30) as response:
                    content = response.read().decode("utf-8", errors="ignore")

                # Save raw API response for debugging
                self._save_raw_data(content, self.api_url, f"api_page_{page}")
                self.logger.debug(f"Saved API response for page {page}")

                # Check if we got any content
                if not content or "No results found" in content or "<tr" not in content:
                    self.logger.debug(f"No more content on page {page}, stopping")
                    # No more pages
                    break

                # Extract genes from the HTML response
                page_genes = self.extract_genes_from_api_response(content)
                self.logger.debug(f"Extracted {len(page_genes)} genes from page {page}")

                if not page_genes:
                    self.logger.debug(f"No genes found on page {page}, stopping")
                    # No genes found on this page, we're done
                    break

                genes.extend(page_genes)
                logger.info(f"Fetched page {page}: {len(page_genes)} genes")

                page += 1

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break

        # Remove duplicates
        unique_genes = list(set(genes))
        logger.info(f"Total unique genes fetched: {len(unique_genes)}")
        return unique_genes

    def extract_genes_from_api_response(self, html: str) -> List[str]:
        """Extract gene symbols from API HTML response."""
        soup = BeautifulSoup(html, "html.parser")
        genes = []

        # Find all rows with gene information
        # Genes are in the first <td> of each title-row
        title_rows = soup.find_all("tr", class_="title-row")

        for row in title_rows:
            cells = row.find_all("td")
            if cells:
                # First cell contains the gene symbol
                gene = cells[0].get_text().strip()
                if gene and 2 <= len(gene) <= 15:
                    cleaned = clean_gene_symbol(gene)
                    if cleaned:
                        genes.append(cleaned)

        return genes

    def extract_genes(self, content: str) -> List[str]:
        """Extract genes from Natera page."""
        soup = BeautifulSoup(content, "html.parser")
        genes = []

        # Natera typically has a well-structured gene list
        # Look for gene tables or lists
        selectors = [
            "table.table-responsive tbody tr",  # Main gene table
            "table.gene-table",
            "div.gene-list",
            "table tbody tr td:first-child",  # First column often has gene
            'div[class*="gene"]',
            "ul.genes li",
            "div.panel-content",
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements:
                    text = elem.get_text()
                    # Look for gene symbols
                    potential_genes = re.findall(r"\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b", text)
                    for gene in potential_genes:
                        if 2 <= len(gene) <= 15:
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)

        # Specifically look for table rows with gene information
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if cells:
                    # First cell often contains the gene symbol
                    first_cell = cells[0].get_text().strip()
                    cleaned = clean_gene_symbol(first_cell)
                    if cleaned and 2 <= len(cleaned) <= 15:
                        genes.append(cleaned)

        # Look for genes in definition lists or formatted sections
        for dl in soup.find_all("dl"):
            for dt in dl.find_all("dt"):
                text = dt.get_text().strip()
                cleaned = clean_gene_symbol(text)
                if cleaned and 2 <= len(cleaned) <= 15:
                    genes.append(cleaned)

        # Fallback: search for gene patterns
        if not genes:
            for element in soup.find_all(["p", "div", "span", "li"]):
                text = element.get_text()
                # Natera might list genes with associated disorders
                if any(keyword in text.lower() for keyword in ["gene", "includes", "tested"]):
                    potential_genes = re.findall(r"\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b", text)
                    for gene in potential_genes:
                        if 2 <= len(gene) <= 15 and not gene.startswith(
                            ("HTTP", "DNA", "RNA", "PDF")
                        ):
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)

        return list(set(genes))

    def run(self) -> ProviderData:
        """Run Natera scraper."""
        logger.info("Starting Natera scraper")

        errors = []
        gene_entries = []

        try:
            # Fetch all genes via API
            genes = self.fetch_all_genes_via_api()

            if not genes:
                logger.warning("No genes found for Natera Renasight panel")

            # Create gene entries
            gene_entries = [
                GeneEntry(
                    symbol=gene,
                    panels=["Renasight"],
                    occurrence_count=1,
                    confidence="high",
                )
                for gene in genes
            ]

            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)

        except Exception as e:
            logger.error(f"Error scraping Natera: {e}")
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
                "panel_name": "Renasight",
                "description": "Comprehensive kidney gene panel",
                "scraper_version": "1.0.0",
            },
            errors=errors if errors else None,
        )

        # Save output
        self.save_output(provider_data)

        logger.info(f"Natera scraping complete: {len(gene_entries)} genes")
        return provider_data


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = NateraScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes")
