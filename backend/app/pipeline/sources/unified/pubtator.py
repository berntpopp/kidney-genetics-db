"""
Unified PubTator data source implementation.

This module replaces the previous implementations (pubtator.py, pubtator_async.py,
pubtator_cache.py, pubtator_cached.py) with a single, async-first implementation.
"""

import asyncio
import logging
from datetime import datetime, timezone

# Import for type hint only
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.datasource_config import get_source_parameter
from app.pipeline.sources.unified.base import UnifiedDataSource

if TYPE_CHECKING:
    from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class PubTatorUnifiedSource(UnifiedDataSource):
    """
    Unified PubTator client with intelligent caching and async processing.

    Features:
    - Async-first design with batch processing
    - Literature mining from PubMed/PubTator
    - Kidney disease-specific search queries
    - Gene mention aggregation from abstracts
    - Rate limiting and pagination support
    """

    @property
    def source_name(self) -> str:
        return "PubTator"

    @property
    def namespace(self) -> str:
        return "pubtator"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | None = None,
        **kwargs,
    ):
        """Initialize PubTator client with literature mining capabilities."""
        super().__init__(cache_service, http_client, db_session, **kwargs)

        # PubTator configuration from datasource config
        self.base_url = get_source_parameter(
            "PubTator", "api_url", "https://www.ncbi.nlm.nih.gov/research/pubtator-api"
        )

        # Search configuration from datasource config
        self.kidney_query = get_source_parameter(
            "PubTator",
            "search_query",
            '("kidney disease" OR "renal disease") AND (gene OR syndrome) AND (variant OR mutation)',
        )
        self.max_pages = get_source_parameter("PubTator", "max_pages", 100)  # Default to 100 pages
        self.rate_limit_delay = max(
            get_source_parameter("PubTator", "rate_limit_delay", 0.3), 0.5
        )  # Min 0.5s delay
        # Sort order: "score desc" for relevance, "date desc" for recency
        self.sort_order = "score desc"  # Fixed value as per datasource_config

        # Gene annotation types to extract
        self.annotation_types = ["Gene", "GeneID"]

        max_pages_str = "ALL" if self.max_pages is None else str(self.max_pages)
        logger.info(
            f"PubTatorUnifiedSource initialized with max pages: {max_pages_str}, sort: {self.sort_order}"
        )

    def _get_default_ttl(self) -> int:
        """Get default TTL for PubTator data."""
        return get_source_parameter("PubTator", "cache_ttl", 604800)

    async def fetch_raw_data(self, tracker: "ProgressTracker" = None) -> dict[str, Any]:
        """
        Fetch kidney disease-related publications directly from PubTator3.
        Uses PubTator3's native search API which returns annotations directly.

        Returns:
            Dictionary with PMIDs and gene annotations
        """
        logger.info("🧬 PUBTATOR SOURCE: fetch_raw_data() METHOD CALLED")
        logger.info(f"🧬 PUBTATOR SOURCE: kidney_query = '{self.kidney_query}'")

        # Search PubTator3 directly - returns complete results with annotations
        logger.info("🧬 PUBTATOR SOURCE: Calling _search_pubtator3()...")
        search_results = await self._search_pubtator3(self.kidney_query, tracker)
        logger.info(f"🧬 PUBTATOR SOURCE: Search returned {len(search_results)} articles")

        if not search_results:
            logger.warning("No publications found for kidney disease query")
            return {}

        # Process search results into our annotation format
        annotations = self._process_search_results(search_results)
        pmids = list(annotations.keys())

        logger.info(f"🎯 Processed {len(annotations)} articles with gene annotations")

        return {
            "pmids": pmids,
            "annotations": annotations,
            "query": self.kidney_query,
            "fetch_date": datetime.now(timezone.utc).isoformat(),
            "total_results": len(search_results),
        }

    def _process_search_results(self, results: list[dict]) -> dict[str, Any]:
        """
        Process PubTator3 search results into gene annotations.
        Extracts genes from the text_hl field.

        Args:
            results: List of search results from PubTator3

        Returns:
            Dictionary mapping PMIDs to annotations
        """
        annotations = {}

        for result in results:
            pmid = str(result.get("pmid", ""))
            if not pmid:
                continue

            # Extract genes from highlighted text
            genes = self._extract_genes_from_highlight(result.get("text_hl", ""))

            # Include all results with their scores
            annotations[pmid] = {
                "pmid": pmid,
                "title": result.get("title", ""),
                "abstract": result.get("text_hl", ""),  # Contains highlighted annotations
                "journal": result.get("journal", ""),
                "authors": result.get("authors", []),
                "date": result.get("date", ""),
                "score": result.get("score", 0),
                "genes": genes,
                "doi": result.get("doi", ""),
            }

        return annotations

    def _extract_genes_from_highlight(self, text_hl: str | None) -> list[dict]:
        """
        Extract gene annotations from PubTator3's highlighted text.

        Format: @GENE_[symbol] @GENE_[id] @@@[display]@@@
        Example: @GENE_PAX2 @GENE_5076 @@@PAX2@@@

        Args:
            text_hl: Highlighted text with annotations (can be None)

        Returns:
            List of gene dictionaries
        """
        import re

        # Handle None or empty text
        if not text_hl:
            return []

        genes = []
        seen = set()  # Deduplicate

        # Pattern to match gene annotations
        # @GENE_symbol @GENE_id @@@display@@@
        pattern = r"@GENE_(\w+)\s+@GENE_(\d+)\s+@@@([^@]+)@@@"

        for match in re.finditer(pattern, text_hl):
            symbol = match.group(1)
            gene_id = match.group(2)
            display = match.group(3)

            # Create unique key for deduplication
            key = f"{symbol}:{gene_id}"
            if key not in seen:
                seen.add(key)
                genes.append(
                    {
                        "text": display,
                        "identifier": gene_id,
                        "type": "Gene",
                        "symbol": symbol,
                    }
                )

        return genes

    async def _search_pubtator3(self, query: str, tracker: "ProgressTracker" = None) -> list[dict]:
        """
        Search PubTator3 directly using its native search API.

        Args:
            query: Search query

        Returns:
            List of article results with annotations
        """
        all_results = []
        page = 1
        total_fetched = 0
        total_pages = None  # Will be set from API response
        consecutive_failures = 0  # Track consecutive failures
        max_consecutive_failures = 3  # Stop after 3 consecutive failures

        while True:
            # Use PubTator3's native search endpoint
            search_url = f"{self.base_url}/search/"
            params = {
                "text": query,
                "filters": "{}",  # Empty filters object
                "page": page,
                "sort": self.sort_order,  # Configurable: "score desc" or "date desc"
            }

            # Log progress
            if self.max_pages is not None:
                logger.info(f"🔍 PubTator3 search page {page}/{self.max_pages}")
            else:
                logger.info(
                    f"🔍 PubTator3 search page {page}/{total_pages if total_pages else '?'}"
                )

            try:
                logger.info(f"🔍 Page {page}: Starting request to PubTator API")
                logger.debug(f"🔍 Page {page}: URL: {search_url}")
                logger.debug(f"🔍 Page {page}: Params: {params}")
                logger.debug(f"🔍 Page {page}: Using retry strategy with timeout=60s")

                # Use existing retry strategy - it already has exponential backoff
                response = await self.retry_strategy.execute_async(
                    lambda url=search_url, p=params: self.http_client.get(url, params=p, timeout=60)
                )

                logger.info(f"🔍 Page {page}: Request completed successfully")

                # Reset consecutive failures on successful response
                consecutive_failures = 0
                logger.debug(
                    f"🔍 Response received for page {page}, status: {response.status_code}"
                )
                logger.debug(f"🔍 Response headers: {dict(response.headers)}")

                if response.status_code != 200:
                    logger.error(
                        f"PubTator3 search failed on page {page}: HTTP {response.status_code}"
                    )
                    logger.error(f"Response content preview: {response.text[:500]}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(f"🛑 Stopping after {consecutive_failures} consecutive errors")
                        break
                    continue

                logger.debug(f"🔍 Page {page}: Starting JSON parsing...")
                try:
                    data = response.json()
                    logger.debug(
                        f"🔍 Page {page}: JSON parsed successfully, keys: {list(data.keys())}"
                    )
                    logger.debug(f"🔍 Page {page}: Response size: {len(response.text)} bytes")
                except Exception as json_err:
                    logger.error(f"🔍 Page {page}: Failed to parse JSON: {json_err}")
                    logger.error(f"🔍 Page {page}: Response preview: {response.text[:500]}")
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(
                            f"🛑 Stopping after {consecutive_failures} consecutive parse errors"
                        )
                        break
                    continue

                results = data.get("results", [])
                logger.debug(f"🔍 Page {page}: Found {len(results)} results")

                # Get total pages from API response
                if total_pages is None:
                    total_pages = data.get("total_pages", 0)
                    total_available = data.get("count", 0)
                    logger.info(
                        f"📊 Total available: {total_available} articles across {total_pages} pages"
                    )

                    # Initialize tracker with actual limit we'll process
                    if tracker:
                        actual_pages = (
                            min(self.max_pages, total_pages) if self.max_pages else total_pages
                        )
                        actual_items = (
                            min(self.max_pages * 10, total_available)
                            if self.max_pages
                            else total_available
                        )
                        tracker.update(total_pages=actual_pages, total_items=actual_items)

                if not results:
                    logger.info(f"No more results at page {page}")
                    break

                all_results.extend(results)
                total_fetched += len(results)

                # Progress logging and tracker update
                total_available = data.get("count", 0)
                logger.info(
                    f"Page {page}: {len(results)} results (total fetched: {total_fetched}/{total_available})"
                )
                logger.debug(
                    f"🔍 Page {page}: Memory usage: all_results contains {len(all_results)} items"
                )

                # Update tracker with current progress
                if tracker:
                    actual_pages = (
                        min(self.max_pages, total_pages) if self.max_pages else total_pages
                    )
                    logger.debug(
                        f"🔍 Page {page}: Updating tracker - current_page={page}, current_item={total_fetched}"
                    )
                    tracker.update(
                        current_page=page,
                        current_item=total_fetched,
                        operation=f"Fetching PubTator data: page {page}/{actual_pages} ({total_fetched} articles)",
                    )
                    logger.debug(f"🔍 Page {page}: Tracker updated successfully")

                # Check stopping conditions
                # 1. If we have a max_pages limit and reached it
                if self.max_pages is not None and page >= self.max_pages:
                    logger.info(f"Reached configured max pages limit ({self.max_pages})")
                    break

                # 2. If we've reached the last page available from API
                if page >= total_pages:
                    logger.info(f"Reached last available page ({page}/{total_pages})")
                    break

                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                page += 1

                # Progress indicator every 100 pages
                if page % 100 == 0:
                    logger.info(
                        f"📈 Progress: Fetched {total_fetched} articles from {page-1} pages..."
                    )

            except Exception as e:
                logger.error(f"❌ Error on page {page}: {type(e).__name__}: {e}")
                logger.exception("Full exception details:")

                # Add more context about the failure
                logger.debug(f"🔍 Page {page}: Failed after retry strategy exhausted")
                logger.debug(f"🔍 Page {page}: Total fetched so far: {total_fetched}")

                consecutive_failures += 1
                logger.info(
                    f"🔍 Page {page}: Consecutive failures: {consecutive_failures}/{max_consecutive_failures}"
                )

                if consecutive_failures >= max_consecutive_failures:
                    logger.warning(f"🛑 Stopping after {consecutive_failures} consecutive failures")
                    break

                # Skip to next page if we haven't hit the limit
                logger.info(f"🔍 Page {page}: Skipping to next page after error")
                page += 1
                continue

        logger.info(f"✅ PubTator3 search complete: {total_fetched} articles from {page-1} pages")
        return all_results

    async def process_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process PubTator3 annotations into structured gene information.
        Now works with complete data from search API including relevance scores.

        Args:
            raw_data: Raw data with PMIDs and annotations

        Returns:
            Dictionary mapping gene symbols to aggregated data
        """
        if not raw_data or "annotations" not in raw_data:
            return {}

        gene_data_map = {}
        total_pmids = len(raw_data.get("pmids", []))
        total_annotations = 0

        logger.info(f"🔄 Processing annotations from {total_pmids} publications...")

        for pmid, article_data in raw_data["annotations"].items():
            for gene in article_data.get("genes", []):
                total_annotations += 1

                # Get gene symbol from the new structure
                gene_symbol = gene.get("symbol", "")
                if not gene_symbol:
                    # Fallback to extracting from text
                    gene_symbol = self._normalize_gene_symbol(gene.get("text", ""))
                    if not gene_symbol:
                        continue

                # Initialize gene entry if new
                if gene_symbol not in gene_data_map:
                    gene_data_map[gene_symbol] = {
                        "pmids": set(),
                        "mentions": [],
                        "identifiers": set(),
                        "publication_count": 0,
                        "total_mentions": 0,
                        "evidence_score": 0,  # Sum of relevance scores
                    }

                # Add publication
                gene_data_map[gene_symbol]["pmids"].add(pmid)

                # Add gene ID if available
                gene_id = gene.get("identifier")
                if gene_id:
                    gene_data_map[gene_symbol]["identifiers"].add(gene_id)

                # Create mention record with article metadata
                mention_record = {
                    "pmid": pmid,
                    "title": article_data.get("title", ""),
                    "journal": article_data.get("journal", ""),
                    "date": article_data.get("date", ""),
                    "score": article_data.get("score", 0),  # Relevance score
                    "doi": article_data.get("doi", ""),
                    "text": gene.get("text", ""),
                }
                gene_data_map[gene_symbol]["mentions"].append(mention_record)

                # Add to evidence score
                gene_data_map[gene_symbol]["evidence_score"] += article_data.get("score", 0)

        # Convert sets to lists and calculate stats
        for _symbol, data in gene_data_map.items():
            data["pmids"] = list(data["pmids"])
            data["identifiers"] = list(data["identifiers"])
            data["publication_count"] = len(data["pmids"])
            data["total_mentions"] = len(data["mentions"])

            # Calculate average evidence score
            if data["publication_count"] > 0:
                data["evidence_score"] = data["evidence_score"] / data["publication_count"]

            # Sort mentions by relevance score (highest first)
            data["mentions"] = sorted(
                data["mentions"], key=lambda x: x.get("score", 0), reverse=True
            )

            # Keep top mentions for display
            data["top_mentions"] = data["mentions"][:5]  # Top 5 for display
            data["mentions"] = data["mentions"][:20]  # Keep top 20

            # Add metadata
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            data["search_query"] = raw_data.get("query", "")

        logger.info(
            f"🎯 PubTator processing complete: "
            f"{total_pmids} publications, {total_annotations} annotations, "
            f"{len(gene_data_map)} unique genes"
        )

        return gene_data_map

    def _normalize_gene_symbol(self, text: str) -> str | None:
        """
        Normalize gene symbol from PubTator text.

        Args:
            text: Raw gene text from annotation

        Returns:
            Normalized gene symbol or None
        """
        if not text:
            return None

        # Remove special characters and normalize
        symbol = text.strip().upper()

        # Remove common suffixes/prefixes
        for suffix in [" GENE", " PROTEIN", " MRNA"]:
            if symbol.endswith(suffix):
                symbol = symbol[: -len(suffix)]

        # Basic validation
        if len(symbol) < 2 or len(symbol) > 15:
            return None

        # Must contain at least one letter
        if not any(c.isalpha() for c in symbol):
            return None

        return symbol

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        """
        Check if a gene record is kidney-related.

        Always returns True as we pre-filter with kidney query.
        """
        return True

    def _get_source_detail(self, evidence_data: dict[str, Any]) -> str:
        """
        Generate source detail string for evidence.

        Args:
            evidence_data: Evidence data

        Returns:
            Source detail string
        """
        pub_count = evidence_data.get("publication_count", 0)
        mention_count = evidence_data.get("total_mentions", 0)

        return f"PubTator: {pub_count} publications, {mention_count} mentions"
