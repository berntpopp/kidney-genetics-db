"""
Base annotation source class for gene annotations.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.cache_service import get_cache_service
from app.core.logging import get_logger
from app.models.gene import Gene
from app.models.gene_annotation import AnnotationHistory, AnnotationSource, GeneAnnotation

logger = get_logger(__name__)


class BaseAnnotationSource(ABC):
    """
    Abstract base class for gene annotation sources.

    Provides common functionality for fetching, storing, and managing
    gene annotations from various external sources.
    """

    # Source identification
    source_name: str = None  # Must be overridden
    display_name: str = None
    version: str = None

    # Cache configuration
    cache_ttl_days: int = 7
    cache_namespace: str = "annotations"

    # Batch processing
    batch_size: int = 50

    def __init__(self, session: Session):
        """
        Initialize annotation source.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

        if not self.source_name:
            raise ValueError("source_name must be defined in subclass")

        # Get or create source record
        self.source_record = self._get_or_create_source()

    def _get_or_create_source(self) -> AnnotationSource:
        """Get or create the annotation source record."""
        source = (
            self.session.query(AnnotationSource).filter_by(source_name=self.source_name).first()
        )

        if not source:
            source = AnnotationSource(
                source_name=self.source_name,
                display_name=self.display_name or self.source_name,
                is_active=True,
                config=self.get_default_config(),
            )
            self.session.add(source)
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

    def store_annotation(
        self, gene: Gene, annotation_data: dict[str, Any], metadata: dict[str, Any] | None = None
    ) -> GeneAnnotation:
        """
        Store annotation in database.

        Args:
            gene: Gene object
            annotation_data: Annotation data to store
            metadata: Optional metadata about the annotation

        Returns:
            Created or updated GeneAnnotation object
        """
        # Check for existing annotation
        existing = (
            self.session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source=self.source_name, version=self.version)
            .first()
        )

        # Track history if updating
        if existing:
            self._record_history(
                gene_id=gene.id,
                operation="update",
                old_data=existing.annotations,
                new_data=annotation_data,
            )

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
                updated_at=now
            )
            self.session.add(annotation)

            self._record_history(gene_id=gene.id, operation="insert", new_data=annotation_data)

        self.session.commit()
        return annotation

    def _record_history(
        self,
        gene_id: int,
        operation: str,
        old_data: dict | None = None,
        new_data: dict | None = None,
    ):
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

    async def update_gene(self, gene: Gene) -> bool:
        """
        Update annotations for a single gene.

        Args:
            gene: Gene to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get cache service
            cache_service = get_cache_service(self.session)

            # Check cache first
            cache_key = f"{gene.approved_symbol}:{gene.hgnc_id}"
            cached_data = await cache_service.get(
                key=cache_key,
                namespace=self.source_name.lower(),
                default=None
            )

            if cached_data:
                logger.sync_info(
                    f"Using cached annotation for {gene.approved_symbol}",
                    source=self.source_name
                )
                annotation_data = cached_data
                metadata = {
                    "retrieved_at": datetime.utcnow().isoformat(),
                    "from_cache": True
                }
            else:
                # Fetch from source
                annotation_data = await self.fetch_annotation(gene)

                if annotation_data:
                    # Cache the result
                    await cache_service.set(
                        key=cache_key,
                        value=annotation_data,
                        namespace=self.source_name.lower(),
                        ttl=self.cache_ttl_days * 86400  # Convert days to seconds
                    )
                    metadata = {
                        "retrieved_at": datetime.utcnow().isoformat(),
                        "from_cache": False
                    }

            if annotation_data:
                self.store_annotation(gene, annotation_data, metadata=metadata)
                return True

            logger.sync_warning(
                f"No annotation found for {gene.approved_symbol}",
                source=self.source_name
            )
            return False

        except Exception as e:
            logger.sync_error(
                f"Error updating gene {gene.approved_symbol}: {str(e)}",
                source=self.source_name
            )
            return False

    async def update_all_genes(self, limit: int | None = None) -> tuple[int, int]:
        """
        Update annotations for all genes.

        Args:
            limit: Optional limit on number of genes to process

        Returns:
            Tuple of (successful_count, failed_count)
        """
        logger.sync_info(f"Starting bulk update for {self.source_name}", limit=limit)

        # Get genes to update
        query = self.session.query(Gene)
        if limit:
            query = query.limit(limit)
        genes = query.all()

        successful = 0
        failed = 0

        # Process in batches
        for i in range(0, len(genes), self.batch_size):
            batch = genes[i : i + self.batch_size]
            logger.sync_info(f"Processing batch {i // self.batch_size + 1}", batch_size=len(batch))

            # Try batch fetch first
            try:
                batch_data = await self.fetch_batch(batch)

                for gene in batch:
                    if gene.id in batch_data:
                        self.store_annotation(
                            gene,
                            batch_data[gene.id],
                            metadata={
                                "retrieved_at": datetime.utcnow().isoformat(),
                                "batch_fetch": True,
                            },
                        )
                        successful += 1
                    else:
                        # Fall back to individual fetch
                        if await self.update_gene(gene):
                            successful += 1
                        else:
                            failed += 1

            except NotImplementedError:
                # Batch fetch not implemented, use individual updates
                for gene in batch:
                    if await self.update_gene(gene):
                        successful += 1
                    else:
                        failed += 1
            except Exception as e:
                logger.sync_error(f"Batch processing error: {str(e)}", batch_start=i)
                failed += len(batch)

        # Update source record
        self.source_record.last_update = datetime.utcnow()
        self.source_record.next_update = datetime.utcnow() + timedelta(days=self.cache_ttl_days)
        self.session.commit()

        # Refresh materialized view
        self._refresh_materialized_view()

        logger.sync_info(
            f"Bulk update completed for {self.source_name}", successful=successful, failed=failed
        )

        return successful, failed

    def _refresh_materialized_view(self):
        """Refresh the gene_annotations_summary materialized view."""
        try:
            self.session.execute(
                text("REFRESH MATERIALIZED VIEW CONCURRENTLY gene_annotations_summary")
            )
            self.session.commit()
            logger.sync_info("Materialized view refreshed")
        except Exception:
            # Try without CONCURRENTLY if it fails
            try:
                self.session.execute(text("REFRESH MATERIALIZED VIEW gene_annotations_summary"))
                self.session.commit()
                logger.sync_info("Materialized view refreshed (non-concurrent)")
            except Exception as e2:
                logger.sync_error(f"Failed to refresh materialized view: {str(e2)}")

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
