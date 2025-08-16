"""
HGNC (HUGO Gene Nomenclature Committee) client for gene symbol standardization.

This module provides a client for interacting with the HGNC REST API to
standardize gene symbols and retrieve gene information.

Based on proven patterns from custom-panel and kidney-genetics-v1 implementations.
"""

import functools
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)


class HGNCClient:
    """Client for interacting with the HGNC REST API with batch processing and fallback strategies."""

    BASE_URL = "https://rest.genenames.org"

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        batch_size: int = 100,
        max_workers: int = 4,
    ):
        """
        Initialize the HGNC client.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds  
            batch_size: Maximum symbols per batch request
            max_workers: Maximum threads for parallel processing
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.batch_size = batch_size
        self.max_workers = max_workers
        
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "kidney-genetics-db/1.0.0"
        })

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
    ) -> Dict[str, Any]:
        """
        Make a request to the HGNC API with retry logic and exponential backoff.

        Args:
            endpoint: API endpoint
            params: Query parameters
            method: HTTP method

        Returns:
            JSON response as dictionary

        Raises:
            requests.RequestException: If request fails after retries
        """
        url = f"{self.BASE_URL}/{endpoint}"

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method, url, params=params, timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
                
            except (requests.RequestException, ValueError) as e:
                if attempt == self.max_retries:
                    logger.error(
                        f"Failed to fetch {url} after {self.max_retries} retries: {e}"
                    )
                    raise
                    
                # Exponential backoff
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)

        raise requests.RequestException("Unexpected error in request loop")

    @functools.lru_cache(maxsize=10000)
    def symbol_to_hgnc_id(self, symbol: str) -> Optional[str]:
        """
        Convert a gene symbol to HGNC ID.

        Args:
            symbol: Gene symbol

        Returns:
            HGNC ID (e.g., "HGNC:5") or None if not found
        """
        try:
            response = self._make_request("search/symbol", {"symbol": symbol})
            docs = response.get("response", {}).get("docs", [])
            if docs:
                return docs[0].get("hgnc_id")
        except (requests.RequestException, ValueError):
            pass
        return None

    @functools.lru_cache(maxsize=10000)
    def get_gene_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive gene information for a symbol.

        Args:
            symbol: Gene symbol

        Returns:
            Dictionary with gene information or None if not found
        """
        try:
            response = self._make_request("search/symbol", {"symbol": symbol})
            docs = response.get("response", {}).get("docs", [])
            if docs:
                return docs[0]
        except (requests.RequestException, ValueError):
            pass
        return None

    @functools.lru_cache(maxsize=1000)
    def standardize_symbol(self, symbol: str) -> str:
        """
        Standardize a gene symbol to the approved HGNC symbol.

        This method tries multiple approaches:
        1. Direct symbol lookup
        2. Previous symbol lookup
        3. Alias symbol lookup

        Args:
            symbol: Input gene symbol

        Returns:
            Standardized HGNC symbol or original symbol if not found
        """
        symbol = symbol.strip().upper()

        # Try direct symbol lookup
        try:
            response = self._make_request(f"search/symbol/{symbol}")
            docs = response.get("response", {}).get("docs", [])
            if docs:
                return docs[0].get("symbol", symbol)
        except (requests.RequestException, ValueError):
            pass

        # Try previous symbol lookup
        try:
            response = self._make_request(f"search/prev_symbol/{symbol}")
            docs = response.get("response", {}).get("docs", [])
            if docs:
                return docs[0].get("symbol", symbol)
        except (requests.RequestException, ValueError):
            pass

        # Try alias symbol lookup
        try:
            response = self._make_request(f"search/alias_symbol/{symbol}")
            docs = response.get("response", {}).get("docs", [])
            if docs:
                return docs[0].get("symbol", symbol)
        except (requests.RequestException, ValueError):
            pass

        logger.warning(f"Could not standardize gene symbol: {symbol}")
        return symbol

    @functools.lru_cache(maxsize=1000)
    def standardize_symbols_batch(
        self, symbols: Tuple[str, ...]
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Standardize multiple gene symbols using HGNC batch API.

        Uses the +OR+ syntax for efficient batch queries, following the exact
        pattern from custom-panel and kidney-genetics-v1 implementations.

        Args:
            symbols: Tuple of gene symbols (tuple for caching compatibility)

        Returns:
            Dictionary mapping original symbols to dict containing approved_symbol and hgnc_id
        """
        if not symbols:
            return {}

        original_symbols = list(symbols)
        result = {
            symbol: {"approved_symbol": symbol, "hgnc_id": None}
            for symbol in original_symbols
        }

        try:
            # Construct query using +OR+ syntax: "GENE1+OR+GENE2+OR+..."
            query_str = "+OR+".join([s.upper() for s in original_symbols])
            endpoint = f"search/symbol/{query_str}"
            
            params = {"fields": "symbol,hgnc_id"}
            response = self._make_request(endpoint, params=params)
            
            docs = response.get("response", {}).get("docs", [])
            
            # Match by symbol name directly
            found_symbols = set()
            for doc in docs:
                approved_symbol = doc.get("symbol")
                hgnc_id = doc.get("hgnc_id")
                if not approved_symbol:
                    continue

                # Check if this approved symbol matches any input symbol (case-insensitive)
                for original_symbol in original_symbols:
                    if original_symbol.upper() == approved_symbol.upper():
                        result[original_symbol] = {
                            "approved_symbol": approved_symbol,
                            "hgnc_id": hgnc_id,
                        }
                        found_symbols.add(original_symbol)
                        break

            # Log batch results
            exact_matches = len(found_symbols)
            need_postprocess = len(original_symbols) - exact_matches
            logger.debug(
                f"HGNC batch API results: {len(original_symbols)} symbols submitted, "
                f"{exact_matches} exact matches found, {need_postprocess} need further processing"
            )

            # For symbols not found in batch, try individual lookups with aliases/prev symbols
            postprocess_fixed = 0
            for original_symbol in original_symbols:
                if original_symbol not in found_symbols:
                    # Try individual standardization (includes alias and prev symbol lookups)
                    standardized = self.standardize_symbol(original_symbol)
                    if standardized.upper() != original_symbol.upper():
                        # Symbol was standardized, try to get its HGNC ID
                        gene_info = self.get_gene_info(standardized)
                        hgnc_id = gene_info.get("hgnc_id") if gene_info else None
                        result[original_symbol] = {
                            "approved_symbol": standardized,
                            "hgnc_id": hgnc_id,
                        }
                        postprocess_fixed += 1

            if need_postprocess > 0:
                logger.debug(
                    f"Alternative symbol search results: {postprocess_fixed} out of "
                    f"{need_postprocess} symbols were successfully resolved"
                )

        except requests.RequestException as e:
            logger.warning(
                f"Batch symbol standardization failed: {e}. Falling back to individual lookups."
            )
            # Fallback to individual lookups
            for original_symbol in original_symbols:
                standardized = self.standardize_symbol(original_symbol)
                gene_info = self.get_gene_info(standardized)
                hgnc_id = gene_info.get("hgnc_id") if gene_info else None
                result[original_symbol] = {
                    "approved_symbol": standardized,
                    "hgnc_id": hgnc_id,
                }

        # Log summary
        changed_count = sum(
            1 for k, v in result.items()
            if v["approved_symbol"] and k.upper() != v["approved_symbol"].upper()
        )
        logger.debug(
            f"HGNC batch complete: {len(symbols)} symbols processed, {changed_count} standardized"
        )

        return result

    def standardize_symbols(
        self, symbols: List[str]
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Standardize multiple gene symbols with automatic batching.

        Args:
            symbols: List of gene symbols

        Returns:
            Dictionary mapping original symbols to dict containing approved_symbol and hgnc_id
        """
        if not symbols:
            return {}

        # Split into batches to avoid URL length limits
        result = {}
        
        for i in range(0, len(symbols), self.batch_size):
            batch = symbols[i : i + self.batch_size]
            batch_result = self.standardize_symbols_batch(tuple(batch))
            result.update(batch_result)

        return result

    def standardize_symbols_parallel(
        self, symbols: List[str]
    ) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Standardize multiple gene symbols using parallel batch processing.
        
        Follows the exact pattern from custom-panel for maximum performance.

        Args:
            symbols: List of gene symbols

        Returns:
            Dictionary mapping original symbols to dict containing approved_symbol and hgnc_id
        """
        if not symbols:
            return {}

        logger.info(f"Standardizing {len(symbols)} gene symbols with parallel HGNC batch API")

        # Split genes into batches
        batches = [
            symbols[i : i + self.batch_size]
            for i in range(0, len(symbols), self.batch_size)
        ]

        if len(batches) == 1:
            # Single batch - process directly
            return self.standardize_symbols_batch(tuple(batches[0]))

        # Multiple batches - use parallel processing
        logger.info(
            f"Processing {len(batches)} HGNC batches in parallel (max_workers={self.max_workers})"
        )

        standardized = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batch jobs
            future_to_batch = {
                executor.submit(self.standardize_symbols_batch, tuple(batch)): batch
                for batch in batches
            }

            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    batch_result = future.result()
                    standardized.update(batch_result)
                    logger.info(f"✓ Completed HGNC batch of {len(batch)} symbols")
                except Exception as e:
                    logger.error(
                        f"✗ HGNC batch processing failed for {len(batch)} symbols: {e}"
                    )
                    # Fallback to individual processing
                    for symbol in batch:
                        try:
                            gene_info = self.get_gene_info(symbol)
                            standardized[symbol] = {
                                "approved_symbol": symbol,
                                "hgnc_id": gene_info.get("hgnc_id") if gene_info else None,
                            }
                        except Exception:
                            standardized[symbol] = {
                                "approved_symbol": symbol,
                                "hgnc_id": None,
                            }

        # Log standardization results
        changed_symbols = {
            k: v for k, v in standardized.items()
            if v["approved_symbol"] and k != v["approved_symbol"]
        }
        if changed_symbols:
            logger.info(f"✨ Standardized {len(changed_symbols)} gene symbols")

        return standardized

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring performance.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "symbol_to_hgnc_id": self.symbol_to_hgnc_id.cache_info()._asdict(),
            "get_gene_info": self.get_gene_info.cache_info()._asdict(),
            "standardize_symbol": self.standardize_symbol.cache_info()._asdict(),
            "standardize_symbols_batch": self.standardize_symbols_batch.cache_info()._asdict(),
        }

    def clear_cache(self) -> None:
        """Clear all cached results."""
        self.symbol_to_hgnc_id.cache_clear()
        self.get_gene_info.cache_clear()
        self.standardize_symbol.cache_clear()
        self.standardize_symbols_batch.cache_clear()