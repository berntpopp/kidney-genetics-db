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

import yaml

from schemas import GeneEntry, ProviderData
from utils import get_hgnc_normalizer, resolve_hgnc_symbol

class BaseDiagnosticScraper(ABC):
    """Abstract base class for all diagnostic panel scrapers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, provider_id: Optional[str] = None):
        """Initialize the scraper.

        Args:
            config: Configuration dictionary
            provider_id: Override provider ID (if not provided, auto-generated from class name)
        """
        # Load config from file if not provided
        if config is None:
            config_path = Path(__file__).parent / "config" / "config.yaml"
            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f)
            else:
                config = {}

        self.config = config

        # Use provided provider_id or auto-generate from class name
        if provider_id:
            self.provider_id = provider_id
        else:
            self.provider_id = self.__class__.__name__.lower().replace("scraper", "")

        self.logger = logging.getLogger(self.__class__.__name__)

        # Set up logging level from config
        log_level = self.config.get("logging", {}).get("level", "INFO")
        self.logger.setLevel(getattr(logging, log_level))

        self.output_dir = Path(self.config.get("output_dir", "output"))
        self.data_dir = Path(self.config.get("data_dir", "data"))
        self.use_browser = False  # Override in child classes if needed
        self.rate_limit = self.config.get("rate_limit", 2)  # seconds between requests

        # Get scraper-specific config including URL
        self.scraper_config = self.config.get("scrapers", {}).get(self.provider_id, {})
        self.url = self.scraper_config.get("url", "")  # URL from config

        # Create data directory for this provider
        self.provider_data_dir = self.data_dir / self.provider_id
        self.provider_data_dir.mkdir(parents=True, exist_ok=True)

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
        self.logger.debug(f"Fetching content from: {url}")

        if self.use_browser:
            content = self._fetch_with_browser(url)
        else:
            content = self._fetch_with_http(url)

        # Save raw content for debugging
        self._save_raw_data(content, url)

        return content

    def _save_raw_data(self, content: str, url: str, suffix: str = ""):
        """Save raw content to data directory for debugging.

        Args:
            content: Raw content to save
            url: Source URL (for filename)
            suffix: Optional suffix for filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create filename from URL or use suffix
        if suffix:
            filename = f"{timestamp}_{suffix}.html"
        else:
            # Extract meaningful part from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            name_part = path_parts[-1] if path_parts else "index"
            filename = f"{timestamp}_{name_part[:50]}.html"

        filepath = self.provider_data_dir / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.debug(f"Saved raw data to: {filepath}")
        except Exception as e:
            self.logger.warning(f"Failed to save raw data: {e}")

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
            self.logger.debug(f"HTTP request to: {url}")
            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=30) as response:
                self.logger.debug(f"Response status: {response.status}")
                self.logger.debug(f"Response headers: {dict(response.headers)}")

                content = response.read()

                # Handle gzip compression
                if response.headers.get('Content-Encoding') == 'gzip':
                    import gzip
                    content = gzip.decompress(content)
                    self.logger.debug("Decompressed gzip content")

                # Try to decode as UTF-8
                if isinstance(content, bytes):
                    content = content.decode("utf-8", errors="ignore")

                self.logger.debug(f"Fetched {len(content)} characters")
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

            self.logger.debug(f"Starting browser for: {url}")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Log console messages from the page
                page.on("console", lambda msg: self.logger.debug(f"Browser console: {msg.text}"))

                self.logger.debug(f"Navigating to: {url}")
                page.goto(url, wait_until="networkidle", timeout=60000)
                self.logger.debug("Page loaded successfully")

                # Wait for dynamic content to load
                try:
                    page.wait_for_selector("table", timeout=5000)
                    self.logger.debug("Table element found")
                except Exception:
                    self.logger.debug("No table element found (may not be needed)")

                # Additional wait for JavaScript rendering
                page.wait_for_timeout(3000)

                content = page.content()
                self.logger.debug(f"Browser fetched {len(content)} characters")

                browser.close()
                return content

        except ImportError as err:
            self.logger.error(f"Playwright not installed. Cannot fetch {url} with browser.")
            raise RuntimeError(
                "Playwright is required for browser-based scraping. "
                "Install with: pip install playwright && playwright install chromium"
            ) from err
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
        if not genes:
            return genes

        # Get normalizer and process in batch for efficiency
        normalizer = get_hgnc_normalizer()
        symbols = [gene.symbol for gene in genes]

        self.logger.info(f"Normalizing {len(symbols)} gene symbols via HGNC API")
        normalized_data = normalizer.normalize_batch(symbols)

        # Update gene entries with normalized data
        for gene in genes:
            # Store the original symbol as reported
            original_symbol = gene.symbol
            gene.reported_as = original_symbol

            # Get normalization result
            norm_result = normalized_data.get(original_symbol, {})

            if norm_result.get("found"):
                # Use HGNC-approved symbol
                approved = norm_result.get("approved_symbol")
                gene.symbol = approved
                gene.hgnc_id = norm_result.get("hgnc_id")
                
                # Set normalization status
                if approved == original_symbol:
                    gene.normalization_status = "unchanged"
                else:
                    gene.normalization_status = "normalized"
            else:
                # Keep original symbol if not found in HGNC
                gene.hgnc_id = None
                gene.normalization_status = "not_found"

        # Log statistics
        stats = normalizer.get_stats()
        self.logger.info(
            f"HGNC normalization complete - API calls: {stats['api_calls']}, "
            f"Cache hits: {stats['cache_hits']}, Cache misses: {stats['cache_misses']}"
        )

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
