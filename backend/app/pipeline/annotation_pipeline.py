"""
Annotation pipeline orchestrator for managing gene annotation updates.
"""

import asyncio
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.progress_tracker import ProgressTracker
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.models.gene_annotation import AnnotationSource, GeneAnnotation
from app.models.progress import DataSourceProgress
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource
from app.pipeline.sources.annotations.descartes import DescartesAnnotationSource
from app.pipeline.sources.annotations.ensembl import EnsemblAnnotationSource
from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource
from app.pipeline.sources.annotations.gtex import GTExAnnotationSource
from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource
from app.pipeline.sources.annotations.hpo import HPOAnnotationSource
from app.pipeline.sources.annotations.mpo_mgi import MPOMGIAnnotationSource
from app.pipeline.sources.annotations.string_ppi import StringPPIAnnotationSource
from app.pipeline.sources.annotations.uniprot import UniProtAnnotationSource

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

    def __init__(self, db_session: Session) -> None:
        """
        Initialize the annotation pipeline.

        Args:
            db_session: Database session for operations
        """
        self.db = db_session
        self.progress_tracker: ProgressTracker | None = None
        self.source_name = "annotation_pipeline"  # For progress tracking
        self.checkpoint_data: dict[str, Any] | None = None  # For storing checkpoint state

        # Register available annotation sources
        # These are class types that will be instantiated when needed
        self.sources: dict[str, type[BaseAnnotationSource]] = {
            "hgnc": HGNCAnnotationSource,
            "gnomad": GnomADAnnotationSource,
            "gtex": GTExAnnotationSource,
            "descartes": DescartesAnnotationSource,
            "mpo_mgi": MPOMGIAnnotationSource,
            "string_ppi": StringPPIAnnotationSource,
            "hpo": HPOAnnotationSource,
            "clinvar": ClinVarAnnotationSource,
            "ensembl": EnsemblAnnotationSource,
            "uniprot": UniProtAnnotationSource,
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
            task_id=task_id,
        )

        # Initialize progress tracking
        self.progress_tracker = ProgressTracker(self.db, self.source_name)

        # Check if we're resuming a paused update
        checkpoint = await self._load_checkpoint()
        if checkpoint:
            logger.sync_info(
                "Resuming from checkpoint", strategy=strategy.value, checkpoint=checkpoint
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
                last_operation=self.progress_tracker.get_current_operation(),
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
                count=len(sources_to_update),
            )

            # Get genes to update based on strategy
            logger.sync_debug("Getting genes to update...")
            genes_to_update = await self._get_genes_to_update(strategy, gene_ids)
            logger.sync_info(
                "Genes to update determined",
                gene_count=len(genes_to_update),
                first_5_genes=[g.approved_symbol for g in genes_to_update[:5]]
                if genes_to_update
                else [],
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

            # Extract gene IDs upfront to avoid session conflicts in parallel processing
            gene_ids_to_update = [g.id for g in genes_to_update]

            # Phase 1: HGNC must complete first (provides Ensembl IDs)
            if "hgnc" in sources_to_update:
                logger.sync_info("Processing HGNC first (dependency for other sources)")
                try:
                    hgnc_results = await self._update_source_with_recovery(
                        "hgnc", gene_ids_to_update, force
                    )
                    results["hgnc"] = hgnc_results
                    sources_completed.append("hgnc")
                    sources_to_update.remove("hgnc")
                except Exception as e:
                    logger.sync_error(f"HGNC update failed - critical dependency: {e}")
                    errors.append({"source": "hgnc", "error": str(e), "critical": True})
                    # HGNC failure may impact other sources

            # Phase 2: Process remaining sources in parallel
            if sources_to_update:
                logger.sync_info(f"Processing {len(sources_to_update)} sources in parallel")

                # Save checkpoint before parallel processing
                await self._save_checkpoint(
                    {
                        "sources_remaining": sources_to_update,
                        "sources_completed": sources_completed,
                        "gene_ids": gene_ids_to_update,
                        "strategy": strategy.value,
                    }
                )

                parallel_results = await self._update_sources_parallel(
                    sources_to_update, gene_ids_to_update, force
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

            # Invalidate API caches after pipeline completion
            if results:
                try:
                    from app.api.endpoints.genes import (
                        clear_gene_ids_cache,
                        invalidate_metadata_cache,
                    )

                    clear_gene_ids_cache()
                    invalidate_metadata_cache()
                    logger.sync_info("API caches invalidated after pipeline completion")
                except Exception as e:
                    # Log but don't fail the pipeline
                    logger.sync_error(f"Failed to invalidate API caches: {e}")

            # Update global percentiles for STRING PPI after batch completion
            if "string_ppi" in sources_completed:
                try:
                    from app.pipeline.tasks.percentile_updater import update_percentiles_for_source

                    await logger.info("Triggering STRING PPI global percentile recalculation")
                    await update_percentiles_for_source(self.db, "string_ppi")
                    await logger.info("STRING PPI percentiles updated successfully")
                except Exception as e:
                    # Log but don't fail the pipeline
                    await logger.error(
                        f"Failed to update STRING PPI percentiles: {e}", exc_info=True
                    )

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
            "ensembl",
            "uniprot",
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

        genes: list[Gene] = []

        if gene_ids:
            # Specific genes requested - simple query
            query = self.db.query(Gene).filter(Gene.id.in_(gene_ids))
            genes = list(query.order_by(Gene.id).all())
        elif strategy == UpdateStrategy.INCREMENTAL:
            # Get genes with incomplete annotations, ordered by clinical importance
            # Using SQLAlchemy ORM to avoid SQL errors
            from app.models.gene import GeneCuration

            # Get genes with fewer annotations than sources
            genes = list(
                self.db.query(Gene)
                .outerjoin(Gene.annotations)
                .group_by(Gene.id)
                .having(func.count(GeneAnnotation.id) < len(self.sources))
                .all()
            )

            # Get scores for prioritization using ORM
            gene_ids_for_scores = [g.id for g in genes]
            if gene_ids_for_scores:
                scores = (
                    self.db.query(GeneCuration.gene_id, GeneCuration.evidence_score)
                    .filter(GeneCuration.gene_id.in_(gene_ids_for_scores))
                    .all()
                )
                score_dict: dict[int, Any] = dict(scores)
            else:
                score_dict = {}

            # Sort by score (highest first), then by ID
            genes.sort(key=lambda g: (-score_dict.get(g.id, 0), g.id))
        elif strategy == UpdateStrategy.SELECTIVE:
            # SELECTIVE: Get all genes for selective source update
            # Similar to FULL but the source filtering happens in run_update
            logger.sync_info(
                "Using SELECTIVE strategy - all genes will be processed for specific sources"
            )

            # Use ORM to get genes with scores, avoiding SQL errors
            from app.models.gene import GeneCuration

            # Query genes with their scores using ORM
            genes_with_scores = (
                self.db.query(Gene, func.coalesce(GeneCuration.evidence_score, 0).label("score"))
                .outerjoin(GeneCuration, Gene.id == GeneCuration.gene_id)
                .order_by(func.coalesce(GeneCuration.evidence_score, 0).desc(), Gene.id)
                .all()
            )

            # Extract just the Gene objects - these are already Gene instances from ORM
            for gene, _score in genes_with_scores:
                genes.append(gene)  # type: ignore[arg-type]
        else:
            # FULL or FORCED - get all genes ordered by clinical importance
            # Use ORM to avoid SQL errors
            from app.models.gene import GeneCuration

            # Query all genes with their scores using ORM
            genes_with_scores = (
                self.db.query(Gene, func.coalesce(GeneCuration.evidence_score, 0).label("score"))
                .outerjoin(GeneCuration, Gene.id == GeneCuration.gene_id)
                .order_by(func.coalesce(GeneCuration.evidence_score, 0).desc(), Gene.id)
                .all()
            )

            # Extract just the Gene objects - these are already Gene instances from ORM
            for gene, _score in genes_with_scores:
                genes.append(gene)  # type: ignore[arg-type]

        logger.sync_info(
            "Genes selected for annotation update",
            strategy=strategy.value,
            total_genes=len(genes),
            top_5_genes=[g.approved_symbol for g in genes[:5]] if genes else [],
            prioritization="evidence_score",
        )

        return genes

    async def _save_checkpoint(self, state: dict) -> None:
        """Save pipeline checkpoint for resume capability."""
        try:
            progress = (
                self.db.query(DataSourceProgress)
                .filter_by(source_name="annotation_pipeline")
                .first()
            )

            if not progress:
                progress = DataSourceProgress(source_name="annotation_pipeline", status="running")
                self.db.add(progress)

            progress.progress_metadata = {
                "sources_remaining": state.get("sources_remaining", []),
                "sources_completed": state.get("sources_completed", []),
                "gene_ids": state.get("gene_ids", []),
                "batch_index": state.get("batch_index", 0),
                "strategy": state.get("strategy", "incremental"),
                "timestamp": datetime.utcnow().isoformat(),
                "version": "2.0",
            }
            self.db.commit()
            logger.sync_debug("Checkpoint saved", state=state)
        except Exception as e:
            logger.sync_error(f"Failed to save checkpoint: {e}")

    async def _load_checkpoint(self) -> dict[str, Any] | None:
        """Load pipeline checkpoint if exists."""
        try:
            progress = (
                self.db.query(DataSourceProgress)
                .filter_by(source_name="annotation_pipeline")
                .first()
            )

            if progress and progress.progress_metadata:
                metadata: dict[str, Any] = dict(progress.progress_metadata)
                logger.sync_info(
                    "Checkpoint found",
                    sources_remaining=metadata.get("sources_remaining"),
                    sources_completed=metadata.get("sources_completed"),
                )
                return metadata
        except Exception as e:
            logger.sync_error(f"Failed to load checkpoint: {e}")
        return None

    async def _update_sources_parallel(
        self, sources: list[str], gene_ids: list[int], force: bool = False
    ) -> dict[str, Any]:
        """Update multiple sources with controlled parallelism.

        Args:
            sources: List of source names to update
            gene_ids: List of gene IDs (not Gene objects) to avoid session conflicts
            force: Whether to force update existing annotations
        """
        results = {}

        # Limit concurrent sources to respect API limits
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent sources

        async def rate_limited_update(source_name: str) -> tuple[str, dict]:
            """Update single source with rate limiting."""
            async with semaphore:
                try:
                    # Refresh database connection for long-running operation
                    if hasattr(self.db, "execute"):
                        # Ping database to ensure connection is alive
                        self.db.execute(text("SELECT 1"))

                    logger.sync_info(f"Starting parallel update for {source_name}")
                    result = await self._update_source_with_recovery(source_name, gene_ids, force)
                    return (source_name, result)
                except Exception as e:
                    logger.sync_error(f"Error in parallel update for {source_name}: {e}")
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
        self, source_name: str, gene_ids: list[int], force: bool = False
    ) -> dict[str, Any]:
        """Update source using batch fetch + bulk DB upsert for speed.

        Uses fetch_batch() to retrieve all annotations at once (bulk sources
        download a file once and do fast local lookups), then writes to the
        database in bulk using INSERT ... ON CONFLICT DO UPDATE.

        Falls back to per-gene update_gene() only for genes not returned by
        fetch_batch().

        Args:
            source_name: Name of the annotation source to update
            gene_ids: List of gene IDs (not Gene objects) to avoid session conflicts.
                     Genes are re-fetched from the database within this function.
            force: Whether to force update existing annotations
        """
        logger.sync_info(
            f"Starting batch update for {source_name}",
            source_name=source_name,
            gene_count=len(gene_ids),
            force=force,
        )

        # Re-fetch genes from database to ensure they're bound to current session
        genes = self.db.query(Gene).filter(Gene.id.in_(gene_ids)).all()

        if len(genes) != len(gene_ids):
            logger.sync_warning(
                f"Gene count mismatch: requested {len(gene_ids)}, found {len(genes)}"
            )

        source_class = self.sources[source_name]
        source = source_class(self.db)
        source.batch_mode = True

        total_genes = len(genes)
        successful = 0
        failed = 0
        failed_genes: list[Gene] = []

        # Phase 1: Batch fetch all annotations at once
        if self.progress_tracker:
            self.progress_tracker.update(
                current_item=0,
                operation=f"Fetching {source_name} annotations (batch)",
            )

        batch_data: dict[int, dict[str, Any]] = {}
        try:
            batch_data = await source.fetch_batch(genes)
            if batch_data is None:
                batch_data = {}
            logger.sync_info(
                f"Batch fetch complete for {source_name}",
                fetched=len(batch_data),
                total=total_genes,
            )
        except Exception as e:
            logger.sync_warning(
                f"Batch fetch failed for {source_name}, falling back to per-gene: {e}",
            )

        # Phase 2: Bulk upsert fetched annotations via INSERT ON CONFLICT
        if batch_data:
            if self.progress_tracker:
                self.progress_tracker.update(
                    current_item=0,
                    operation=f"Writing {source_name}: {len(batch_data)} annotations (bulk)",
                )

            upsert_count = self._bulk_upsert_annotations(
                source_name, source.version, batch_data
            )
            successful = upsert_count
            logger.sync_info(
                f"Bulk upsert complete for {source_name}",
                upserted=upsert_count,
            )

        # Phase 3: Per-gene fallback for genes not in batch_data
        missed_genes = [g for g in genes if g.id not in batch_data]
        if missed_genes:
            logger.sync_info(
                f"Per-gene fallback for {source_name}",
                missed=len(missed_genes),
            )
            for i, gene in enumerate(missed_genes):
                if self.progress_tracker and i % 100 == 0:
                    self.progress_tracker.update(
                        current_item=len(batch_data) + i,
                        operation=(
                            f"Updating {source_name}: "
                            f"fallback {i}/{len(missed_genes)} genes"
                        ),
                    )
                try:
                    if await source.update_gene(gene):
                        successful += 1
                    else:
                        failed_genes.append(gene)
                        failed += 1
                except Exception as e:
                    logger.sync_warning(f"Failed to update {gene.approved_symbol}: {e}")
                    failed_genes.append(gene)
                    failed += 1

            try:
                self.db.commit()
            except Exception as e:
                logger.sync_warning(f"Fallback commit failed: {e}")
                self.db.rollback()

        # Phase 4: Retry failed genes
        if failed_genes:
            logger.sync_info(f"Retrying {len(failed_genes)} failed genes with backoff")
            retry_config = RetryConfig(
                max_retries=3, initial_delay=2.0, exponential_base=2.0, max_delay=30.0
            )

            @retry_with_backoff(config=retry_config)
            async def retry_gene(gene: Gene) -> bool:
                return await source.update_gene(gene)

            for gene in failed_genes:
                try:
                    if await retry_gene(gene):
                        successful += 1
                        failed -= 1
                        logger.sync_info(f"Successfully retried {gene.approved_symbol}")
                except Exception as e:
                    logger.sync_error(f"Failed to retry {gene.approved_symbol}: {e}")

        source.batch_mode = False

        # Clear caches in background
        try:
            from concurrent.futures import ThreadPoolExecutor

            from app.core.cache_service import get_cache_service

            if not hasattr(self, "_executor"):
                self._executor = ThreadPoolExecutor(max_workers=2)

            def clear_cache_sync() -> None:
                cache_service = get_cache_service(self.db)
                if cache_service:
                    cache_service.clear_namespace_sync(source_name.lower())
                    cache_service.clear_namespace_sync("annotations")
                    logger.sync_debug(f"Cleared cache for {source_name}")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, clear_cache_sync)

        except Exception as e:
            logger.sync_debug(f"Cache clear failed: {e}")

        # Update source metadata
        source_record = source.source_record
        source_record.last_update = datetime.utcnow()
        source_record.next_update = datetime.utcnow() + timedelta(days=source.cache_ttl_days)
        self.db.commit()

        return {
            "successful": successful,
            "failed": failed,
            "total": total_genes,
            "recovery_attempted": len(failed_genes) > 0,
        }

    def _bulk_upsert_annotations(
        self,
        source_name: str,
        version: str | None,
        batch_data: dict[int, dict[str, Any]],
    ) -> int:
        """Bulk upsert annotations using INSERT ... ON CONFLICT DO UPDATE.

        Writes all annotations in a single SQL statement per chunk,
        replacing ~5000 individual SELECT+INSERT/UPDATE pairs.

        Args:
            source_name: Annotation source name
            version: Source version string
            batch_data: Mapping of gene_id -> annotation JSONB data

        Returns:
            Number of rows upserted
        """
        if not batch_data:
            return 0

        now = datetime.utcnow()
        metadata_json = json.dumps(
            {"retrieved_at": now.isoformat(), "batch_fetch": True}
        )

        upserted = 0
        chunk_size = 500  # Rows per INSERT statement
        items = list(batch_data.items())

        for chunk_start in range(0, len(items), chunk_size):
            chunk = items[chunk_start : chunk_start + chunk_size]

            # Build parameterized VALUES list
            values_clauses = []
            params: dict[str, Any] = {}
            for idx, (gene_id, annotations) in enumerate(chunk):
                values_clauses.append(
                    f"(:gene_id_{idx}, :source, :version, "
                    f"CAST(:annotations_{idx} AS jsonb), "
                    f"CAST(:metadata AS jsonb), :now, :now)"
                )
                params[f"gene_id_{idx}"] = gene_id
                params[f"annotations_{idx}"] = json.dumps(annotations)

            params["source"] = source_name
            params["version"] = version
            params["metadata"] = metadata_json
            params["now"] = now

            sql = text(
                f"INSERT INTO gene_annotations "
                f"(gene_id, source, version, annotations, source_metadata, "
                f"created_at, updated_at) VALUES {', '.join(values_clauses)} "
                f"ON CONFLICT (gene_id, source, version) DO UPDATE SET "
                f"annotations = EXCLUDED.annotations, "
                f"source_metadata = EXCLUDED.source_metadata, "
                f"updated_at = EXCLUDED.updated_at"
            )

            try:
                self.db.execute(sql, params)
                self.db.commit()
                upserted += len(chunk)
            except Exception as e:
                logger.sync_error(
                    f"Bulk upsert failed for {source_name} chunk: {e}"
                )
                self.db.rollback()

        return upserted

    async def _refresh_materialized_view(self) -> bool:
        """Refresh all materialized views without blocking."""

        def refresh_sync() -> bool:
            views_to_refresh = ["gene_scores", "gene_annotations_summary"]
            all_success = True

            for view_name in views_to_refresh:
                try:
                    # Try concurrent refresh first
                    self.db.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"))
                    self.db.commit()
                    logger.sync_info(f"Materialized view {view_name} refreshed concurrently")
                except Exception:
                    # Fallback to non-concurrent
                    try:
                        self.db.execute(text(f"REFRESH MATERIALIZED VIEW {view_name}"))
                        self.db.commit()
                        logger.sync_info(
                            f"Materialized view {view_name} refreshed (non-concurrent)"
                        )
                    except Exception as e:
                        logger.sync_error(f"Failed to refresh materialized view {view_name}: {e}")
                        self.db.rollback()
                        all_success = False

            return all_success

        # Execute in thread pool to avoid blocking
        if not hasattr(self, "_executor"):
            from concurrent.futures import ThreadPoolExecutor

            self._executor = ThreadPoolExecutor(max_workers=2)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self._executor, refresh_sync)
        return result

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
