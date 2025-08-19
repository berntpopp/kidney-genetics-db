"""Base scraper class for all diagnostic panel scrapers."""

import json
import logging
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from schemas import GeneEntry, ProviderData
from utils import resolve_hgnc_symbol


class BaseDiagnosticScraper(ABC):
    """Abstract base class for all diagnostic panel scrapers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the scraper.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.provider_id = self.__class__.__name__.lower().replace("scraper", "")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_dir = Path(self.config.get("output_dir", "output"))
        self.use_browser = False  # Override in child classes if needed
        self.rate_limit = self.config.get("rate_limit", 2)  # seconds between requests

    @abstractmethod
    def run(self) -> ProviderData:
        """Main execution method - must be implemented by each scraper.

        Returns:
            ProviderData object with scraped results
        """
        pass

    def fetch_content(self, url: str) -> str:
        """Fetch content from URL using appropriate method.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string
        """
        if self.use_browser:
            return self._fetch_with_browser(url)
        return self._fetch_with_http(url)

    def _fetch_with_http(self, url: str) -> str:
        """Standard HTTP request.

        Args:
            url: URL to fetch

        Returns:
            HTML content
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                # Try to decode as UTF-8
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="ignore")
                return content
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            raise

    def _fetch_with_browser(self, url: str) -> str:
        """Browser automation for protected sites.

        Args:
            url: URL to fetch

        Returns:
            HTML content
        """
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=60000)

                # Wait for dynamic content to load
                try:
                    page.wait_for_selector("table", timeout=5000)
                except Exception:
                    pass  # Table might not exist

                # Additional wait for JavaScript rendering
                page.wait_for_timeout(3000)

                content = page.content()
                browser.close()
                return content
        except ImportError:
            self.logger.error(f"Playwright not installed. Cannot fetch {url} with browser.")
            raise RuntimeError(
                "Playwright is required for browser-based scraping. "
                "Install with: pip install playwright && playwright install chromium"
            )
        except Exception as e:
            self.logger.error(f"Error fetching {url} with browser: {e}")
            raise

    def normalize_genes(self, genes: List[GeneEntry]) -> List[GeneEntry]:
        """Normalize gene symbols to HGNC approved symbols.

        Args:
            genes: List of GeneEntry objects

        Returns:
            List of normalized GeneEntry objects
        """
        for gene in genes:
            hgnc_data = resolve_hgnc_symbol(gene.symbol)
            if hgnc_data:
                gene.hgnc_id = hgnc_data.get("hgnc_id")
                gene.approved_symbol = hgnc_data.get("approved_symbol")

        return genes

    def save_output(self, data: ProviderData):
        """Save scraped data to JSON file.

        Args:
            data: ProviderData object to save
        """
        date_dir = self.output_dir / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        output_file = date_dir / f"{self.provider_id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data.model_dump(), f, indent=2, default=str)

        self.logger.info(f"Saved output to {output_file}")

    def sleep(self):
        """Apply rate limiting between requests."""
        if self.rate_limit > 0:
            time.sleep(self.rate_limit)