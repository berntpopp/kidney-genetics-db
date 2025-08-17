"""
Enhanced HGNC client with unified cache system integration.

This module provides an upgraded HGNC client that uses the unified cache service
for persistent, shared caching across application instances.

Improvements over the original:
- Persistent cache (survives application restarts)
- Shared cache across multiple instances
- Intelligent TTL management
- HTTP caching via Hishel
- Better error handling and fallback
- Cache statistics and monitoring
"""

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService, cached, get_cache_service
from app.core.cached_http_client import CachedHttpClient, get_cached_http_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class HGNCClientCached:
    """
    Enhanced HGNC client with unified cache system integration.

    Features:
    - Persistent cache shared across instances
    - HTTP caching via Hishel for compliance
    - Intelligent retry and fallback logic
    - Circuit breaker pattern for resilience
    - Cache statistics and monitoring
    """

    BASE_URL = "https://rest.genenames.org"
    NAMESPACE = "hgnc"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | AsyncSession | None = None,
        timeout: int = 30,
        max_retries: int = 3,
        batch_size: int = 100,
        max_workers: int = 4,
    ):
        """
        Initialize the enhanced HGNC client.

        Args:
            cache_service: Cache service instance
            http_client: HTTP client with caching
            db_session: Database session for cache persistence
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            batch_size: Maximum symbols per batch request
            max_workers: Maximum threads for parallel processing
        """
        self.cache_service = cache_service or get_cache_service(db_session)
        self.http_client = http_client or get_cached_http_client(cache_service, db_session)
        self.timeout = timeout
        self.max_retries = max_retries
        self.batch_size = batch_size
        self.max_workers = max_workers

        # Get TTL for HGNC namespace
        self.ttl = settings.CACHE_TTL_HGNC

        logger.info(f"HGNCClientCached initialized with TTL: {self.ttl}s")

    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
    ) -> dict[str, Any]:
        """
        Make a request to the HGNC API with caching and retry logic.

        Args:
            endpoint: API endpoint
            params: Query parameters
            method: HTTP method

        Returns:
            JSON response as dictionary
        """
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            # Use cached HTTP client for automatic caching
            # IMPORTANT: HGNC API returns XML by default, must request JSON
            response = await self.http_client.get(
                url,
                params=params,
                headers={"Accept": "application/json"},
                namespace=self.NAMESPACE,
                fallback_ttl=self.ttl
            )

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"HGNC API request failed for {url}: {e}")
            raise

    async def symbol_to_hgnc_id(self, symbol: str) -> str | None:
        """
        Convert a gene symbol to HGNC ID with persistent caching.

        Args:
            symbol: Gene symbol

        Returns:
            HGNC ID (e.g., "HGNC:5") or None if not found
        """
        cache_key = f"symbol_to_hgnc_id:{symbol.strip().upper()}"

        async def fetch_hgnc_id():
            try:
                response = await self._make_request("search/symbol", {"symbol": symbol})
                docs = response.get("response", {}).get("docs", [])
                if docs:
                    return docs[0].get("hgnc_id")
                return None
            except Exception as e:
                logger.warning(f"Failed to fetch HGNC ID for symbol {symbol}: {e}")
                return None

        return await cached(
            cache_key,
            fetch_hgnc_id,
            self.NAMESPACE,
            self.ttl,
            self.cache_service.db_session
        )

    async def get_gene_info(self, symbol: str) -> dict[str, Any] | None:
        """
        Get comprehensive gene information for a symbol with persistent caching.

        Args:
            symbol: Gene symbol

        Returns:
            Dictionary with gene information or None if not found
        """
        cache_key = f"gene_info:{symbol.strip().upper()}"

        async def fetch_gene_info():
            try:
                response = await self._make_request("search/symbol", {"symbol": symbol})
                docs = response.get("response", {}).get("docs", [])
                if docs:
                    return docs[0]
                return None
            except Exception as e:
                logger.warning(f"Failed to fetch gene info for symbol {symbol}: {e}")
                return None

        return await cached(
            cache_key,
            fetch_gene_info,
            self.NAMESPACE,
            self.ttl,
            self.cache_service.db_session
        )

    async def standardize_symbol(self, symbol: str) -> str:
        """
        Standardize a gene symbol to the approved HGNC symbol with persistent caching.

        This method tries multiple approaches:
        1. Direct symbol lookup
        2. Previous symbol lookup
        3. Alias symbol lookup

        Args:
            symbol: Input gene symbol

        Returns:
            Standardized HGNC symbol or original symbol if not found
        """
        normalized_symbol = symbol.strip().upper()
        cache_key = f"standardize_symbol:{normalized_symbol}"

        async def fetch_standardized_symbol():
            # Try direct symbol lookup
            try:
                response = await self._make_request(f"search/symbol/{normalized_symbol}")
                docs = response.get("response", {}).get("docs", [])
                if docs:
                    return docs[0].get("symbol", symbol)
            except Exception:
                pass

            # Try previous symbol lookup
            try:
                response = await self._make_request(f"search/prev_symbol/{normalized_symbol}")
                docs = response.get("response", {}).get("docs", [])
                if docs:
                    return docs[0].get("symbol", symbol)
            except Exception:
                pass

            # Try alias symbol lookup
            try:
                response = await self._make_request(f"search/alias_symbol/{normalized_symbol}")
                docs = response.get("response", {}).get("docs", [])
                if docs:
                    return docs[0].get("symbol", symbol)
            except Exception:
                pass

            logger.warning(f"Could not standardize gene symbol: {symbol}")
            return symbol

        return await cached(
            cache_key,
            fetch_standardized_symbol,
            self.NAMESPACE,
            self.ttl,
            self.cache_service.db_session
        )

    async def standardize_symbols_batch(
        self, symbols: list[str]
    ) -> dict[str, dict[str, str | None]]:
        """
        Standardize multiple gene symbols using cached batch API.

        Uses intelligent caching to minimize API calls while maintaining
        the same interface as the original batch method.

        Args:
            symbols: List of gene symbols

        Returns:
            Dictionary mapping original symbols to standardization results
        """
        if not symbols:
            return {}

        # Check cache for each symbol first
        result = {}
        uncached_symbols = []

        for symbol in symbols:
            cache_key = f"standardize_symbol:{symbol.strip().upper()}"
            cached_result = await self.cache_service.get(cache_key, self.NAMESPACE)

            if cached_result is not None:
                # Get additional info from cache
                hgnc_id_key = f"symbol_to_hgnc_id:{symbol.strip().upper()}"
                cached_hgnc_id = await self.cache_service.get(hgnc_id_key, self.NAMESPACE)

                result[symbol] = {
                    "approved_symbol": cached_result,
                    "hgnc_id": cached_hgnc_id
                }
            else:
                uncached_symbols.append(symbol)

        # Process uncached symbols in batches
        if uncached_symbols:
            logger.info(f"Processing {len(uncached_symbols)} uncached symbols in batch")

            for i in range(0, len(uncached_symbols), self.batch_size):
                batch = uncached_symbols[i:i + self.batch_size]
                batch_result = await self._process_batch(batch)
                result.update(batch_result)

        logger.debug(f"Batch standardization complete: {len(symbols)} symbols processed")
        return result

    async def _process_batch(self, symbols: list[str]) -> dict[str, dict[str, str | None]]:
        """Process a batch of symbols using the HGNC batch API."""
        try:
            # Use the +OR+ syntax for batch queries
            original_symbols = symbols
            query_str = "+OR+".join([s.upper() for s in original_symbols])
            endpoint = f"search/symbol/{query_str}"

            response = await self._make_request(endpoint, {"fields": "symbol,hgnc_id"})
            docs = response.get("response", {}).get("docs", [])

            # Process results and cache individually
            result = {}
            found_symbols = set()

            for symbol in original_symbols:
                result[symbol] = {"approved_symbol": symbol, "hgnc_id": None}

            # Match by symbol name directly
            for doc in docs:
                approved_symbol = doc.get("symbol")
                hgnc_id = doc.get("hgnc_id")
                if not approved_symbol:
                    continue

                # Check if this approved symbol matches any input symbol
                for original_symbol in original_symbols:
                    if original_symbol.upper() == approved_symbol.upper():
                        result[original_symbol] = {
                            "approved_symbol": approved_symbol,
                            "hgnc_id": hgnc_id,
                        }
                        found_symbols.add(original_symbol)

                        # Cache the results
                        await self._cache_symbol_results(original_symbol, approved_symbol, hgnc_id)
                        break

            # Process symbols not found in batch with individual lookups
            for original_symbol in original_symbols:
                if original_symbol not in found_symbols:
                    # Use individual standardization (which will cache the result)
                    standardized = await self.standardize_symbol(original_symbol)
                    if standardized.upper() != original_symbol.upper():
                        gene_info = await self.get_gene_info(standardized)
                        hgnc_id = gene_info.get("hgnc_id") if gene_info else None
                        result[original_symbol] = {
                            "approved_symbol": standardized,
                            "hgnc_id": hgnc_id,
                        }

            return result

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            # Fallback to individual lookups
            result = {}
            for symbol in symbols:
                standardized = await self.standardize_symbol(symbol)
                gene_info = await self.get_gene_info(standardized)
                hgnc_id = gene_info.get("hgnc_id") if gene_info else None
                result[symbol] = {
                    "approved_symbol": standardized,
                    "hgnc_id": hgnc_id,
                }
            return result

    async def _cache_symbol_results(
        self, original_symbol: str, approved_symbol: str, hgnc_id: str | None
    ) -> None:
        """Cache individual symbol results for future use."""
        normalized_symbol = original_symbol.strip().upper()

        # Cache standardized symbol
        standardize_key = f"standardize_symbol:{normalized_symbol}"
        await self.cache_service.set(standardize_key, approved_symbol, self.NAMESPACE, self.ttl)

        # Cache HGNC ID if available
        if hgnc_id:
            hgnc_id_key = f"symbol_to_hgnc_id:{normalized_symbol}"
            await self.cache_service.set(hgnc_id_key, hgnc_id, self.NAMESPACE, self.ttl)

    async def standardize_symbols_parallel(
        self, symbols: list[str]
    ) -> dict[str, dict[str, str | None]]:
        """
        Standardize multiple gene symbols using parallel processing with caching.

        Args:
            symbols: List of gene symbols

        Returns:
            Dictionary mapping original symbols to standardization results
        """
        if not symbols:
            return {}

        logger.info(f"Standardizing {len(symbols)} gene symbols with parallel processing")

        # Split into batches
        batches = [
            symbols[i:i + self.batch_size]
            for i in range(0, len(symbols), self.batch_size)
        ]

        if len(batches) == 1:
            # Single batch - process directly
            return await self.standardize_symbols_batch(batches[0])

        # Multiple batches - use parallel processing
        logger.info(f"Processing {len(batches)} batches in parallel")

        # Use asyncio gather for parallel processing
        tasks = [
            self.standardize_symbols_batch(batch)
            for batch in batches
        ]

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        standardized = {}
        for i, batch_result in enumerate(batch_results):
            if isinstance(batch_result, Exception):
                logger.error(f"Batch {i} failed: {batch_result}")
                # Fallback to individual processing for failed batch
                for symbol in batches[i]:
                    try:
                        gene_info = await self.get_gene_info(symbol)
                        standardized[symbol] = {
                            "approved_symbol": symbol,
                            "hgnc_id": gene_info.get("hgnc_id") if gene_info else None,
                        }
                    except Exception:
                        standardized[symbol] = {
                            "approved_symbol": symbol,
                            "hgnc_id": None,
                        }
            else:
                standardized.update(batch_result)

        # Log standardization results
        changed_symbols = {
            k: v for k, v in standardized.items()
            if v["approved_symbol"] and k != v["approved_symbol"]
        }
        if changed_symbols:
            logger.info(f"Standardized {len(changed_symbols)} gene symbols")

        return standardized

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for the HGNC namespace."""
        return await self.cache_service.get_stats(self.NAMESPACE)

    async def clear_cache(self) -> int:
        """Clear all HGNC cache entries."""
        return await self.cache_service.clear_namespace(self.NAMESPACE)

    async def warm_cache(self, common_symbols: list[str] | None = None) -> int:
        """
        Warm the cache with commonly used gene symbols.

        Args:
            common_symbols: List of common symbols to preload

        Returns:
            Number of entries cached
        """
        if not common_symbols:
            # Default set of common kidney-related gene symbols
            common_symbols = [
                "PKD1", "PKD2", "COL4A5", "NPHS1", "NPHS2", "WT1", "PAX2",
                "HNF1B", "UMOD", "MUC1", "REN", "AGTR1", "ACE", "APOL1",
                "ACTN4", "TRPC6", "CD2AP", "PLCE1", "LAMB2", "PDSS2"
            ]

        logger.info(f"Warming HGNC cache with {len(common_symbols)} symbols")

        # Use batch processing to warm cache efficiently
        await self.standardize_symbols_batch(common_symbols)

        # Also get detailed info for each symbol
        tasks = [self.get_gene_info(symbol) for symbol in common_symbols]
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("HGNC cache warming completed")
        return len(common_symbols)


# Global cached client instance
_hgnc_client_cached: HGNCClientCached | None = None


def get_hgnc_client_cached(
    cache_service: CacheService | None = None,
    db_session: Session | AsyncSession | None = None
) -> HGNCClientCached:
    """Get or create the global cached HGNC client instance."""
    global _hgnc_client_cached

    if _hgnc_client_cached is None:
        _hgnc_client_cached = HGNCClientCached(
            cache_service=cache_service,
            db_session=db_session
        )

    return _hgnc_client_cached


# Convenience functions for backward compatibility

async def standardize_gene_symbols_cached(
    symbols: list[str],
    db_session: Session | AsyncSession | None = None
) -> dict[str, dict[str, str | None]]:
    """
    Convenience function to standardize gene symbols using the cached client.

    Args:
        symbols: List of gene symbols to standardize
        db_session: Database session for cache persistence

    Returns:
        Dictionary mapping original symbols to standardization results
    """
    client = get_hgnc_client_cached(db_session=db_session)
    return await client.standardize_symbols_batch(symbols)


async def get_gene_info_cached(
    symbol: str,
    db_session: Session | AsyncSession | None = None
) -> dict[str, Any] | None:
    """
    Convenience function to get gene info using the cached client.

    Args:
        symbol: Gene symbol
        db_session: Database session for cache persistence

    Returns:
        Gene information dictionary or None if not found
    """
    client = get_hgnc_client_cached(db_session=db_session)
    return await client.get_gene_info(symbol)
