"""
Unified PubTator data source implementation.

This module replaces the previous implementations (pubtator.py, pubtator_async.py,
pubtator_cache.py, pubtator_cached.py) with a single, async-first implementation.
"""

import asyncio
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
        self.rate_limit_delay = max(
            get_source_parameter("PubTator", "rate_limit_delay", 0.3), 0.5
        )  # Min 0.5s delay
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
        Search PubTator3 with intelligent duplicate detection.

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

        all_results = []
        page = 1
        total_pages = None
        consecutive_duplicate_pages = 0
        max_consecutive_failures = 3
        consecutive_failures = 0

        # Smart update limits
        smart_max_pages = 500
        duplicate_threshold = 0.9  # 90%
        consecutive_duplicate_limit = 3

        while True:
            # Safeguard 4: Resource monitoring and circuit breaker
            if page > 1 and page % 100 == 0:  # Check every 100 pages
                import psutil

                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 85:  # Stop if memory usage > 85%
                    logger.sync_warning(
                        "High memory usage detected, stopping update",
                        page=page,
                        memory_percent=memory_percent,
                    )
                    break
                logger.sync_info("Resource check", page=page, memory_percent=memory_percent)

            # Safeguard 5: Progress milestone logging for recovery
            if page % 250 == 0:  # Every 250 pages
                progress_pct = (page / total_pages * 100) if total_pages else 0
                logger.sync_info(
                    "Progress milestone",
                    page=page,
                    total_pages=total_pages,
                    progress_percent=f"{progress_pct:.1f}%",
                    articles_collected=len(all_results),
                )

            # Use PubTator3's native search endpoint
            search_url = f"{self.base_url}/search/"
            params = {
                "text": query,
                "filters": "{}",
                "page": page,
                "sort": self.sort_order,  # Always "score desc" for consistent ordering
            }

            # Log progress
            if mode == "smart":
                max_pages_display = smart_max_pages
            else:
                # Full mode: Use full_update max_pages from config (None = no limit)
                full_max_pages = get_source_parameter("PubTator", "full_update", {}).get(
                    "max_pages"
                )
                max_pages_display = full_max_pages or "ALL"
            logger.sync_info(
                f"PubTator3 search page (mode: {mode})",
                current_page=page,
                max_pages=max_pages_display,
                total_pages=total_pages if total_pages else "?",
            )

            try:
                logger.sync_info("Starting request to PubTator API", page=page, mode=mode)

                # SAFEGUARD SYSTEM: Multiple layers of protection against hangs
                logger.sync_debug("About to execute HTTP request", url=search_url, params=params)

                # Safeguard 1: Asyncio timeout wrapper (120s absolute maximum)
                try:
                    async with asyncio.timeout(120):  # 120s failsafe timeout
                        # Safeguard 2: Enhanced HTTP timeouts with connection limits
                        response = await self.retry_strategy.execute_async(
                            lambda url=search_url, p=params: self.http_client.get(
                                url,
                                params=p,
                                timeout=httpx.Timeout(
                                    connect=30.0,  # 30s connection timeout
                                    read=60.0,  # 60s read timeout
                                    write=30.0,  # 30s write timeout
                                    pool=30.0,  # 30s pool timeout
                                ),
                            )
                        )

                except asyncio.TimeoutError:
                    logger.sync_error("Request timed out after 120 seconds", page=page, mode=mode)
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.sync_error(
                            "Stopping after consecutive timeout failures",
                            failures=consecutive_failures,
                        )
                        break
                    await asyncio.sleep(self.rate_limit_delay * 2)  # Longer delay after timeout
                    page += 1
                    continue

                logger.sync_debug(
                    "HTTP request returned", page=page, status_code=response.status_code
                )
                logger.sync_info("Request completed successfully", page=page)
                consecutive_failures = 0

                if response.status_code != 200:
                    logger.sync_error(
                        "PubTator3 search failed", page=page, status_code=response.status_code
                    )
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.sync_error(
                            "Stopping after consecutive errors",
                            consecutive_failures=consecutive_failures,
                        )
                        break
                    continue

                try:
                    data = response.json()
                    logger.sync_debug("JSON parsed successfully", page=page, keys=list(data.keys()))
                except Exception as json_err:
                    logger.sync_error("Failed to parse JSON", page=page, error=str(json_err))
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        logger.sync_error(
                            "Stopping after consecutive parse errors",
                            consecutive_failures=consecutive_failures,
                        )
                        break
                    continue

                results = data.get("results", [])
                logger.sync_debug("Found results", page=page, result_count=len(results))

                # Get total pages from API response
                if total_pages is None:
                    total_pages = data.get("total_pages", 0)
                    total_available = data.get("count", 0)
                    logger.sync_info(
                        "Total available data",
                        total_articles=total_available,
                        total_pages=total_pages,
                    )

                    # Initialize tracker with actual limit we'll process
                    if tracker:
                        if mode == "smart":
                            actual_pages = min(smart_max_pages, total_pages)
                            actual_items = min(smart_max_pages * 10, total_available)
                        else:
                            # Full mode: Use full_update config
                            full_max_pages = get_source_parameter(
                                "PubTator", "full_update", {}
                            ).get("max_pages")
                            if full_max_pages is not None:
                                actual_pages = min(full_max_pages, total_pages)
                                actual_items = min(full_max_pages * 10, total_available)
                            else:
                                # No limit - process all pages
                                actual_pages = total_pages
                                actual_items = total_available
                        tracker.update(total_pages=actual_pages, total_items=actual_items)

                if not results:
                    logger.sync_info("No more results", page=page)
                    break

                # Smart mode: Database duplicate checking
                if mode == "smart":
                    page_pmids = {str(r.get("pmid")) for r in results if r.get("pmid")}
                    new_pmids = page_pmids - existing_pmids
                    duplicate_rate = 1 - (len(new_pmids) / len(page_pmids)) if page_pmids else 0

                    logger.sync_info(
                        "Database duplicate check",
                        page=page,
                        total_on_page=len(page_pmids),
                        already_in_db=len(page_pmids) - len(new_pmids),
                        new=len(new_pmids),
                        duplicate_rate=f"{duplicate_rate:.1%}",
                    )

                    # Stop if high duplicate rate
                    if duplicate_rate > duplicate_threshold:
                        consecutive_duplicate_pages += 1
                        if consecutive_duplicate_pages >= consecutive_duplicate_limit:
                            logger.sync_info(
                                "Stopping smart update: High database duplicate rate",
                                consecutive_pages=consecutive_duplicate_pages,
                                duplicate_rate=f"{duplicate_rate:.1%}",
                            )
                            break
                    else:
                        consecutive_duplicate_pages = 0

                    # Only add results with new PMIDs
                    new_results = [r for r in results if str(r.get("pmid")) in new_pmids]
                    all_results.extend(new_results)

                    logger.sync_info(
                        f"Smart mode: Added {len(new_results)} new results from page {page}"
                    )
                else:
                    # Full mode: Add everything
                    all_results.extend(results)
                    logger.sync_info(f"Full mode: Added {len(results)} results from page {page}")

                # Update progress
                if tracker:
                    total_fetched = len(all_results)
                    if mode == "smart":
                        actual_pages = min(smart_max_pages, total_pages)
                    else:
                        # Full mode: Use full_update max_pages from config (None = no limit)
                        full_max_pages = get_source_parameter("PubTator", "full_update", {}).get(
                            "max_pages"
                        )
                        actual_pages = (
                            min(full_max_pages, total_pages) if full_max_pages else total_pages
                        )

                    tracker.update(
                        current_page=page,
                        current_item=total_fetched,
                        operation=f"Fetching PubTator data ({mode} mode): page {page}/{actual_pages} ({total_fetched} articles)",
                    )

                    # Safeguard 3: Periodic database commit to prevent long transactions
                    if page % 50 == 0:  # Commit every 50 pages
                        try:
                            self.db_session.commit()
                            logger.sync_debug("Periodic database commit", page=page)
                        except Exception as commit_err:
                            logger.sync_warning(
                                "Periodic commit failed", page=page, error=str(commit_err)
                            )

                # Check stopping conditions
                if mode == "smart":
                    # Smart mode: Stop after reasonable number of pages
                    if page >= smart_max_pages:
                        logger.sync_info(
                            "Smart update page limit reached", max_pages=smart_max_pages
                        )
                        break
                else:
                    # Full mode: Get full_update max_pages from config (None = no limit)
                    full_max_pages = get_source_parameter("PubTator", "full_update", {}).get(
                        "max_pages"
                    )
                    if full_max_pages is not None and page >= full_max_pages:
                        logger.sync_info("Reached full update page limit", max_pages=full_max_pages)
                        break

                # Check if we've reached the last page available from API
                if page >= total_pages:
                    logger.sync_info(
                        "Reached last available page", current_page=page, total_pages=total_pages
                    )
                    break

                # Rate limiting
                logger.sync_debug("Rate limiting sleep", delay=self.rate_limit_delay)
                await asyncio.sleep(self.rate_limit_delay)
                page += 1
                logger.sync_debug("Moving to next page", next_page=page)

                # Progress indicator every 100 pages
                if page % 100 == 0:
                    logger.sync_info(
                        "Progress update", total_fetched=len(all_results), pages_completed=page - 1
                    )

            except Exception as e:
                logger.sync_error(
                    "Error on page", page=page, error_type=type(e).__name__, error=str(e)
                )
                consecutive_failures += 1

                if consecutive_failures >= max_consecutive_failures:
                    logger.sync_warning(
                        "Stopping after consecutive failures",
                        consecutive_failures=consecutive_failures,
                    )
                    break

                page += 1
                continue

        logger.sync_info(
            f"PubTator3 search complete ({mode} mode)",
            total_articles=len(all_results),
            pages_processed=page - 1,
            mode=mode,
        )
        return all_results

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
