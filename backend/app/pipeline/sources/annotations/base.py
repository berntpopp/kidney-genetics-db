"""
Base annotation source class for gene annotations.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import ColumnElement
from sqlalchemy.orm import Session

from app.core.cache_service import get_cache_service
from app.core.logging import get_logger
from app.core.retry_utils import RetryableHTTPClient, RetryConfig
from app.models.gene import Gene
from app.models.gene_annotation import AnnotationHistory, AnnotationSource, GeneAnnotation

logger = get_logger(__name__)


class BaseAnnotationSource(ABC):
    """
    Abstract base class for gene annotation sources.

    Provides common functionality for fetching, storing, and managing
    gene annotations from various external sources.
    """

    # Source identification (must be overridden in subclasses)
    source_name: str | None = None
    display_name: str | None = None
    version: str | None = None

    # Cache configuration
    cache_ttl_days: int = 7
    cache_namespace: str = "annotations"

    # Batch processing
    batch_size: int = 50

    # Retry configuration (initialized in __init__)
    retry_config: RetryConfig | None = None
    http_client: RetryableHTTPClient | None = None

    # Rate limiting
    requests_per_second: float = 2.0  # Default 2 req/s

    def __init__(self, session: Session):
        """
        Initialize annotation source with retry capabilities.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.batch_mode = False  # Flag to disable cache invalidation during batch updates
        self._update_count = 0  # Track updates for rate-limited source record updates

        if not self.source_name:
            raise ValueError("source_name must be defined in subclass")

        # Load configuration from datasource_config if available
        from app.core.datasource_config import get_annotation_config

        config = get_annotation_config(self.source_name) or {}

        # Apply configuration with defaults
        if config:
            self.requests_per_second = config.get("requests_per_second", self.requests_per_second)
            self.cache_ttl_days = config.get("cache_ttl_days", self.cache_ttl_days)
            max_retries = config.get("max_retries", 5)
        else:
            max_retries = 5

        # The one retry loop for this source's HTTP calls (RetryableHTTPClient, #364)
        self.retry_config = RetryConfig(
            max_retries=max_retries,
            initial_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True,
            retry_on_status_codes=(429, 500, 502, 503, 504),
        )

        # Get or create source record
        self.source_record = self._get_or_create_source()
        # The label shows the configured schedule; next_update follows cache_ttl_days (#370)
        if config.get("update_frequency"):
            self.source_record.update_frequency = config["update_frequency"]

    def _get_or_create_source(self) -> AnnotationSource:
        """Get or create the annotation source record."""
        source: AnnotationSource | None = (
            self.session.query(AnnotationSource).filter_by(source_name=self.source_name).first()
        )

        if not source:
            source = AnnotationSource(
                source_name=self.source_name,
                display_name=self.display_name or self.source_name,
                version=self.version or "1.0",
                is_active=True,
                config=self.get_default_config(),
            )
            self.session.add(source)
            self.session.commit()
        elif self.version and source.version != self.version:
            logger.sync_info(
                f"Source version changed: {source.version} -> {self.version}",
                source=self.source_name,
            )
            source.version = self.version
            self.session.commit()

        return source

    def get_default_config(self) -> dict[str, Any]:
        """
        Get default configuration for this source.
        Can be overridden by subclasses.
        """
        return {"cache_ttl_days": self.cache_ttl_days, "batch_size": self.batch_size}

    @abstractmethod
    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch annotation for a single gene from the external source.

        Args:
            gene: Gene object to fetch annotations for

        Returns:
            Dictionary of annotation data or None if not found
        """
        pass

    @abstractmethod
    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Fetch annotations for multiple genes.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene_id to annotation data
        """
        pass

    async def get_http_client(self) -> RetryableHTTPClient:
        """
        Get or create a RetryableHTTPClient with proper configuration.

        Returns:
            Configured HTTP client with retry logic
        """
        if not self.http_client:
            base_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )

            self.http_client = RetryableHTTPClient(
                client=base_client, retry_config=self.retry_config
            )

        return self.http_client

    async def apply_rate_limit(self, url: str | None = None) -> None:
        """
        Apply rate limiting between requests.

        Args:
            url: Optional URL for per-domain rate limiting. If provided,
                uses the shared DomainRateLimiterRegistry. If not provided,
                falls back to simple sleep-based delay.
        """
        if url:
            from app.core.domain_rate_limiter import get_domain_rate_limiter_registry

            registry = get_domain_rate_limiter_registry()
            limiter = registry.get_for_url(url)
            async with limiter.acquire():
                return
        else:
            delay = 1.0 / self.requests_per_second
            await asyncio.sleep(delay)

    def store_annotation(
        self,
        gene: Gene,
        annotation_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        skip_cache_invalidation: bool = False,
    ) -> GeneAnnotation:
        """
        Store annotation in database and invalidate API cache.

        Args:
            gene: Gene object
            annotation_data: Annotation data to store
            metadata: Optional metadata about the annotation

        Returns:
            Created or updated GeneAnnotation object
        """
        # Check for existing annotation
        existing: GeneAnnotation | None = (
            self.session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source=self.source_name)
            .first()
        )

        annotation: GeneAnnotation
        # Track history if updating
        if existing:
            self._record_history(
                gene_id=gene.id,
                operation="update",
                old_data=existing.annotations,
                new_data=annotation_data,
            )

            if existing.version != self.version:
                existing.version = self.version
            existing.annotations = annotation_data
            existing.source_metadata = metadata
            existing.updated_at = datetime.now(timezone.utc)
            annotation = existing
        else:
            # Create new annotation
            now = datetime.now(timezone.utc)
            annotation = GeneAnnotation(
                gene_id=gene.id,
                source=self.source_name,
                version=self.version,
                annotations=annotation_data,
                source_metadata=metadata,
                created_at=now,
                updated_at=now,
            )
            self.session.add(annotation)

            self._record_history(gene_id=gene.id, operation="insert", new_data=annotation_data)

        # Commit immediately when not in batch mode (single gene updates)
        if not self.batch_mode:
            self.session.commit()
            # Update source record timestamp only occasionally to avoid excessive DB updates
            # This prevents performance issues when updating many genes
            self._update_count += 1

            # Update timestamp every 10 genes or on first update
            if self._update_count == 1 or self._update_count % 10 == 0:
                self.source_record.last_update = datetime.utcnow()
                self.source_record.next_update = datetime.utcnow() + timedelta(
                    days=self.cache_ttl_days
                )
                self.session.commit()

        # Invalidate API cache after successful database update
        # This ensures the API will fetch fresh data on next request
        # Skip during batch mode to avoid thousands of async operations
        if not self.batch_mode and not skip_cache_invalidation:
            self._invalidate_api_cache_sync(gene.id)

        return annotation

    def _invalidate_api_cache_sync(self, gene_id: int) -> None:
        """
        Synchronously invalidate API cache for a gene's annotations.
        This clears both the specific source cache and the 'all' cache
        used by the API endpoint.
        """
        # Skip individual cache invalidation during batch mode
        # We'll clear the entire cache at the end of the batch
        if self.batch_mode:
            return

        try:
            import asyncio

            # Detect async context using zero-cost asyncio check
            # instead of expensive inspect.stack() (~1ms per call)
            try:
                asyncio.get_running_loop()
                # We're in an async context with a running loop
                # Schedule as a task - fire and forget
                asyncio.create_task(self._invalidate_api_cache(gene_id))
                return
            except RuntimeError:
                # No running loop - fall through to sync handling
                pass

            # We're in a true sync context - use threading to avoid blocking
            import threading

            def run_async_in_thread() -> None:
                # Create a new event loop in this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    new_loop.run_until_complete(self._invalidate_api_cache(gene_id))
                finally:
                    new_loop.close()
                    asyncio.set_event_loop(None)

            # Run in a daemon thread so we don't block
            thread = threading.Thread(target=run_async_in_thread, daemon=True)
            thread.start()
            # Don't wait for completion - fire and forget

        except Exception as e:
            # Don't fail the update if cache invalidation fails
            # This is expected during batch operations
            logger.sync_debug(
                f"Cache invalidation skipped: {str(e)}", source=self.source_name, gene_id=gene_id
            )

    async def _invalidate_api_cache(self, gene_id: int) -> None:
        """
        Invalidate API cache for a gene's annotations (async version).
        This clears both the specific source cache and the 'all' cache
        used by the API endpoint.
        """
        try:
            cache_service = get_cache_service(self.session)

            # Invalidate the 'all' cache (used by API when no source specified)
            cache_key_all = f"{gene_id}:all"
            await cache_service.delete(cache_key_all, namespace="annotations")

            # Invalidate the specific source cache (source_name is validated in __init__)
            source_name_lower = self.source_name.lower() if self.source_name else ""
            cache_key_source = f"{gene_id}:{source_name_lower}"
            await cache_service.delete(cache_key_source, namespace="annotations")

            logger.sync_debug(
                f"Invalidated API cache for gene {gene_id}",
                source=self.source_name,
                keys=[cache_key_all, cache_key_source],
            )
        except Exception as e:
            # Don't fail the update if cache invalidation fails
            logger.sync_warning(
                f"Failed to invalidate cache for gene {gene_id}: {str(e)}", source=self.source_name
            )

    def _record_history(
        self,
        gene_id: int,
        operation: str,
        old_data: dict | None = None,
        new_data: dict | None = None,
    ) -> None:
        """Record annotation change in history."""
        history = AnnotationHistory(
            gene_id=gene_id,
            source=self.source_name,
            operation=operation,
            old_data=old_data,
            new_data=new_data,
            changed_by=f"{self.source_name}_updater",
            change_reason="Automated update",
        )
        self.session.add(history)

    def _release_transaction(self) -> None:
        """Commit before a network await so no transaction idles across it (#249).

        Loaded objects are kept (not expired), so reading them later does not reopen a
        transaction before the await.
        """
        expire_on_commit = self.session.expire_on_commit
        self.session.expire_on_commit = False
        try:
            self.session.commit()
        finally:
            self.session.expire_on_commit = expire_on_commit

    async def update_gene(self, gene: Gene) -> bool:
        """
        Update annotations for a single gene with proper retry and cache validation.

        Args:
            gene: Gene to update

        Returns:
            True if successful, False otherwise
        """
        try:
            cache_service = get_cache_service(self.session)
            cache_key = f"{gene.approved_symbol}:{gene.hgnc_id}"
            self._release_transaction()
            # source_name is validated non-None in __init__
            source_namespace = self.source_name.lower() if self.source_name else "unknown"

            # Check cache first
            cached_data = await cache_service.get(
                key=cache_key, namespace=source_namespace, default=None
            )

            # Validate cached data - don't use empty/null responses
            if cached_data and self._is_valid_annotation(cached_data):
                logger.sync_debug(  # Changed from info to debug
                    f"Using cached annotation for {gene.approved_symbol}", source=self.source_name
                )
                annotation_data = cached_data
                metadata = {"retrieved_at": datetime.utcnow().isoformat(), "from_cache": True}
            else:
                # Fetch from source with retry
                annotation_data = await self.fetch_annotation(gene)

                # Only cache valid responses
                if annotation_data and self._is_valid_annotation(annotation_data):
                    await cache_service.set(
                        key=cache_key,
                        value=annotation_data,
                        namespace=source_namespace,
                        ttl=self.cache_ttl_days * 86400,
                    )
                    metadata = {"retrieved_at": datetime.utcnow().isoformat(), "from_cache": False}
                else:
                    # Don't cache invalid responses
                    logger.sync_warning(  # Keep as warning for missing data
                        f"Invalid or missing annotation for {gene.approved_symbol}",
                        source=self.source_name,
                    )
                    return False

            if annotation_data:
                self.store_annotation(gene, annotation_data, metadata=metadata)
                return True

            return False

        except Exception as e:
            logger.sync_error(  # Already correct
                f"Error updating gene {gene.approved_symbol}: {str(e)}",
                source=self.source_name,
                gene_id=gene.id,
            )
            return False

    @classmethod
    def stale_annotation_filter(cls) -> ColumnElement[bool] | None:
        """SQL condition on GeneAnnotation that marks a stored payload as outdated.

        Routine runs re-annotate genes matching it; None (default) means never stale.
        """
        return None

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """
        Validate annotation data to ensure it's not empty or error response.
        Override in subclasses for source-specific validation.
        """
        if not annotation_data:
            return False

        # Check for common error indicators
        if annotation_data.get("error") or annotation_data.get("status") == "error":
            return False

        # Check for empty results
        if isinstance(annotation_data, dict):
            # Must have at least one non-metadata field
            meaningful_keys = [
                k for k in annotation_data.keys() if k not in ["source", "version", "timestamp"]
            ]
            return len(meaningful_keys) > 0

        return True

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about annotations from this source.

        Returns:
            Dictionary with statistics
        """
        total_count = self.session.query(GeneAnnotation).filter_by(source=self.source_name).count()

        latest = (
            self.session.query(GeneAnnotation)
            .filter_by(source=self.source_name)
            .order_by(GeneAnnotation.updated_at.desc())
            .first()
        )

        return {
            "source": self.source_name,
            "total_annotations": total_count,
            "last_updated": latest.updated_at if latest else None,
            "version": self.version,
            "is_active": self.source_record.is_active,
            "next_update": self.source_record.next_update,
        }
