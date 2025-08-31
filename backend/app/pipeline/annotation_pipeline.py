"""
Annotation pipeline orchestrator for managing gene annotation updates.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.progress_tracker import ProgressTracker
from app.models.gene import Gene
from app.models.gene_annotation import AnnotationSource
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource
from app.pipeline.sources.annotations.descartes import DescartesAnnotationSource
from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource
from app.pipeline.sources.annotations.gtex import GTExAnnotationSource
from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource
from app.pipeline.sources.annotations.hpo import HPOAnnotationSource
from app.pipeline.sources.annotations.mpo_mgi import MPOMGIAnnotationSource
from app.pipeline.sources.annotations.string_ppi import StringPPIAnnotationSource

logger = get_logger(__name__)


class UpdateStrategy(str, Enum):
    """Update strategy options."""

    FULL = "full"  # Update all genes
    INCREMENTAL = "incremental"  # Update only changed/new genes
    FORCED = "forced"  # Force refresh regardless of TTL
    SELECTIVE = "selective"  # Update specific sources only


class AnnotationPipeline:
    """
    Main orchestrator for gene annotation updates.

    Coordinates multiple annotation sources, handles errors,
    tracks progress, and manages update strategies.
    """

    def __init__(self, db_session: Session):
        """
        Initialize the annotation pipeline.

        Args:
            db_session: Database session for operations
        """
        self.db = db_session
        self.progress_tracker = None

        # Register available annotation sources
        self.sources = {
            "hgnc": HGNCAnnotationSource,
            "gnomad": GnomADAnnotationSource,
            "gtex": GTExAnnotationSource,
            "descartes": DescartesAnnotationSource,
            "mpo_mgi": MPOMGIAnnotationSource,
            "string_ppi": StringPPIAnnotationSource,
            "hpo": HPOAnnotationSource,
            "clinvar": ClinVarAnnotationSource,
        }

    async def run_update(
        self,
        strategy: UpdateStrategy = UpdateStrategy.INCREMENTAL,
        sources: list[str] | None = None,
        gene_ids: list[int] | None = None,
        force: bool = False,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Run annotation update with specified strategy.

        Args:
            strategy: Update strategy to use
            sources: Specific sources to update (None = all)
            gene_ids: Specific gene IDs to update (None = all)
            force: Force update regardless of TTL
            task_id: Optional task ID for progress tracking

        Returns:
            Dictionary with update results
        """
        start_time = datetime.utcnow()

        # Initialize progress tracking
        if task_id:
            self.progress_tracker = ProgressTracker(self.db, "annotation_pipeline")
            self.progress_tracker.start(operation=f"Starting annotation update ({strategy.value})")

        try:
            # Determine which sources to update
            sources_to_update = await self._get_sources_to_update(sources, force)

            # Get genes to update based on strategy
            genes_to_update = await self._get_genes_to_update(strategy, gene_ids)

            # Check if there's anything to update
            if not sources_to_update or not genes_to_update:
                logger.sync_warning(
                    "No sources or genes to update",
                    sources_count=len(sources_to_update),
                    genes_count=len(genes_to_update),
                )
                if self.progress_tracker:
                    self.progress_tracker.complete(operation="No updates needed")
                return {
                    "sources_updated": [],
                    "genes_updated": 0,
                    "errors": [],
                    "duration": 0,
                    "message": "No sources or genes to update",
                }

            logger.sync_info(
                "Starting annotation update",
                strategy=strategy.value,
                sources=sources_to_update,
                gene_count=len(genes_to_update),
            )

            # Run updates for each source
            results = {}
            errors = []

            total_steps = len(sources_to_update) * len(genes_to_update)
            current_step = 0

            for source_name in sources_to_update:
                logger.sync_info(f"Updating {source_name} annotations")

                if self.progress_tracker:
                    # Avoid division by zero
                    progress = 0 if total_steps == 0 else int((current_step / total_steps) * 100)
                    self.progress_tracker.update(
                        current_item=progress,
                        operation=f"Updating {source_name} annotations",
                    )

                try:
                    source_results = await self._update_source(
                        source_name, genes_to_update, force, current_step, total_steps
                    )
                    results[source_name] = source_results
                    current_step += len(genes_to_update)

                except Exception as e:
                    logger.sync_error(f"Error updating {source_name}", error=str(e))
                    errors.append({"source": source_name, "error": str(e)})
                    current_step += len(genes_to_update)

            # Refresh materialized view
            await self._refresh_materialized_view()

            # Calculate summary statistics
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            summary = {
                "strategy": strategy.value,
                "sources_updated": len(results),
                "genes_processed": len(genes_to_update),
                "duration_seconds": duration,
                "results_by_source": results,
                "errors": errors,
                "success": len(errors) == 0,
            }

            if self.progress_tracker:
                self.progress_tracker.complete(
                    operation=f"Update completed in {duration:.1f} seconds"
                )

            logger.sync_info("Annotation update completed", **summary)

            return summary

        except Exception as e:
            logger.sync_error(f"Pipeline error: {str(e)}", strategy=strategy.value)

            if self.progress_tracker:
                self.progress_tracker.error(error_message=f"Pipeline failed: {str(e)}")

            raise

    async def _get_sources_to_update(
        self, requested_sources: list[str] | None, force: bool
    ) -> list[str]:
        """
        Determine which sources need updating.

        Args:
            requested_sources: Specific sources requested
            force: Force update regardless of schedule

        Returns:
            List of source names to update
        """
        if requested_sources:
            # Validate requested sources
            valid_sources = []
            for source in requested_sources:
                if source in self.sources:
                    valid_sources.append(source)
                else:
                    logger.sync_warning(f"Unknown source: {source}")
            return valid_sources

        # Get all active sources that need updating
        sources_to_update = []

        sources = self.db.query(AnnotationSource).filter(AnnotationSource.is_active.is_(True)).all()

        for source in sources:
            if force or source.is_update_due():
                sources_to_update.append(source.source_name)

        # Ensure HGNC runs first as it provides Ensembl IDs needed by other sources
        priority_order = [
            "hgnc",
            "gnomad",
            "gtex",
            "descartes",
            "mpo_mgi",
            "string_ppi",
            "hpo",
            "clinvar",
        ]
        ordered_sources = []

        # Add sources in priority order
        for priority_source in priority_order:
            if priority_source in sources_to_update:
                ordered_sources.append(priority_source)

        # Add any remaining sources not in priority list
        for source in sources_to_update:
            if source not in ordered_sources:
                ordered_sources.append(source)

        return ordered_sources

    async def _get_genes_to_update(
        self, strategy: UpdateStrategy, gene_ids: list[int] | None
    ) -> list[Gene]:
        """
        Get list of genes to update based on strategy.

        Args:
            strategy: Update strategy
            gene_ids: Specific gene IDs if provided

        Returns:
            List of Gene objects to update
        """
        query = self.db.query(Gene)

        if gene_ids:
            # Specific genes requested
            query = query.filter(Gene.id.in_(gene_ids))
        elif strategy == UpdateStrategy.INCREMENTAL:
            # Only genes without annotations or outdated ones
            # For now, get genes that don't have annotations from all sources
            query = (
                query.outerjoin(Gene.annotations)
                .group_by(Gene.id)
                .having(
                    text("COUNT(gene_annotations.id) < 2")  # Less than 2 sources
                )
            )
        elif strategy == UpdateStrategy.FULL or strategy == UpdateStrategy.FORCED:
            # All genes
            pass

        genes = query.all()
        return genes

    async def _update_source(
        self, source_name: str, genes: list[Gene], force: bool, current_step: int, total_steps: int
    ) -> dict[str, Any]:
        """
        Update annotations from a specific source.

        Args:
            source_name: Name of the annotation source
            genes: List of genes to update
            force: Force update
            current_step: Current progress step
            total_steps: Total progress steps

        Returns:
            Update results for this source
        """
        source_class = self.sources[source_name]
        source = source_class(self.db)

        successful = 0
        failed = 0

        # Process genes in batches
        batch_size = source.batch_size

        for i in range(0, len(genes), batch_size):
            batch = genes[i : i + batch_size]

            if self.progress_tracker:
                # Avoid division by zero
                progress = 0 if total_steps == 0 else int(((current_step + i) / total_steps) * 100)
                self.progress_tracker.update(
                    current_item=progress,
                    operation=f"Updating {source_name}: {i}/{len(genes)} genes",
                )

            # Try batch update first
            try:
                batch_results = await source.fetch_batch(batch)

                for gene in batch:
                    if gene.id in batch_results:
                        source.store_annotation(
                            gene,
                            batch_results[gene.id],
                            metadata={
                                "retrieved_at": datetime.utcnow().isoformat(),
                                "pipeline_run": True,
                            },
                        )
                        successful += 1
                    else:
                        failed += 1

            except NotImplementedError:
                # Fall back to individual updates
                for gene in batch:
                    success = await source.update_gene(gene)
                    if success:
                        successful += 1
                    else:
                        failed += 1
            except Exception as e:
                logger.sync_error(
                    f"Batch update error for {source_name}", error=str(e), batch_start=i
                )
                failed += len(batch)

        # Update source metadata
        source_record = source.source_record
        source_record.last_update = datetime.utcnow()
        source_record.next_update = datetime.utcnow() + timedelta(days=source.cache_ttl_days)
        self.db.commit()

        return {"successful": successful, "failed": failed, "total": len(genes)}

    async def _refresh_materialized_view(self):
        """Refresh the gene_annotations_summary materialized view."""
        try:
            self.db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY gene_annotations_summary"))
            self.db.commit()
            logger.sync_info("Materialized view refreshed")
        except Exception:
            # Try without CONCURRENTLY
            try:
                self.db.execute(text("REFRESH MATERIALIZED VIEW gene_annotations_summary"))
                self.db.commit()
                logger.sync_info("Materialized view refreshed (non-concurrent)")
            except Exception as e2:
                logger.sync_error(f"Failed to refresh materialized view: {str(e2)}")

    async def check_source_status(self) -> list[dict[str, Any]]:
        """
        Check the status of all annotation sources.

        Returns:
            List of source status dictionaries
        """
        sources = self.db.query(AnnotationSource).all()

        status_list = []
        for source in sources:
            status = {
                "source": source.source_name,
                "display_name": source.display_name,
                "is_active": source.is_active,
                "last_update": source.last_update.isoformat() if source.last_update else None,
                "next_update": source.next_update.isoformat() if source.next_update else None,
                "update_due": source.is_update_due(),
                "update_frequency": source.update_frequency,
            }

            # Get annotation count
            from app.models.gene_annotation import GeneAnnotation

            count = (
                self.db.query(GeneAnnotation)
                .filter(GeneAnnotation.source == source.source_name)
                .count()
            )
            status["annotation_count"] = count

            status_list.append(status)

        return status_list

    async def validate_annotations(self, source: str | None = None) -> dict[str, Any]:
        """
        Validate existing annotations for consistency.

        Args:
            source: Specific source to validate (None = all)

        Returns:
            Validation results
        """
        from app.models.gene_annotation import GeneAnnotation

        issues = []

        # Check for missing required fields
        query = self.db.query(GeneAnnotation)
        if source:
            query = query.filter(GeneAnnotation.source == source)

        annotations = query.all()

        for annotation in annotations:
            # Check HGNC annotations
            if annotation.source == "hgnc":
                if not annotation.get_annotation_value("ncbi_gene_id"):
                    issues.append(
                        {
                            "gene_id": annotation.gene_id,
                            "source": "hgnc",
                            "issue": "Missing NCBI Gene ID",
                        }
                    )

            # Check gnomAD annotations
            elif annotation.source == "gnomad":
                if annotation.get_annotation_value("pli") is None:
                    issues.append(
                        {
                            "gene_id": annotation.gene_id,
                            "source": "gnomad",
                            "issue": "Missing pLI score",
                        }
                    )

        return {
            "total_annotations": len(annotations),
            "issues_found": len(issues),
            "issues": issues[:100],  # Limit to first 100 issues
        }
