"""
Unified PubTator data source implementation with streaming architecture.

This module implements stream-processing for unlimited results with constant memory usage,
proper evidence merging to prevent data loss, and checkpoint-based resume capability.
"""

import asyncio
import hashlib
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.datasource_config import get_source_parameter
from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene, GeneEvidence
from app.models.progress import DataSourceProgress
from app.pipeline.sources.unified.base import UnifiedDataSource
from app.pipeline.sources.unified.filtering_utils import (
    apply_database_filter,
    validate_threshold_config,
)

if TYPE_CHECKING:
    from app.core.progress_tracker import ProgressTracker

logger = get_logger(__name__)


class PubTatorUnifiedSource(UnifiedDataSource):
    """
    Unified PubTator client with streaming architecture.

    Key improvements:
    - Stream processing (constant memory usage)
    - Proper evidence merging (no data loss)
    - Checkpoint-based resume capability
    - Uses existing infrastructure (CachedHttpClient, retry logic)
    - Minimum publication filtering for quality control

    Publication Filtering:
    - Genes must have >= min_publications (default: 3) to be included
    - Filters out low-confidence genes with insufficient evidence
    - Reduces noise from single-publication mentions
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
        """Initialize PubTator client with streaming capabilities."""
        super().__init__(cache_service, http_client, db_session, **kwargs)

        # Configuration from datasource config
        self.base_url = get_source_parameter(
            "PubTator", "api_url", "https://www.ncbi.nlm.nih.gov/research/pubtator-api"
        )
        self.kidney_query = get_source_parameter(
            "PubTator",
            "search_query",
            '("kidney disease" OR "renal disease") AND (gene OR syndrome) AND (variant OR mutation)',
        )
        self.max_pages = get_source_parameter("PubTator", "max_pages", None)  # None = unlimited

        # Load filtering configuration with validation
        raw_threshold = get_source_parameter("PubTator", "min_publications", 3)
        self.min_publications = validate_threshold_config(
            raw_threshold, "publications", self.source_name
        )
        self.filtering_enabled = get_source_parameter(
            "PubTator", "min_publications_enabled", True
        )
        self.filter_after_complete = get_source_parameter(
            "PubTator", "filter_after_complete", True
        )

        self.sort_order = "score desc"
        self.chunk_size = 1000  # Optimal for PostgreSQL bulk operations
        self.transaction_size = 5000  # Commit every 5000 records

        logger.sync_info(
            f"{self.source_name} initialized with filtering",
            max_pages="ALL" if self.max_pages is None else str(self.max_pages),
            min_publications=self.min_publications,
            filtering_enabled=self.filtering_enabled,
            filter_after_complete=self.filter_after_complete,
            chunk_size=self.chunk_size,
        )

    def _get_default_ttl(self) -> int:
        """Get default TTL for PubTator data."""
        return get_source_parameter("PubTator", "cache_ttl", 604800)  # 7 days

    async def fetch_raw_data(
        self, tracker: "ProgressTracker" = None, mode: str = "smart"
    ) -> dict[str, Any]:
        """
        Stream-process PubTator data directly to database.

        Returns the stats for compatibility with the base class.
        """
        logger.sync_info("Starting PubTator stream processing", mode=mode)

        # Stream-process all data
        stats = await self._stream_process_pubtator(self.kidney_query, tracker, mode)

        # Return stats wrapped for compatibility
        # The base class expects genes_found to be populated
        return {
            "stats": stats,
            "genes_found": stats.get("genes_processed", 0),
            "mode": mode,
            "processed_articles": stats.get("processed_articles", 0),
            "processed_genes": stats.get("genes_processed", 0),
            "fetch_date": datetime.now(timezone.utc).isoformat(),
        }

    async def process_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        No processing needed - data already processed during streaming.
        This method just returns empty dict as data is already in database.
        """
        return {}  # Already processed during fetch

    async def update_data(
        self, db: Session, tracker: "ProgressTracker", mode: str = "smart"
    ) -> dict[str, Any]:
        """
        Override base class to handle PubTator's streaming architecture.

        PubTator doesn't follow the fetch->process->store pattern.
        Instead, it streams and processes data directly to the database.
        """
        stats = self._initialize_stats()

        try:
            tracker.start(f"Starting {self.source_name} update")
            logger.sync_info("Starting data update", source_name=self.source_name)

            # Stream and process data directly
            tracker.update(operation="Streaming and processing PubTator data")
            stream_stats = await self._stream_process_pubtator(self.kidney_query, tracker, mode)

            # Merge stats
            stats.update(stream_stats)
            stats["data_fetched"] = True
            stats["genes_found"] = stream_stats.get("processed_genes", 0)
            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            stats["duration"] = (
                datetime.fromisoformat(stats["completed_at"])
                - datetime.fromisoformat(stats["started_at"])
            ).total_seconds()

            # Get the actual total counts from the database
            from sqlalchemy import text

            result = db.execute(
                text("""
                    SELECT
                        COUNT(DISTINCT gene_id) as total_genes,
                        COUNT(*) as total_evidence
                    FROM gene_evidence
                    WHERE source_name = :source_name
                """),
                {"source_name": self.source_name},
            ).fetchone()

            total_genes = result[0] if result else 0
            total_evidence = result[1] if result else 0

            logger.sync_info(
                "Data update completed",
                source_name=self.source_name,
                total_genes=total_genes,
                total_evidence=total_evidence,
                genes_created=stats.get("genes_created", 0),
                evidence_created=stats.get("evidence_created", 0),
            )

            tracker.complete(
                f"{self.source_name}: {total_genes} genes, {total_evidence} evidence "
                f"(+{stats.get('genes_created', 0)} new genes, +{stats.get('evidence_created', 0)} new evidence)"
            )

            return stats

        except Exception as e:
            logger.sync_error("Data update failed", source_name=self.source_name, error=str(e))
            tracker.error(str(e))
            stats["error"] = str(e)
            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            raise

    @retry_with_backoff(config=RetryConfig(
        max_retries=5,
        initial_delay=1.0,
        max_delay=60.0,
        retry_on_status_codes=(429, 500, 502, 503, 504),
        # Add retry for connection errors
        retry_on_exceptions=(
            httpx.HTTPStatusError,
            httpx.RequestError,
            httpx.TimeoutException,
            httpx.RemoteProtocolError,  # This catches "Server disconnected" errors
            asyncio.TimeoutError,
            ConnectionError,
            TimeoutError
        )
    ))
    async def _fetch_page(self, page: int, query: str) -> dict | None:
        """
        Fetch a single page using CachedHttpClient.

        The client automatically handles:
        - HTTP caching (Hishel)
        - Database fallback caching
        - Circuit breakers
        - Timeout handling
        """
        params = {
            "text": query,
            "page": page,
            "sort": self.sort_order,
            "filters": "{}"
        }

        # Don't catch exceptions here - let retry_with_backoff handle them!
        # CachedHttpClient handles all caching automatically!
        response = await self.http_client.get(
            f"{self.base_url}/search/",
            params=params,
            timeout=30  # CachedHttpClient respects this
        )

        if response.status_code != 200:
            logger.sync_error(f"Bad status on page {page}: {response.status_code}")
            # For non-retryable status codes, return None
            if response.status_code not in (429, 500, 502, 503, 504):
                return None
            # For retryable status codes, raise an exception to trigger retry
            raise Exception(f"HTTP {response.status_code} error on page {page}")

        return response.json()

    async def _stream_process_pubtator(
        self, query: str, tracker: "ProgressTracker", mode: str
    ) -> dict[str, Any]:
        """
        Main streaming processor - fetches, processes, and stores data in chunks.

        Key improvements:
        1. No memory accumulation
        2. Checkpoint-based resume
        3. Bulk database operations
        4. Proper error handling
        """
        # Load checkpoint for resume
        checkpoint = await self._load_checkpoint()
        start_page = checkpoint.get("last_page", 0) + 1
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]

        # Verify same query on resume
        if checkpoint.get("query_hash") and checkpoint.get("query_hash") != query_hash:
            logger.sync_warning("Query changed, starting from beginning")
            start_page = 1

        # Handle mode change
        if checkpoint.get("mode") != mode:
            logger.sync_info(f"Mode changed from {checkpoint.get('mode')} to {mode}")
            if mode == "full":
                # Full mode: clear existing entries
                await self._clear_existing_entries()
            start_page = 1

        # Initialize streaming state
        article_buffer = []
        gene_data_buffer = {}
        stats = {
            "processed_articles": 0,
            "processed_genes": 0,
            "current_page": start_page - 1,
            "total_pages": None,
            "genes_processed": 0,
            "genes_created": 0,
            "genes_updated": 0,
            "evidence_created": 0,
            "evidence_updated": 0,
            "errors": 0,
        }

        # Get existing PMIDs for smart mode
        existing_pmids = set()
        if mode == "smart":
            existing_pmids = await self._get_existing_pmids_from_db()
            logger.sync_info(f"Smart mode: Found {len(existing_pmids)} existing PMIDs")

        # Streaming loop
        page = start_page
        consecutive_duplicates = 0

        while True:
            try:
                # Check memory usage
                if not self._check_resources():
                    logger.sync_warning("Resource limit reached, saving progress")
                    break

                # Fetch page (with automatic caching via CachedHttpClient)
                logger.sync_debug(f"Fetching page {page}")

                try:
                    response = await self._fetch_page(page, query)
                except Exception as e:
                    # All retries exhausted, log and continue with next page
                    logger.sync_error(f"Failed to fetch page {page} after retries: {str(e)}")
                    # Save checkpoint and try next page
                    await self._save_checkpoint(page - 1, mode, query_hash)
                    page += 1
                    continue

                if not response:
                    logger.sync_warning(f"No response for page {page}")
                    break

                results = response.get("results", [])
                if not results:
                    logger.sync_info(f"No more results at page {page}")
                    break

                # Update total pages on first response
                if stats["total_pages"] is None:
                    stats["total_pages"] = response.get("total_pages", 0)
                    if tracker:
                        tracker.update(
                            total_pages=stats["total_pages"],
                            total_items=response.get("count", 0)
                        )

                # Process articles in this page
                new_articles = 0
                for article in results:
                    pmid = str(article.get("pmid", ""))

                    # Skip if already exists (smart mode)
                    if mode == "smart" and pmid in existing_pmids:
                        consecutive_duplicates += 1
                        continue

                    consecutive_duplicates = 0
                    new_articles += 1

                    # Add to buffer
                    article_buffer.append(article)

                    # Extract and accumulate gene data
                    self._accumulate_gene_data(article, gene_data_buffer)

                # Check for high duplicate rate in smart mode
                if mode == "smart" and consecutive_duplicates > 100:
                    logger.sync_info("Smart mode: High duplicate rate, stopping")
                    break

                # Process buffer when it reaches chunk size
                if len(article_buffer) >= self.chunk_size:
                    await self._flush_buffers(article_buffer, gene_data_buffer, stats, tracker)
                    article_buffer.clear()
                    gene_data_buffer.clear()

                    # Save checkpoint
                    await self._save_checkpoint(page, mode, query_hash)

                    # Commit transaction periodically
                    if stats["processed_articles"] % self.transaction_size == 0:
                        self.db_session.commit()
                        logger.sync_info(f"Transaction committed at {stats['processed_articles']} articles")

                # Update progress
                stats["current_page"] = page
                if tracker:
                    tracker.update(
                        current_page=page,
                        current_item=stats["processed_articles"],
                        operation=f"Processing page {page}/{stats['total_pages'] or '?'}"
                    )

                # Check stopping conditions
                if self.max_pages and page >= self.max_pages:
                    logger.sync_info(f"Reached max pages limit: {self.max_pages}")
                    break

                page += 1

            except Exception as e:
                logger.sync_error(f"Error on page {page}: {str(e)}")
                # Save checkpoint on error
                await self._save_checkpoint(page - 1, mode, query_hash)
                raise

        # Flush remaining buffers
        if article_buffer or gene_data_buffer:
            await self._flush_buffers(article_buffer, gene_data_buffer, stats, tracker)
            await self._save_checkpoint(stats["current_page"], mode, query_hash)

        # Final commit before filtering
        self.db_session.commit()

        # Apply final filtering if enabled
        if self.filtering_enabled and self.filter_after_complete:
            logger.sync_info(
                "Applying final filter to complete PubTator dataset",
                min_publications=self.min_publications
            )

            try:
                # Apply filter on complete database
                filter_stats = apply_database_filter(
                    db=self.db_session,
                    source_name=self.source_name,
                    count_field="publication_count",
                    min_threshold=self.min_publications,
                    entity_name="publications",
                    enabled=self.filtering_enabled
                )

                # Commit the deletions
                self.db_session.commit()

                # Add filter stats to overall stats
                stats["genes_filtered"] = filter_stats.filtered_count
                stats["genes_kept"] = filter_stats.total_after
                stats["filter_rate"] = filter_stats.filter_rate

                # Log filter statistics (metadata storage removed - method doesn't exist)
                logger.sync_info(
                    "PubTator filter statistics",
                    filtered_count=filter_stats.filtered_count,
                    filter_rate=f"{filter_stats.filter_rate:.1f}%",
                    min_publications=self.min_publications
                )

            except Exception as e:
                self.db_session.rollback()
                logger.sync_error(
                    "Failed to apply final filter",
                    source=self.source_name,
                    error=str(e)
                )
                raise
        else:
            # No filtering applied, set stats to reflect all genes kept
            stats["genes_filtered"] = 0
            stats["genes_kept"] = stats["processed_genes"]
            stats["filter_rate"] = 0

        logger.sync_info(
            "PubTator processing complete",
            processed_articles=stats["processed_articles"],
            total_genes_found=stats["processed_genes"],
            genes_kept=stats.get("genes_kept", stats["processed_genes"]),
            genes_filtered=stats.get("genes_filtered", 0),
            filter_rate=f"{stats.get('filter_rate', 0):.1f}%",
            min_publications=self.min_publications if self.filtering_enabled else "disabled",
            last_page=stats["current_page"]
        )

        return stats

    def _accumulate_gene_data(self, article: dict, gene_buffer: dict):
        """Accumulate gene data from article into buffer."""
        genes = self._extract_genes_from_highlight(article.get("text_hl"))

        for gene in genes:
            gene_symbol = gene.get("symbol", "")
            if not gene_symbol:
                continue

            if gene_symbol not in gene_buffer:
                gene_buffer[gene_symbol] = {
                    "pmids": set(),
                    "mentions": [],
                    "identifiers": set(),
                    "publication_count": 0,
                    "total_mentions": 0,
                    "evidence_score": 0,
                }

            # Add data
            pmid = str(article.get("pmid", ""))
            gene_buffer[gene_symbol]["pmids"].add(pmid)
            gene_buffer[gene_symbol]["identifiers"].add(gene.get("identifier", ""))
            gene_buffer[gene_symbol]["mentions"].append({
                "pmid": pmid,
                "title": article.get("title", ""),
                "journal": article.get("journal", ""),
                "date": article.get("date", ""),
                "score": article.get("score", 0),
                "text": gene.get("text", ""),
            })
            gene_buffer[gene_symbol]["evidence_score"] += article.get("score", 0)

    async def _flush_buffers(
        self,
        article_buffer: list,
        gene_buffer: dict,
        stats: dict,
        tracker: "ProgressTracker" = None
    ):
        """
        Flush buffers to database with MERGE logic to prevent data loss.

        CRITICAL: This method merges with existing evidence, not replace it!
        Otherwise we lose all PMIDs from previous chunks.
        """
        if not gene_buffer:
            return

        # Process each gene with the parent class method
        # which handles normalization and gene creation
        processed_genes = {}

        for gene_symbol, new_data in gene_buffer.items():
            # Convert sets to lists for the new data
            processed_data = new_data.copy()
            processed_data["pmids"] = list(new_data["pmids"])
            processed_data["identifiers"] = list(new_data["identifiers"])
            processed_data["publication_count"] = len(processed_data["pmids"])
            processed_data["total_mentions"] = len(processed_data["mentions"])

            # NO FILTERING HERE - moved to end of processing for chunk boundary safety
            # Filtering will be applied after all chunks are processed

            # Calculate average score
            if processed_data["publication_count"] > 0:
                processed_data["evidence_score"] = processed_data.get("evidence_score", 0) / processed_data["publication_count"]

            # Keep only top mentions
            processed_data["mentions"] = sorted(
                processed_data["mentions"],
                key=lambda x: x.get("score", 0),
                reverse=True
            )[:20]

            processed_genes[gene_symbol] = processed_data

        # Use parent class method to store genes
        # We'll override _create_or_update_evidence to handle merging
        await self._store_genes_in_database(
            self.db_session,
            processed_genes,
            stats,
            tracker  # Pass the tracker
        )

        # Update stats
        stats["processed_articles"] += len(article_buffer)
        stats["processed_genes"] = stats.get("processed_genes", 0) + len(gene_buffer)

        logger.sync_info(
            f"Flushed buffers: {len(article_buffer)} articles, "
            f"{len(processed_genes)} genes processed (filtering will be applied after all chunks)"
        )

    async def _create_or_update_evidence(
        self, db: Session, gene: Gene, evidence_data: dict[str, Any], stats: dict[str, Any]
    ) -> None:
        """
        Override parent method to MERGE evidence instead of replacing.

        CRITICAL: This prevents data loss when processing in chunks!
        """
        try:
            # Check if evidence already exists
            existing = (
                db.query(GeneEvidence)
                .filter(
                    GeneEvidence.gene_id == gene.id,
                    GeneEvidence.source_name == self.source_name,
                )
                .first()
            )

            if existing:
                # MERGE with existing data - this is the critical part!
                if existing.evidence_data:
                    merged_data = self._merge_evidence_data(
                        existing.evidence_data,
                        evidence_data
                    )
                else:
                    merged_data = evidence_data

                # Update existing evidence with merged data
                existing.source_detail = self._get_source_detail(merged_data)
                existing.evidence_data = merged_data
                existing.evidence_date = datetime.now(timezone.utc).date()
                db.add(existing)
                stats["evidence_updated"] += 1

                logger.sync_debug(
                    "Updated evidence for gene",
                    gene_symbol=gene.approved_symbol,
                    source_name=self.source_name,
                )
            else:
                # Call parent's implementation for new evidence
                await super()._create_or_update_evidence(db, gene, evidence_data, stats)

        except Exception as e:
            logger.sync_error(
                "Error creating/updating evidence for gene",
                gene_symbol=gene.approved_symbol,
                error=str(e),
            )
            stats["errors"] += 1

    def _merge_evidence_data(self, existing_data: dict, new_data: dict) -> dict:
        """
        Merge new PubTator evidence with existing evidence.

        CRITICAL: This prevents data loss when processing in chunks!
        - Merges PMIDs (union)
        - Combines mentions (deduped by PMID)
        - Recalculates scores and counts
        - Preserves top mentions by score
        """
        merged = existing_data.copy() if existing_data else {}

        # Merge PMIDs (union of sets to avoid duplicates)
        existing_pmids = set(merged.get("pmids", []))
        new_pmids = set(new_data.get("pmids", []))
        merged["pmids"] = list(existing_pmids | new_pmids)

        # Merge identifiers
        existing_ids = set(merged.get("identifiers", []))
        new_ids = set(new_data.get("identifiers", []))
        merged["identifiers"] = list(existing_ids | new_ids)

        # Merge mentions (deduplicate by PMID, keep highest score)
        mentions_by_pmid = {}

        # Add existing mentions
        for mention in merged.get("mentions", []):
            pmid = mention.get("pmid")
            if pmid:
                mentions_by_pmid[pmid] = mention

        # Add/update with new mentions (overwrites if same PMID with better data)
        for mention in new_data.get("mentions", []):
            pmid = mention.get("pmid")
            if pmid:
                # Keep the mention with higher score if duplicate
                if pmid in mentions_by_pmid:
                    if mention.get("score", 0) > mentions_by_pmid[pmid].get("score", 0):
                        mentions_by_pmid[pmid] = mention
                else:
                    mentions_by_pmid[pmid] = mention

        # Sort mentions by score and keep top 20 for display
        all_mentions = sorted(
            mentions_by_pmid.values(),
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        merged["mentions"] = all_mentions[:20]  # Keep top 20 for UI
        merged["top_mentions"] = all_mentions[:5]  # Keep top 5 for quick display

        # Update counts
        merged["publication_count"] = len(merged["pmids"])
        merged["total_mentions"] = len(mentions_by_pmid)

        # Recalculate average evidence score
        total_score = sum(m.get("score", 0) for m in mentions_by_pmid.values())
        merged["evidence_score"] = total_score / len(mentions_by_pmid) if mentions_by_pmid else 0

        # Add metadata
        merged["last_updated"] = datetime.now(timezone.utc).isoformat()
        merged["search_query"] = new_data.get("search_query", merged.get("search_query", ""))

        logger.sync_debug(
            f"Merged evidence: {len(existing_pmids)} existing + {len(new_pmids)} new = "
            f"{len(merged['pmids'])} total PMIDs"
        )

        return merged

    async def _load_checkpoint(self) -> dict:
        """Load checkpoint from DataSourceProgress table."""
        progress = self.db_session.query(DataSourceProgress).filter_by(
            source_name="PubTator"
        ).first()

        if progress and progress.progress_metadata:
            checkpoint = progress.progress_metadata
            logger.sync_info(
                "Loaded checkpoint",
                last_page=checkpoint.get("last_page"),
                mode=checkpoint.get("mode")
            )
            return checkpoint

        return {}

    async def _save_checkpoint(self, page: int, mode: str, query_hash: str):
        """Save checkpoint to DataSourceProgress table."""
        progress = self.db_session.query(DataSourceProgress).filter_by(
            source_name="PubTator"
        ).first()

        if not progress:
            progress = DataSourceProgress(source_name="PubTator")
            self.db_session.add(progress)

        # Keep it simple - just essentials
        progress.progress_metadata = {
            "last_page": page,
            "mode": mode,
            "query_hash": query_hash,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        progress.current_page = page

        self.db_session.commit()
        logger.sync_debug(f"Checkpoint saved at page {page}")

    async def _clear_existing_entries(self):
        """Clear existing PubTator entries for full mode."""
        deleted = (
            self.db_session.query(GeneEvidence)
            .filter(GeneEvidence.source_name == "PubTator")
            .delete()
        )
        self.db_session.commit()
        logger.sync_info(f"Cleared {deleted} existing PubTator entries")

    async def _get_existing_pmids_from_db(self) -> set[str]:
        """Get existing PMIDs for smart mode duplicate detection."""
        records = (
            self.db_session.query(GeneEvidence)
            .filter(GeneEvidence.source_name == "PubTator")
            .all()
        )

        existing_pmids = set()
        for record in records:
            if record.evidence_data and "pmids" in record.evidence_data:
                pmids = record.evidence_data["pmids"]
                if isinstance(pmids, list):
                    existing_pmids.update(str(pmid) for pmid in pmids)

        return existing_pmids

    def _extract_genes_from_highlight(self, text_hl: str | None) -> list[dict]:
        """Extract gene annotations from PubTator3's highlighted text."""

        if not text_hl:
            return []

        genes = []
        seen = set()

        # Pattern: @GENE_symbol @GENE_id @@@display@@@
        pattern = r"@GENE_(\w+)\s+@GENE_(\d+)\s+@@@([^@]+)@@@"

        for match in re.finditer(pattern, text_hl):
            symbol = match.group(1)
            gene_id = match.group(2)
            display = match.group(3)

            key = f"{symbol}:{gene_id}"
            if key not in seen:
                seen.add(key)
                genes.append({
                    "text": display,
                    "identifier": gene_id,
                    "type": "Gene",
                    "symbol": symbol,
                })

        return genes

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

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        """Always True as we pre-filter with kidney query."""
        return True

    def _get_source_detail(self, evidence_data: dict[str, Any]) -> str:
        """Generate source detail string for evidence."""
        pub_count = evidence_data.get("publication_count", 0)
        mention_count = evidence_data.get("total_mentions", 0)
        return f"PubTator: {pub_count} publications, {mention_count} mentions"
