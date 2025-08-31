"""
Unified PubTator data source implementation.

This module replaces the previous implementations (pubtator.py, pubtator_async.py,
pubtator_cache.py, pubtator_cached.py) with a single, async-first implementation.
"""

import asyncio
import gc
from datetime import datetime, timezone

# Import for type hint only
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.datasource_config import get_source_parameter
from app.core.logging import get_logger
from app.models.gene import GeneEvidence
from app.pipeline.sources.unified.base import UnifiedDataSource

if TYPE_CHECKING:
    from app.core.progress_tracker import ProgressTracker

logger = get_logger(__name__)


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
        # REMOVED: rate_limit_delay - now using CachedHttpClient's intelligent retry with exponential backoff
        # The HTTP client handles rate limiting properly with retry only on failures, not on every request
        # Sort order: "score desc" for relevance, "date desc" for recency
        self.sort_order = "score desc"  # Fixed value as per datasource_config

        # Gene annotation types to extract
        self.annotation_types = ["Gene", "GeneID"]

        max_pages_str = "ALL" if self.max_pages is None else str(self.max_pages)
        logger.sync_info(
            "PubTatorUnifiedSource initialized", max_pages=max_pages_str, sort_order=self.sort_order
        )

    def _get_default_ttl(self) -> int:
        """Get default TTL for PubTator data."""
        return get_source_parameter("PubTator", "cache_ttl", 604800)

    async def fetch_raw_data(
        self, tracker: "ProgressTracker" = None, mode: str = "smart"
    ) -> dict[str, Any]:
        """
        Fetch kidney disease-related publications directly from PubTator3.
        Uses PubTator3's native search API which returns annotations directly.

        Returns:
            Dictionary with PMIDs and gene annotations
        """
        logger.sync_info("PUBTATOR SOURCE: fetch_raw_data() METHOD CALLED")
        logger.sync_info("PUBTATOR SOURCE: kidney_query", kidney_query=self.kidney_query)

        # Search PubTator3 directly - returns complete results with annotations
        logger.sync_info("PUBTATOR SOURCE: Calling _search_pubtator3()")
        search_results = await self._search_pubtator3(self.kidney_query, tracker, mode)
        logger.sync_info(
            "PUBTATOR SOURCE: Search returned articles", article_count=len(search_results)
        )

        if not search_results:
            logger.sync_warning("No publications found for kidney disease query")
            return {}

        # Process search results into our annotation format
        annotations = self._process_search_results(search_results)
        pmids = list(annotations.keys())

        logger.sync_info("Processed articles with gene annotations", article_count=len(annotations))

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

    async def _search_pubtator3(
        self, query: str, tracker: "ProgressTracker" = None, mode: str = "smart"
    ) -> list[dict]:
        """
        Search PubTator3 with chunked processing to prevent memory issues.

        Args:
            query: Search query
            tracker: Progress tracker
            mode: Update mode - "smart" (incremental) or "full" (complete refresh)

        Returns:
            List of article results with annotations
        """

        # Handle full mode: Clear existing entries first
        if mode == "full":
            deleted = (
                self.db_session.query(GeneEvidence)
                .filter(GeneEvidence.source_name == "PubTator")
                .delete()
            )
            self.db_session.commit()
            logger.sync_info(f"Full update: Deleted {deleted} existing PubTator entries")
            existing_pmids = set()
        else:
            # Smart mode: Get existing PMIDs from database
            existing_pmids = await self._get_existing_pmids_from_db()
            logger.sync_info(
                f"Smart update: Found {len(existing_pmids)} existing PMIDs in database"
            )

        # Configuration
        config = self._get_search_config(mode)

        # State tracking
        state = {
            "results": [],  # Results to return
            "chunk": [],  # Current chunk for processing
            "processed_count": 0,
            "page": 1,
            "total_pages": None,
            "consecutive_duplicates": 0,
            "consecutive_failures": 0,
        }

        while True:
            try:
                # Check resource limits periodically
                if state["page"] % 100 == 0 and not self._check_resources():
                    logger.sync_warning("Resource limit reached, stopping")
                    break

                # Build request parameters
                params = self._build_request_params(query, state["page"])

                # Make API request
                response = await self._fetch_page(params, state["page"])
                if response is None:
                    state["consecutive_failures"] += 1
                    if state["consecutive_failures"] >= config["max_failures"]:
                        logger.sync_error("Too many failures, stopping")
                        break
                    state["page"] += 1
                    continue

                state["consecutive_failures"] = 0

                # Parse response
                data = response.json()
                results = data.get("results", [])

                # Initialize total pages
                if state["total_pages"] is None:
                    state["total_pages"] = data.get("total_pages", 0)
                    self._init_tracker(tracker, state["total_pages"], data.get("count", 0), config)

                if not results:
                    logger.sync_info("No more results", page=state["page"])
                    break

                # Add to current chunk
                state["chunk"].extend(results)
                state["processed_count"] += len(results)

                # Check for duplicates in smart mode
                if mode == "smart" and existing_pmids:
                    should_stop = self._check_duplicates(state, existing_pmids, config)
                    if should_stop:
                        break

                # Process chunk when it reaches threshold
                if len(state["chunk"]) >= config["chunk_size"]:
                    # Filter duplicates in smart mode
                    if mode == "smart" and existing_pmids:
                        filtered_chunk = [
                            a for a in state["chunk"]
                            if str(a.get("pmid", "")) not in existing_pmids
                        ]
                    else:
                        filtered_chunk = state["chunk"]

                    # Add to results (up to limit)
                    remaining_space = config["max_results"] - len(state["results"])
                    if remaining_space > 0:
                        state["results"].extend(filtered_chunk[:remaining_space])

                    # Clear chunk and collect garbage
                    state["chunk"] = []
                    gc.collect()

                    logger.sync_info(
                        f"Processed chunk: {len(filtered_chunk)} articles, total results: {len(state['results'])}"
                    )

                    # Stop if we have enough results
                    if len(state["results"]) >= config["max_results"]:
                        logger.sync_info(f"Reached result limit of {config['max_results']}")
                        break

                # Update progress
                self._update_progress(tracker, state, mode, config)

                # No periodic commits - let the framework handle transactions

                # Check stopping conditions
                if self._should_stop(state, config):
                    break

                # Progress tracking (rate limiting handled by CachedHttpClient's retry logic)
                state["page"] += 1

                if state["page"] % 50 == 0:
                    self._log_progress(state)

            except Exception as e:
                logger.sync_error(f"Error on page {state['page']}: {str(e)}")
                state["consecutive_failures"] += 1
                if state["consecutive_failures"] >= config["max_failures"]:
                    break
                state["page"] += 1
                continue

        # Process remaining chunk
        if state["chunk"]:
            if mode == "smart" and existing_pmids:
                filtered_chunk = [
                    a for a in state["chunk"]
                    if str(a.get("pmid", "")) not in existing_pmids
                ]
            else:
                filtered_chunk = state["chunk"]

            remaining_space = config["max_results"] - len(state["results"])
            if remaining_space > 0:
                state["results"].extend(filtered_chunk[:remaining_space])

        logger.sync_info(
            f"Search complete: {state['processed_count']} processed, {len(state['results'])} returned"
        )

        return state["results"]

    async def _get_existing_pmids_from_db(self) -> set[str]:
        """
        Get all PMIDs currently in database for PubTator source.

        Returns:
            Set of existing PMIDs
        """
        logger.sync_info("Loading existing PMIDs from database")

        # Query gene_evidence table for PubTator entries
        staging_records = (
            self.db_session.query(GeneEvidence).filter(GeneEvidence.source_name == "PubTator").all()
        )

        existing_pmids = set()
        for record in staging_records:
            if record.evidence_data and "pmids" in record.evidence_data:
                pmids = record.evidence_data["pmids"]
                if isinstance(pmids, list):
                    existing_pmids.update(str(pmid) for pmid in pmids)

        logger.sync_info("Loaded existing PMIDs from database", count=len(existing_pmids))

        return existing_pmids

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

        logger.sync_info("Processing annotations", publication_count=total_pmids)

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

        logger.sync_info(
            "PubTator processing complete",
            publications=total_pmids,
            annotations=total_annotations,
            unique_genes=len(gene_data_map),
        )

        return gene_data_map

    def _get_search_config(self, mode: str) -> dict:
        """Get configuration for search based on mode."""
        base_config = {
            "chunk_size": 500,
            "request_timeout": 30,
            "max_failures": 3,
            "duplicate_threshold": 0.9,
            "duplicate_limit": 3,
        }

        if mode == "smart":
            base_config["max_pages"] = 500
            base_config["max_results"] = 5000  # Limit results in smart mode
        else:
            # Full mode: no limits on pages or results
            full_max = get_source_parameter("PubTator", "full_update", {}).get("max_pages")
            base_config["max_pages"] = full_max
            # Set max_results very high for full mode (effectively unlimited)
            base_config["max_results"] = 100000  # Support up to 100k articles

        return base_config

    def _build_request_params(self, query: str, page: int) -> dict:
        """Build request parameters."""
        return {
            "text": query,
            "filters": "{}",
            "page": page,
            "sort": self.sort_order,
        }

    async def _fetch_page(self, params: dict, page: int) -> httpx.Response | None:
        """Fetch a single page with timeout protection using cached HTTP client."""
        search_url = f"{self.base_url}/search/"

        try:
            async with asyncio.timeout(30):  # 30s timeout
                # Use the cached HTTP client instead of raw httpx
                response = await self.http_client.get(
                    search_url,
                    params=params,
                    timeout=30  # CachedHttpClient takes timeout in seconds
                )

            if response.status_code != 200:
                logger.sync_error(f"Bad status on page {page}: {response.status_code}")
                return None

            return response

        except asyncio.TimeoutError:
            logger.sync_error(f"Timeout on page {page}")
            return None
        except Exception as e:
            logger.sync_error(f"Request error on page {page}: {str(e)}")
            return None

    def _check_resources(self) -> bool:
        """Check if system resources are adequate."""
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 85:
                logger.sync_warning(f"High memory usage: {memory_percent}%")
                return False
            return True
        except ImportError:
            return True  # Continue if psutil not available

    def _check_duplicates(self, state: dict, existing_pmids: set, config: dict) -> bool:
        """Check for duplicate rate and return True if should stop."""
        recent = state["chunk"][-100:] if len(state["chunk"]) > 100 else state["chunk"]
        recent_pmids = {str(a.get("pmid", "")) for a in recent}
        duplicate_rate = len(recent_pmids & existing_pmids) / len(recent_pmids) if recent_pmids else 0

        if duplicate_rate > config["duplicate_threshold"]:
            state["consecutive_duplicates"] += 1
            if state["consecutive_duplicates"] >= config["duplicate_limit"]:
                logger.sync_info(f"High duplicate rate: {duplicate_rate:.1%}")
                return True
        else:
            state["consecutive_duplicates"] = 0
        return False


    def _init_tracker(self, tracker, total_pages: int, total_items: int, config: dict):
        """Initialize progress tracker."""
        if not tracker:
            return

        max_pages = config.get("max_pages")
        if max_pages:
            actual_pages = min(max_pages, total_pages)
            actual_items = min(max_pages * 10, total_items)
        else:
            actual_pages = total_pages
            actual_items = total_items

        tracker.update(total_pages=actual_pages, total_items=actual_items)

    def _update_progress(self, tracker, state: dict, mode: str, config: dict):
        """Update progress tracker."""
        if not tracker:
            return

        max_pages = config.get("max_pages")
        total_pages = state["total_pages"] or 1

        if max_pages:
            actual_pages = min(max_pages, total_pages)
        else:
            actual_pages = total_pages

        tracker.update(
            current_page=state["page"],
            current_item=state["processed_count"],
            operation=f"PubTator ({mode}): page {state['page']}/{actual_pages} ({state['processed_count']} processed, {len(state['results'])} saved)"
        )

    def _should_stop(self, state: dict, config: dict) -> bool:
        """Check if should stop processing."""
        # Check page limits
        max_pages = config.get("max_pages")
        if max_pages and state["page"] >= max_pages:
            logger.sync_info(f"Reached page limit: {max_pages}")
            return True

        # Check if reached last page
        if state["total_pages"] and state["page"] >= state["total_pages"]:
            logger.sync_info(f"Reached last page: {state['total_pages']}")
            return True

        return False

    def _log_progress(self, state: dict):
        """Log progress information."""
        logger.sync_info(
            f"Progress: page {state['page']}/{state['total_pages'] or '?'}, "
            f"processed: {state['processed_count']}, "
            f"saved: {len(state['results'])}"
        )

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
