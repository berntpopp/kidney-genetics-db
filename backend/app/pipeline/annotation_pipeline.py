"""
Annotation pipeline orchestrator for managing gene annotation updates.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.progress_tracker import ProgressTracker
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.models.gene_annotation import AnnotationSource
from app.models.progress import DataSourceProgress
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
        self.source_name = "annotation_pipeline"  # For progress tracking
        self.checkpoint_data = None  # For storing checkpoint state

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

        logger.sync_info(
            "AnnotationPipeline.run_update started",
            strategy=strategy.value,
            sources=sources,
            gene_ids=gene_ids[:5] if gene_ids else None,
            force=force,
            task_id=task_id
        )

        # Initialize progress tracking
        self.progress_tracker = ProgressTracker(self.db, self.source_name)

        # Check if we're resuming a paused update
        checkpoint = await self._load_checkpoint()
        if checkpoint:
            logger.sync_info(
                "Resuming from checkpoint",
                strategy=strategy.value,
                checkpoint=checkpoint
            )
            # Restore state from checkpoint
            if not sources:
                sources = checkpoint.get("sources_remaining")
            if not gene_ids:
                gene_ids = checkpoint.get("gene_ids_remaining")

        if self.progress_tracker.is_paused():
            logger.sync_info(
                "Resuming paused annotation update",
                strategy=strategy.value,
                last_operation=self.progress_tracker.get_current_operation()
            )
        else:
            self.progress_tracker.start(operation=f"Starting annotation update ({strategy.value})")

        try:
            # Determine which sources to update
            logger.sync_debug("Getting sources to update...")
            sources_to_update = await self._get_sources_to_update(sources, force)
            logger.sync_info(
                "Sources to update determined",
                sources_to_update=sources_to_update,
                count=len(sources_to_update)
            )

            # Get genes to update based on strategy
            logger.sync_debug("Getting genes to update...")
            genes_to_update = await self._get_genes_to_update(strategy, gene_ids)
            logger.sync_info(
                "Genes to update determined",
                gene_count=len(genes_to_update),
                first_5_genes=[g.approved_symbol for g in genes_to_update[:5]] if genes_to_update else []
            )

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

            # Run updates with parallel processing where possible
            results = {}
            errors = []
            sources_completed = []

            # Phase 1: HGNC must complete first (provides Ensembl IDs)
            if "hgnc" in sources_to_update:
                logger.sync_info("Processing HGNC first (dependency for other sources)")
                try:
                    hgnc_results = await self._update_source_with_recovery(
                        "hgnc", genes_to_update, force
                    )
                    results["hgnc"] = hgnc_results
                    sources_completed.append("hgnc")
                    sources_to_update.remove("hgnc")
                except Exception as e:
                    logger.sync_error("HGNC update failed - critical dependency", error=str(e))
                    errors.append({"source": "hgnc", "error": str(e), "critical": True})
                    # HGNC failure may impact other sources

            # Phase 2: Process remaining sources in parallel
            if sources_to_update:
                logger.sync_info(f"Processing {len(sources_to_update)} sources in parallel")

                # Save checkpoint before parallel processing
                await self._save_checkpoint({
                    "sources_remaining": sources_to_update,
                    "sources_completed": sources_completed,
                    "gene_ids": [g.id for g in genes_to_update],
                    "strategy": strategy.value
                })

                parallel_results = await self._update_sources_parallel(
                    sources_to_update, genes_to_update, force
                )

                for source_name, result in parallel_results.items():
                    if "error" in result:
                        errors.append({"source": source_name, "error": result["error"]})
                    else:
                        results[source_name] = result
                        sources_completed.append(source_name)

            # Refresh materialized view ONCE after all sources complete
            if results:
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

        Prioritizes genes by clinical importance (evidence score) to ensure
        the most important genes get annotations first.

        Args:
            strategy: Update strategy
            gene_ids: Specific gene IDs if provided

        Returns:
            List of Gene objects to update, ordered by importance
        """
        from sqlalchemy import func

        if gene_ids:
            # Specific genes requested - simple query
            query = self.db.query(Gene).filter(Gene.id.in_(gene_ids))
            genes = query.order_by(Gene.id).all()
        elif strategy == UpdateStrategy.INCREMENTAL:
            # Get genes with incomplete annotations, ordered by clinical importance
            # First get gene scores for prioritization
            scores_subq = (
                self.db.execute(
                    text("""
                    SELECT g.id, COALESCE(gs.raw_score, 0) as score
                    FROM genes g
                    LEFT JOIN gene_scores gs ON g.id = gs.gene_id
                    """)
                ).fetchall()
            )
            score_dict = {row[0]: row[1] for row in scores_subq}

            # Get genes with fewer annotations than sources
            genes = (
                self.db.query(Gene)
                .outerjoin(Gene.annotations)
                .group_by(Gene.id)
                .having(func.count(text("gene_annotations.id")) < len(self.sources))
                .all()
            )

            # Sort by score (highest first), then by ID
            genes.sort(key=lambda g: (-score_dict.get(g.id, 0), g.id))
        else:
            # FULL or FORCED - get all genes ordered by clinical importance
            # Get gene scores for prioritization
            scores_subq = (
                self.db.execute(
                    text("""
                    SELECT g.id, COALESCE(gs.raw_score, 0) as score
                    FROM genes g
                    LEFT JOIN gene_scores gs ON g.id = gs.gene_id
                    ORDER BY COALESCE(gs.raw_score, 0) DESC, g.id
                    """)
                ).fetchall()
            )

            # Get genes in the prioritized order
            gene_ids_ordered = [row[0] for row in scores_subq]

            # Fetch Gene objects in this order
            if gene_ids_ordered:
                genes = self.db.query(Gene).filter(Gene.id.in_(gene_ids_ordered)).all()
                # Create a dict for quick lookup
                gene_dict = {g.id: g for g in genes}
                # Return in the prioritized order
                genes = [gene_dict[gid] for gid in gene_ids_ordered if gid in gene_dict]
            else:
                genes = []

        logger.sync_info(
            "Genes selected for annotation update",
            strategy=strategy.value,
            total_genes=len(genes),
            top_5_genes=[g.approved_symbol for g in genes[:5]] if genes else [],
            prioritization="evidence_score"
        )

        return genes

    async def _save_checkpoint(self, state: dict) -> None:
        """Save pipeline checkpoint for resume capability."""
        try:
            progress = self.db.query(DataSourceProgress).filter_by(
                source_name="annotation_pipeline"
            ).first()

            if not progress:
                progress = DataSourceProgress(
                    source_name="annotation_pipeline",
                    status="running"
                )
                self.db.add(progress)

            progress.progress_metadata = {
                "sources_remaining": state.get("sources_remaining", []),
                "sources_completed": state.get("sources_completed", []),
                "gene_ids": state.get("gene_ids", []),
                "batch_index": state.get("batch_index", 0),
                "strategy": state.get("strategy", "incremental"),
                "timestamp": datetime.utcnow().isoformat(),
                "version": "2.0"
            }
            self.db.commit()
            logger.sync_debug("Checkpoint saved", state=state)
        except Exception as e:
            logger.sync_error("Failed to save checkpoint", error=str(e))

    async def _load_checkpoint(self) -> dict | None:
        """Load pipeline checkpoint if exists."""
        try:
            progress = self.db.query(DataSourceProgress).filter_by(
                source_name="annotation_pipeline"
            ).first()

            if progress and progress.progress_metadata:
                logger.sync_info(
                    "Checkpoint found",
                    sources_remaining=progress.progress_metadata.get("sources_remaining"),
                    sources_completed=progress.progress_metadata.get("sources_completed")
                )
                return progress.progress_metadata
        except Exception as e:
            logger.sync_error("Failed to load checkpoint", error=str(e))
        return None

    async def _update_sources_parallel(
        self,
        sources: list[str],
        genes: list[Gene],
        force: bool = False
    ) -> dict[str, Any]:
        """Update multiple sources with controlled parallelism."""
        results = {}

        # Limit concurrent sources to respect API limits
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent sources

        async def rate_limited_update(source_name: str) -> tuple[str, dict]:
            """Update single source with rate limiting."""
            async with semaphore:
                try:
                    # Check if paused - skip this check for now as it's not critical
                    # Can be added later with proper implementation

                    logger.sync_info(f"Starting parallel update for {source_name}")
                    result = await self._update_source_with_recovery(
                        source_name, genes, force
                    )
                    return (source_name, result)
                except Exception as e:
                    logger.sync_error(f"Error in parallel update for {source_name}", error=str(e))
                    return (source_name, {"error": str(e)})

        # Create tasks for all sources
        tasks = [rate_limited_update(src) for src in sources]

        # Use gather with return_exceptions=True to handle failures independently
        parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in parallel_results:
            if isinstance(result, Exception):
                logger.sync_error(f"Task failed with exception: {result}")
                continue
            if isinstance(result, tuple) and len(result) == 2:
                source_name, source_result = result
                results[source_name] = source_result

        return results

    async def _update_source_with_recovery(
        self,
        source_name: str,
        genes: list[Gene],
        force: bool = False
    ) -> dict[str, Any]:
        """Update source with gene-level error recovery and retry."""
        logger.sync_info(
            f"Starting update with recovery for {source_name}",
            source_name=source_name,
            gene_count=len(genes),
            force=force
        )

        source_class = self.sources[source_name]
        source = source_class(self.db)

        successful = 0
        failed = 0
        failed_genes = []

        # Process genes in batches with concurrency
        batch_size = source.batch_size
        max_concurrent = 3 if source_name == "clinvar" else 5

        for i in range(0, len(genes), batch_size):
            # Check for pause
            if self.progress_tracker and self.progress_tracker.is_paused():
                await self._save_checkpoint({
                    "sources_remaining": [source_name],
                    "gene_ids": [g.id for g in genes[i:]],
                    "batch_index": i
                })
                logger.sync_info(f"Paused at batch {i}/{len(genes)}")
                return {"successful": successful, "failed": failed, "paused": True}

            batch = genes[i : i + batch_size]

            if self.progress_tracker:
                self.progress_tracker.update(
                    current_item=i,
                    operation=f"Updating {source_name}: {i}/{len(genes)} genes"
                )

            # Process batch with concurrency
            semaphore = asyncio.Semaphore(max_concurrent)

            async def update_with_semaphore(gene: Gene, sem: asyncio.Semaphore) -> tuple[Gene, bool]:
                async with sem:
                    try:
                        success = await source.update_gene(gene)
                        return (gene, success)
                    except Exception as e:
                        logger.sync_warning(
                            f"Failed to update {gene.approved_symbol}",
                            error=str(e)
                        )
                        return (gene, False)

            # Execute batch concurrently
            tasks = [update_with_semaphore(gene, semaphore) for gene in batch]
            batch_results = await asyncio.gather(*tasks)

            # Process results
            for gene, success in batch_results:
                if success:
                    successful += 1
                else:
                    failed_genes.append(gene)
                    failed += 1

        # Retry failed genes with exponential backoff
        if failed_genes:
            logger.sync_info(f"Retrying {len(failed_genes)} failed genes with backoff")
            retry_config = RetryConfig(
                max_retries=3,
                initial_delay=2.0,
                exponential_base=2.0,
                max_delay=30.0
            )

            @retry_with_backoff(config=retry_config)
            async def retry_gene(gene: Gene):
                return await source.update_gene(gene)

            for gene in failed_genes:
                try:
                    if await retry_gene(gene):
                        successful += 1
                        failed -= 1
                        logger.sync_info(f"Successfully retried {gene.approved_symbol}")
                except Exception as e:
                    logger.sync_error(f"Failed to retry {gene.approved_symbol}", error=str(e))

        # Update source metadata
        source_record = source.source_record
        source_record.last_update = datetime.utcnow()
        source_record.next_update = datetime.utcnow() + timedelta(days=source.cache_ttl_days)
        self.db.commit()

        return {
            "successful": successful,
            "failed": failed,
            "total": len(genes),
            "recovery_attempted": len(failed_genes) > 0
        }

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
