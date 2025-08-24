"""
Mayo Clinic Labs scraper - uses Botright to bypass Akamai protection.
"""

import asyncio
import logging
import os
import re
import sys
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import GeneEntry, ProviderData
from utils import clean_gene_symbol

logger = logging.getLogger(__name__)

class MayoClinicScraper(BaseDiagnosticScraper):
    """Scraper for Mayo Clinic Labs - single comprehensive panel"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config, provider_id="mayo_clinic")
        self.provider_name = "Mayo Clinic Labs"
        self.provider_type = "single_panel"
        self.use_browser = True  # Use Playwright Stealth for Akamai bypass
        self.logger.debug(f"Initialized Mayo Clinic scraper with URL: {self.url}")

    async def _fetch_with_stealth(self, url: str) -> str:
        """Fetch content using Playwright Stealth to bypass Akamai protection.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string

        Raises:
            RuntimeError: If Playwright Stealth is not installed or fails
        """
        try:
            from playwright.async_api import async_playwright
            from playwright_stealth import Stealth

            self.logger.info("Using Playwright Stealth to bypass Akamai protection")

            # Use stealth configuration with custom languages
            stealth = Stealth(
                navigator_languages_override=("en-US", "en"),
                init_scripts_only=True
            )

            async with stealth.use_async(async_playwright()) as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor"
                    ]
                )

                try:
                    # Create browser context with realistic settings
                    context = await browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        ),
                        viewport={"width": 1920, "height": 1080},
                        extra_http_headers={
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                            "Accept-Language": "en-US,en;q=0.5",
                            "Accept-Encoding": "gzip, deflate, br",
                            "DNT": "1",
                            "Connection": "keep-alive",
                            "Upgrade-Insecure-Requests": "1"
                        }
                    )

                    page = await context.new_page()

                    self.logger.debug(f"Playwright Stealth navigating to: {url}")

                    # Navigate to the page with realistic timing
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                    self.logger.debug("Page loaded successfully with Playwright Stealth")

                    # Wait for dynamic content with realistic timing
                    await page.wait_for_timeout(3000)

                    # Try to wait for specific elements that might indicate content is loaded
                    try:
                        await page.wait_for_selector("body", timeout=10000)
                    except Exception:
                        self.logger.debug("Body selector not found, continuing...")

                    # Get page content
                    content = await page.content()
                    self.logger.debug(f"Playwright Stealth fetched {len(content)} characters")

                    return content

                finally:
                    await browser.close()

        except ImportError as err:
            self.logger.error("Playwright Stealth not installed. Install with: pip install playwright-stealth")
            raise RuntimeError(
                "Playwright Stealth is required to bypass Mayo Clinic's Akamai protection. "
                "Install with: pip install playwright-stealth && playwright install chromium"
            ) from err
        except Exception as e:
            self.logger.error(f"Error fetching {url} with Playwright Stealth: {e}")
            raise

    def fetch_content(self, url: str) -> str:
        """Override fetch_content to use Playwright Stealth for Mayo Clinic.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string
        """
        self.logger.debug(f"Fetching content from: {url}")

        # Use Playwright Stealth for Mayo Clinic to bypass Akamai
        try:
            # Run the async Playwright Stealth method
            content = asyncio.run(self._fetch_with_stealth(url))

            # Save raw content for debugging
            self._save_raw_data(content, url)

            return content

        except Exception as e:
            self.logger.error(f"Failed to fetch content with Playwright Stealth: {e}")
            # Fall back to regular browser method
            self.logger.info("Falling back to regular Playwright...")
            return super().fetch_content(url)

    def extract_genes(self, content: str) -> List[str]:
        """Extract genes from Mayo Clinic page content"""
        from bs4 import BeautifulSoup

        genes = []
        self.logger.debug("Starting gene extraction from Mayo Clinic content")

        # Save raw HTML for debugging
        self._save_raw_data(content, self.url, "mayo_clinic_page")
        self.logger.debug(f"Saved raw HTML, {len(content)} characters")

        soup = BeautifulSoup(content, 'html.parser')

        # Try multiple approaches to find genes

        # Approach 1: Look for emphasized elements (em or i tags)
        gene_elements = soup.find_all(['em', 'i'])
        for elem in gene_elements:
            text = elem.get_text()
            # Parse gene symbols from emphasized text
            if ',' in text or re.search(r'[A-Z]{2,}[0-9]*', text):
                # This might be a gene list
                potential_genes = re.split(r'[,\s]+', text)
                for gene in potential_genes:
                    cleaned = clean_gene_symbol(gene)
                    if cleaned and 2 <= len(cleaned) <= 15:
                        genes.append(cleaned)
                        self.logger.debug(f"Found gene in em/i tag: {cleaned}")

        # Approach 2: Look for the paragraph containing the gene list
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text()
            if '302 genes' in text or 'hereditary kidney disease' in text:
                self.logger.debug("Found paragraph with gene count reference")
                # This paragraph likely contains the gene list
                # Get all text content
                full_text = text

                # Look for patterns after "disease:" or in emphasized text
                # Mayo typically lists genes separated by commas
                if ':' in full_text:
                    # Get everything after the colon
                    parts = full_text.split(':', 1)
                    if len(parts) > 1:
                        gene_section = parts[1]
                        # Extract gene symbols
                        gene_pattern = r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b'
                        potential_genes = re.findall(gene_pattern, gene_section)
                        for gene in potential_genes:
                            cleaned = clean_gene_symbol(gene)
                            if cleaned and 2 <= len(cleaned) <= 15:
                                genes.append(cleaned)
                                self.logger.debug(f"Found gene after colon: {cleaned}")

        # Approach 3: Look specifically in div elements that might contain gene lists
        if not genes:
            self.logger.info("Looking for genes in div elements")
            divs = soup.find_all('div')
            for div in divs:
                text = div.get_text()
                # Check if this div contains multiple gene-like strings
                gene_pattern = r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b'
                potential_genes = re.findall(gene_pattern, text)

                # If we find many potential genes in one div, it's likely the gene list
                if len(potential_genes) > 50:
                    self.logger.debug(f"Found div with {len(potential_genes)} potential genes")
                    for gene in potential_genes:
                        if 2 <= len(gene) <= 15 and not gene.startswith(('HTTP', 'MAYO', 'TEST', 'PDF')):
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)
                    if genes:
                        break  # Found the gene list

        # Approach 4: Check table cells
        if not genes:
            self.logger.info("Looking for genes in table cells")
            cells = soup.find_all('td')
            for cell in cells:
                text = cell.get_text().strip()
                # Check if this looks like a gene symbol
                if re.match(r'^[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*$', text):
                    cleaned = clean_gene_symbol(text)
                    if cleaned and 2 <= len(cleaned) <= 15:
                        genes.append(cleaned)
                        self.logger.debug(f"Found gene in td: {cleaned}")

        # Remove duplicates and return
        unique_genes = list(set(genes))
        self.logger.info(f"Extracted {len(unique_genes)} unique genes from Mayo Clinic")
        return unique_genes

    def run(self) -> ProviderData:
        """Run Mayo Clinic scraper"""
        logger.info("Starting Mayo Clinic scraper")

        errors = []
        gene_entries = []

        try:
            # Fetch content using browser (due to Akamai protection)
            content = self.fetch_content(self.url)

            # Extract genes
            genes = self.extract_genes(content)

            # Create filtered gene entries
            gene_entries = self.create_filtered_gene_entries(
                gene_symbols=genes,
                panel_names=["Comprehensive Nephrology Gene Panel (NEPHP)"]
            )

            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)

        except Exception as e:
            logger.error(f"Error scraping Mayo Clinic: {e}")
            errors.append(str(e))

        # Create provider data
        provider_data = ProviderData(
            id=self.provider_id,
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_type=self.provider_type,
            main_url=self.url,
            total_panels=1,
            sub_panels=None,  # Single panel, no sub-panels
            total_unique_genes=len(gene_entries),
            genes=gene_entries,
            metadata={
                'panel_name': 'Comprehensive Nephrology Gene Panel (NEPHP)',
                'test_id': '618086',
                'scraper_version': '2.0.0',
                'akamai_bypass': 'playwright-stealth',
                'stealth_features': ['navigator_webdriver_hidden', 'custom_languages', 'realistic_headers']
            },
            errors=errors if errors else None
        )

        # Save output
        self.save_output(provider_data)

        logger.info(f"Mayo Clinic scraping complete: {len(gene_entries)} genes")
        return provider_data

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = MayoClinicScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes")
