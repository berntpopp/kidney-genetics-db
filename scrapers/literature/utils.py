"""Shared utilities for diagnostic panel scrapers."""

import json
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HGNCNormalizer:
    """Minimal HGNC normalization service with file-based caching."""

    BASE_URL = "https://rest.genenames.org"
    CACHE_DIR = Path("data/hgnc_cache")
    CACHE_TTL = 30 * 24 * 3600  # 30 days in seconds

    def __init__(self):
        """Initialize the HGNC normalizer."""
        self.cache_dir = self.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session_cache = {}  # In-memory cache for current session
        self.stats = {"api_calls": 0, "cache_hits": 0, "cache_misses": 0}

    def _get_cache_path(self, symbol: str) -> Path:
        """Get cache file path for a symbol."""
        clean_symbol = re.sub(r"[^A-Z0-9]", "_", symbol.upper())
        return self.cache_dir / f"{clean_symbol}.json"

    def _load_from_cache(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Load symbol data from cache if valid."""
        cache_path = self._get_cache_path(symbol)

        if cache_path.exists():
            try:
                with open(cache_path, "r") as f:
                    cached = json.load(f)

                # Check if cache is still valid
                cached_time = datetime.fromisoformat(cached["cached_at"])
                if datetime.now() - cached_time < timedelta(seconds=self.CACHE_TTL):
                    self.stats["cache_hits"] += 1
                    return cached["data"]
            except Exception as e:
                logger.debug(f"Cache read error for {symbol}: {e}")

        self.stats["cache_misses"] += 1
        return None

    def _save_to_cache(self, symbol: str, data: Dict[str, Any]):
        """Save symbol data to cache."""
        cache_path = self._get_cache_path(symbol)

        try:
            cache_data = {
                "symbol": symbol,
                "data": data,
                "cached_at": datetime.now().isoformat(),
            }
            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.debug(f"Cache write error for {symbol}: {e}")

    def _make_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make a request to HGNC API."""
        url = f"{self.BASE_URL}/{endpoint}"

        headers = {
            "Accept": "application/json",
            "User-Agent": "kidney-genetics-db/1.0",
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                self.stats["api_calls"] += 1
                data = json.loads(response.read().decode("utf-8"))
                return data
        except Exception as e:
            logger.debug(f"HGNC API error for {url}: {e}")
            return None

    def normalize_symbol(self, symbol: str) -> Dict[str, Any]:
        """Normalize a single gene symbol.

        Args:
            symbol: Gene symbol to normalize

        Returns:
            Dict with hgnc_id, approved_symbol, and found status
        """
        if not symbol:
            return {"hgnc_id": None, "approved_symbol": symbol, "found": False}

        normalized = symbol.strip().upper()

        # Check session cache first
        if normalized in self.session_cache:
            return self.session_cache[normalized]

        # Check file cache
        cached = self._load_from_cache(normalized)
        if cached:
            self.session_cache[normalized] = cached
            return cached

        # Try API lookup - current symbol
        response = self._make_request(f"search/symbol/{urllib.parse.quote(normalized)}")
        if response and response.get("response", {}).get("docs"):
            doc = response["response"]["docs"][0]
            result = {
                "hgnc_id": doc.get("hgnc_id"),
                "approved_symbol": doc.get("symbol", symbol),
                "found": True,
            }
            self._save_to_cache(normalized, result)
            self.session_cache[normalized] = result
            return result

        # Try previous symbol
        response = self._make_request(f"search/prev_symbol/{urllib.parse.quote(normalized)}")
        if response and response.get("response", {}).get("docs"):
            doc = response["response"]["docs"][0]
            result = {
                "hgnc_id": doc.get("hgnc_id"),
                "approved_symbol": doc.get("symbol", symbol),
                "found": True,
                "was_previous": True,
            }
            self._save_to_cache(normalized, result)
            self.session_cache[normalized] = result
            return result

        # Try alias symbol
        response = self._make_request(f"search/alias_symbol/{urllib.parse.quote(normalized)}")
        if response and response.get("response", {}).get("docs"):
            doc = response["response"]["docs"][0]
            result = {
                "hgnc_id": doc.get("hgnc_id"),
                "approved_symbol": doc.get("symbol", symbol),
                "found": True,
                "was_alias": True,
            }
            self._save_to_cache(normalized, result)
            self.session_cache[normalized] = result
            return result

        # Not found - cache negative result
        result = {"hgnc_id": None, "approved_symbol": symbol, "found": False}
        self._save_to_cache(normalized, result)
        self.session_cache[normalized] = result
        return result

    def normalize_batch(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Normalize a batch of gene symbols.

        Args:
            symbols: List of gene symbols

        Returns:
            Dict mapping original symbols to normalization results
        """
        results = {}

        for symbol in symbols:
            if symbol:
                results[symbol] = self.normalize_symbol(symbol)
            else:
                results[symbol] = {
                    "hgnc_id": None,
                    "approved_symbol": symbol,
                    "found": False,
                }

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get normalization statistics."""
        return self.stats.copy()


# Global normalizer instance
_normalizer = None


def get_hgnc_normalizer() -> HGNCNormalizer:
    """Get or create the global HGNC normalizer instance."""
    global _normalizer
    if _normalizer is None:
        _normalizer = HGNCNormalizer()
    return _normalizer


@lru_cache(maxsize=10000)
def resolve_hgnc_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Resolve a gene symbol to HGNC data.

    This is a compatibility wrapper for the new HGNC normalizer.

    Args:
        symbol: Gene symbol to resolve

    Returns:
        Dict with hgnc_id and approved_symbol, or None if not found
    """
    try:
        normalizer = get_hgnc_normalizer()
        result = normalizer.normalize_symbol(symbol)

        if result.get("found"):
            return {
                "hgnc_id": result.get("hgnc_id"),
                "approved_symbol": result.get("approved_symbol"),
            }
        # Return original symbol if not found in HGNC
        return {"hgnc_id": None, "approved_symbol": symbol.upper()}
    except Exception as e:
        logger.error(f"Error resolving HGNC symbol {symbol}: {e}")
        return None


def clean_gene_symbol(symbol: str) -> str:
    """Clean a gene symbol by removing special characters and annotations.

    Args:
        symbol: Raw gene symbol from source

    Returns:
        Cleaned gene symbol
    """
    # Remove common annotations
    symbol = re.sub(r"\[.*?\]", "", symbol)  # Remove bracketed content
    symbol = re.sub(r"\(.*?\)", "", symbol)  # Remove parenthetical content
    symbol = symbol.replace("*", "").replace("#", "").replace(".", "")
    symbol = symbol.strip()

    # Remove common suffixes/prefixes
    if symbol.endswith("-AS1"):
        symbol = symbol[:-4]

    # Validate basic gene symbol format
    # Allow letters (any case), numbers, and hyphens (for MT genes)
    # Must start with a letter
    if not re.match(r"^[A-Za-z][A-Za-z0-9\-]*$", symbol):
        return ""

    return symbol


def calculate_confidence(gene_count: int, source_type: str) -> str:
    """Calculate confidence score for gene data.

    Args:
        gene_count: Number of genes found
        source_type: Type of source (e.g., 'commercial', 'academic')

    Returns:
        Confidence level: 'high', 'medium', or 'low'
    """
    if gene_count > 100 and source_type in ["commercial", "academic"]:
        return "high"
    if gene_count > 50:
        return "medium"
    return "low"


def normalize_panel_name(name: str) -> str:
    """Normalize panel name for consistency.

    Args:
        name: Raw panel name

    Returns:
        Normalized panel name
    """
    # Remove extra whitespace
    name = " ".join(name.split())

    # Standardize common terms
    replacements = {
        "NGS": "Next Generation Sequencing",
        "WES": "Whole Exome Sequencing",
        "WGS": "Whole Genome Sequencing",
        "&": "and",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    return name.strip()


def validate_gene_list(genes: list) -> tuple[list, list]:
    """Validate a list of gene symbols.

    Args:
        genes: List of gene symbols to validate

    Returns:
        Tuple of (valid_genes, invalid_genes)
    """
    valid_genes = []
    invalid_genes = []

    for gene in genes:
        if gene and 2 <= len(gene) <= 15:
            if re.match(r"^[A-Z][A-Z0-9]{1,}[A-Z0-9]*$", gene):
                valid_genes.append(gene)
            else:
                invalid_genes.append(gene)
        else:
            invalid_genes.append(gene)

    return valid_genes, invalid_genes
