"""
PubTator data source integration with unified cache system.

Fetches kidney disease-related gene mentions from biomedical literature
using the enhanced caching infrastructure.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService, cached, get_cache_service
from app.core.cached_http_client import CachedHttpClient, get_cached_http_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class PubTatorClientCached:
    """
    Enhanced PubTator client with unified cache system integration.
    
    Features:
    - Persistent cache shared across instances
    - HTTP caching via Hishel for API compliance
    - Intelligent retry and fallback logic
    - Circuit breaker pattern for resilience
    - Database-backed cache storage
    """

    NAMESPACE = "pubtator"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | AsyncSession | None = None,
    ):
        """Initialize the enhanced PubTator client."""
        self.cache_service = cache_service or get_cache_service(db_session)
        self.http_client = http_client or get_cached_http_client(cache_service, db_session)

        # PubTator configuration from settings
        self.base_url = settings.PUBTATOR_API_URL
        self.kidney_query = settings.PUBTATOR_SEARCH_QUERY
        self.max_pages_per_run = settings.PUBTATOR_MAX_PAGES
        self.use_cache = settings.PUBTATOR_USE_CACHE
        self.batch_size = settings.PUBTATOR_BATCH_SIZE
        self.rate_limit_delay = settings.PUBTATOR_RATE_LIMIT_DELAY
        self.min_date = settings.PUBTATOR_MIN_DATE

        # Get TTL for PubTator namespace
        self.ttl = settings.CACHE_TTL_PUBTATOR

        logger.info(f"PubTatorClientCached initialized with TTL: {self.ttl}s")

    async def search_publications(self, query: str, max_results: int = 100) -> list[str]:
        """
        Search PubMed for kidney-related publications with caching.
        
        Args:
            query: Search query
            max_results: Maximum number of PMIDs to return
        
        Returns:
            List of PMIDs
        """
        cache_key = f"pubmed_search:{query}:{max_results}:{self.min_date}"

        async def fetch_pmids():
            try:
                # Use PubMed E-utilities for search
                url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
                params = {
                    "db": "pubmed",
                    "term": f"{query} AND genetics[MeSH]",
                    "retmax": max_results,
                    "retmode": "json",
                    "sort": "relevance",
                    "mindate": self.min_date,
                }

                response = await self.http_client.get(
                    url,
                    params=params,
                    namespace=self.NAMESPACE,
                    fallback_ttl=self.ttl
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("esearchresult", {}).get("idlist", [])
                return []

            except Exception as e:
                logger.error(f"Error searching PubMed for query '{query}': {e}")
                return []

        return await cached(
            cache_key,
            fetch_pmids,
            self.NAMESPACE,
            self.ttl,
            self.cache_service.db_session
        )

    async def get_annotations_by_search(
        self,
        query: str,
        max_pages: int | None = None,
        tracker=None
    ) -> dict[str, Any]:
        """
        Get PubTator annotations by searching with enhanced caching support.
        
        Args:
            query: Search query
            max_pages: Maximum number of pages to fetch (None = use configured limit)
            tracker: Progress tracker for updates
        
        Returns:
            Dictionary mapping gene symbols to annotation data
        """
        # Create cache key for the complete query result
        pages_key = max_pages or self.max_pages_per_run
        cache_key = f"search_annotations:{query}:{pages_key}"

        # Check cache first
        if self.use_cache:
            cached_data = await self.cache_service.get(cache_key, self.NAMESPACE)
            if cached_data and cached_data.get("complete", False):
                logger.info(f"Using cached data for query: {query[:50]}...")
                return cached_data.get("gene_annotations", {})

        # Fetch new data
        gene_annotations = await self._fetch_annotations_from_api(query, max_pages, tracker)

        # Cache the results if enabled
        if self.use_cache and gene_annotations:
            # Determine if this is a complete result
            total_pages = getattr(self, '_last_total_pages', 1)
            actual_pages = min(max_pages or self.max_pages_per_run, total_pages)
            is_complete = (actual_pages >= total_pages)

            cache_data = {
                "gene_annotations": gene_annotations,
                "complete": is_complete,
                "total_genes": len(gene_annotations),
                "pages_processed": actual_pages,
                "total_pages": total_pages,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

            await self.cache_service.set(cache_key, cache_data, self.NAMESPACE, self.ttl)
            logger.info(f"Cached {len(gene_annotations)} genes for future use")

        return gene_annotations

    async def _fetch_annotations_from_api(
        self,
        query: str,
        max_pages: int | None = None,
        tracker=None
    ) -> dict[str, Any]:
        """Fetch annotations from PubTator API with caching per step."""
        gene_annotations = {}
        all_pmids = []

        # Step 1: Get total pages and determine processing limit
        total_pages = await self._get_total_pages(query)
        self._last_total_pages = total_pages

        if max_pages is None:
            max_pages = min(self.max_pages_per_run, total_pages)
        else:
            max_pages = min(max_pages, total_pages)

        logger.info(f"Will process {max_pages} pages (configured limit: {self.max_pages_per_run})")

        # Step 2: Search for PMIDs using cached requests
        all_pmids = await self._fetch_pmids_from_search(query, max_pages, tracker)

        # Step 3: Get annotations for collected PMIDs (in batches)
        if all_pmids:
            gene_annotations = await self._fetch_annotations_for_pmids(all_pmids, tracker)

        return gene_annotations

    async def _get_total_pages(self, query: str) -> int:
        """Get total pages available for a query with caching."""
        cache_key = f"total_pages:{query}"

        async def fetch_total_pages():
            try:
                url = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/search/"
                response = await self.http_client.get(
                    url,
                    params={"text": query, "page": 1},
                    namespace=self.NAMESPACE,
                    fallback_ttl=3600  # Cache for 1 hour
                )

                if response.status_code == 200:
                    data = response.json()
                    total_pages = data.get("total_pages", 1)
                    logger.info(f"PubTator search has {total_pages} total pages")
                    return total_pages
                return 1

            except Exception as e:
                logger.error(f"Error getting total pages: {e}")
                return 1

        return await cached(
            cache_key,
            fetch_total_pages,
            self.NAMESPACE,
            3600,  # 1 hour TTL for page count
            self.cache_service.db_session
        )

    async def _fetch_pmids_from_search(
        self,
        query: str,
        max_pages: int,
        tracker=None
    ) -> list[str]:
        """Fetch PMIDs from search pages with individual page caching."""
        all_pmids = []

        # Create tasks for parallel page fetching (but limit concurrency)
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent requests

        async def fetch_page(page: int) -> list[str]:
            async with semaphore:
                cache_key = f"search_page:{query}:{page}"

                async def fetch_page_data():
                    try:
                        url = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/search/"
                        response = await self.http_client.get(
                            url,
                            params={"text": query, "page": page},
                            namespace=self.NAMESPACE,
                            fallback_ttl=self.ttl
                        )

                        if response.status_code != 200:
                            logger.warning(f"PubTator3 search returned status {response.status_code}")
                            return []

                        data = response.json()
                        results = data.get("results", [])

                        # Extract PMIDs
                        pmids = []
                        for result in results:
                            pmid = result.get("pmid")
                            if pmid:
                                pmids.append(str(pmid))

                        return pmids

                    except Exception as e:
                        logger.error(f"Error fetching PubTator3 search page {page}: {e}")
                        return []

                pmids = await cached(
                    cache_key,
                    fetch_page_data,
                    self.NAMESPACE,
                    self.ttl,
                    self.cache_service.db_session
                )

                # Add rate limiting
                await asyncio.sleep(self.rate_limit_delay)

                return pmids

        # Fetch pages in batches to respect rate limits
        batch_size = 5
        for batch_start in range(1, max_pages + 1, batch_size):
            batch_end = min(batch_start + batch_size, max_pages + 1)
            page_numbers = list(range(batch_start, batch_end))

            # Create tasks for this batch
            tasks = [fetch_page(page) for page in page_numbers]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for i, result in enumerate(batch_results):
                page = page_numbers[i]
                if isinstance(result, Exception):
                    logger.error(f"Page {page} failed: {result}")
                    continue

                all_pmids.extend(result)

                # Log progress every 10 pages
                if page % 10 == 0 or page == 1:
                    logger.info(f"Processing page {page}/{max_pages}: found {len(all_pmids)} PMIDs so far")
                    if tracker:
                        tracker.update(current_page=page, operation=f"Fetching page {page}/{max_pages}")

        return all_pmids

    async def _fetch_annotations_for_pmids(
        self,
        all_pmids: list[str],
        tracker=None
    ) -> dict[str, Any]:
        """Fetch annotations for PMIDs with batch caching."""
        gene_annotations = {}
        total_batches = (len(all_pmids) + self.batch_size - 1) // self.batch_size
        logger.info(f"Processing {len(all_pmids)} PMIDs in {total_batches} batches of {self.batch_size}")

        for batch_num, i in enumerate(range(0, len(all_pmids), self.batch_size), 1):
            batch_pmids = all_pmids[i : i + self.batch_size]
            pmids_str = ",".join(batch_pmids)

            if batch_num % 5 == 0 or batch_num == 1:
                logger.info(f"Processing annotation batch {batch_num}/{total_batches}")
                if tracker:
                    tracker.update(operation=f"Processing annotations batch {batch_num}/{total_batches}")

            # Cache key for this batch
            cache_key = f"annotations_batch:{pmids_str[:50]}:{len(batch_pmids)}"

            async def fetch_batch_annotations():
                try:
                    url = "https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/biocjson"
                    response = await self.http_client.get(
                        url,
                        params={"pmids": pmids_str, "concepts": "gene"},
                        namespace=self.NAMESPACE,
                        fallback_ttl=self.ttl
                    )

                    if response.status_code == 200:
                        data = response.json()
                        return self._parse_annotations(data)
                    return {}

                except Exception as e:
                    logger.error(f"Error fetching PubTator3 annotations for batch: {e}")
                    return {}

            batch_annotations = await cached(
                cache_key,
                fetch_batch_annotations,
                self.NAMESPACE,
                self.ttl,
                self.cache_service.db_session
            )

            # Merge batch results
            self._merge_annotations(gene_annotations, batch_annotations)

            # Rate limiting for batch requests
            await asyncio.sleep(self.rate_limit_delay * 1.5)

        return gene_annotations

    def _parse_annotations(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse PubTator response data into gene annotations."""
        gene_annotations = {}
        articles = data.get("PubTator3", [])

        for article in articles:
            pmid = article.get("pmid")
            passages = article.get("passages", [])

            for passage in passages:
                annotations = passage.get("annotations", [])

                for ann in annotations:
                    if ann.get("infons", {}).get("type") == "Gene":
                        gene_text = ann.get("text", "")
                        gene_id = ann.get("infons", {}).get("identifier")

                        if gene_text:
                            symbol = self.normalize_gene_symbol(gene_text)
                            if symbol:
                                if symbol not in gene_annotations:
                                    gene_annotations[symbol] = {
                                        "pmids": set(),
                                        "mentions": 0,
                                        "ncbi_gene_ids": set(),
                                    }

                                gene_annotations[symbol]["pmids"].add(str(pmid))
                                gene_annotations[symbol]["mentions"] += 1
                                if gene_id:
                                    gene_annotations[symbol]["ncbi_gene_ids"].add(gene_id)

        # Convert sets to lists for JSON serialization
        for gene_data in gene_annotations.values():
            gene_data["pmids"] = list(gene_data["pmids"])
            gene_data["ncbi_gene_ids"] = list(gene_data["ncbi_gene_ids"])

        return gene_annotations

    def _merge_annotations(
        self,
        target: dict[str, Any],
        source: dict[str, Any]
    ) -> None:
        """Merge source annotations into target."""
        for symbol, data in source.items():
            if symbol not in target:
                target[symbol] = {
                    "pmids": set(),
                    "mentions": 0,
                    "ncbi_gene_ids": set(),
                }

            # Ensure target fields are sets for merging
            if isinstance(target[symbol]["pmids"], list):
                target[symbol]["pmids"] = set(target[symbol]["pmids"])
            if isinstance(target[symbol]["ncbi_gene_ids"], list):
                target[symbol]["ncbi_gene_ids"] = set(target[symbol]["ncbi_gene_ids"])

            # Merge data
            if isinstance(data["pmids"], list):
                target[symbol]["pmids"].update(data["pmids"])
            else:
                target[symbol]["pmids"].update(data["pmids"])

            target[symbol]["mentions"] += data["mentions"]

            if isinstance(data["ncbi_gene_ids"], list):
                target[symbol]["ncbi_gene_ids"].update(data["ncbi_gene_ids"])
            else:
                target[symbol]["ncbi_gene_ids"].update(data["ncbi_gene_ids"])

        # Convert back to lists
        for gene_data in target.values():
            if isinstance(gene_data["pmids"], set):
                gene_data["pmids"] = list(gene_data["pmids"])
            if isinstance(gene_data["ncbi_gene_ids"], set):
                gene_data["ncbi_gene_ids"] = list(gene_data["ncbi_gene_ids"])

    def normalize_gene_symbol(self, gene_text: str) -> str | None:
        """
        Normalize gene text to standard symbol.
        
        Args:
            gene_text: Gene text from PubTator
        
        Returns:
            Normalized gene symbol or None
        """
        if not gene_text:
            return None

        # Remove common suffixes/prefixes
        symbol = gene_text.upper()
        symbol = symbol.replace("HUMAN", "").strip()

        # Basic validation
        if len(symbol) > 1 and symbol[0].isalpha():
            return symbol

        return None

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for the PubTator namespace."""
        return await self.cache_service.get_stats(self.NAMESPACE)

    async def clear_cache(self) -> int:
        """Clear all PubTator cache entries."""
        return await self.cache_service.clear_namespace(self.NAMESPACE)

    async def warm_cache(self, common_queries: list[str] | None = None) -> int:
        """
        Warm the cache with commonly used queries.
        
        Args:
            common_queries: List of common queries to preload
        
        Returns:
            Number of entries cached
        """
        if not common_queries:
            # Default kidney disease query
            common_queries = [self.kidney_query]

        logger.info(f"Warming PubTator cache with {len(common_queries)} queries")

        entries_cached = 0
        for query in common_queries:
            try:
                # Process limited pages for cache warming
                await self.get_annotations_by_search(query, max_pages=5)
                entries_cached += 1
            except Exception as e:
                logger.error(f"Error warming cache for query '{query}': {e}")

        logger.info("PubTator cache warming completed")
        return entries_cached


# Global cached client instance
_pubtator_client_cached: PubTatorClientCached | None = None


def get_pubtator_client_cached(
    cache_service: CacheService | None = None,
    db_session: Session | AsyncSession | None = None
) -> PubTatorClientCached:
    """Get or create the global cached PubTator client instance."""
    global _pubtator_client_cached

    if _pubtator_client_cached is None:
        _pubtator_client_cached = PubTatorClientCached(
            cache_service=cache_service,
            db_session=db_session
        )

    return _pubtator_client_cached


# Convenience functions for backward compatibility

async def search_publications_cached(
    query: str,
    max_results: int = 100,
    db_session: Session | AsyncSession | None = None
) -> list[str]:
    """
    Convenience function to search publications using the cached client.
    
    Args:
        query: Search query
        max_results: Maximum number of results
        db_session: Database session for cache persistence
    
    Returns:
        List of PMIDs
    """
    client = get_pubtator_client_cached(db_session=db_session)
    return await client.search_publications(query, max_results)


async def get_annotations_by_search_cached(
    query: str,
    max_pages: int | None = None,
    tracker=None,
    db_session: Session | AsyncSession | None = None
) -> dict[str, Any]:
    """
    Convenience function to get annotations using the cached client.
    
    Args:
        query: Search query
        max_pages: Maximum pages to process
        tracker: Progress tracker
        db_session: Database session for cache persistence
    
    Returns:
        Gene annotations dictionary
    """
    client = get_pubtator_client_cached(db_session=db_session)
    return await client.get_annotations_by_search(query, max_pages, tracker)
