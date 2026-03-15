"""
Lightweight pipeline orchestrator with 3-stage DAG.

Chains: Evidence sources -> Annotation pipeline -> Evidence aggregation.
Each stage waits for the previous stage to complete before starting.
Source-level failures are tolerated (skip source, continue).
Stage-level failures halt downstream stages.
"""

import asyncio
from enum import IntEnum
from typing import Any

from app.core.logging import get_logger
from app.models.progress import DataSourceProgress, SourceStatus

logger = get_logger(__name__)


class PipelineStage(IntEnum):
    """Pipeline execution stages in dependency order."""

    IDLE = 0
    EVIDENCE = 1
    ANNOTATIONS = 2
    AGGREGATION = 3
    COMPLETE = 4


class PipelineOrchestrator:
    """
    Manages the 3-stage pipeline lifecycle.

    Usage:
        orchestrator = PipelineOrchestrator(task_manager)
        await orchestrator.start_pipeline()

    On each evidence source completion, call:
        orchestrator.on_source_completed("PanelApp")

    When all evidence sources finish, annotations trigger automatically.
    """

    # Evidence sources that must complete before annotations start
    EVIDENCE_SOURCES = [
        "PanelApp",
        "PubTator",
        "ClinGen",
        "GenCC",
        "HPO",
    ]

    def __init__(self, task_manager: Any) -> None:
        self.task_manager = task_manager
        self._current_stage = PipelineStage.IDLE
        self._completed_sources: set[str] = set()
        self._failed_sources: set[str] = set()
        self._pipeline_lock = asyncio.Lock()

    @property
    def current_stage(self) -> PipelineStage:
        return self._current_stage

    def _load_state_from_db(self) -> None:
        """Populate _completed_sources and _failed_sources from data_source_progress.

        This allows the orchestrator to survive backend restarts by recovering
        which evidence sources already finished in a previous run.
        """
        from app.core.database import SessionLocal

        evidence_names = set(self.EVIDENCE_SOURCES)
        db = SessionLocal()
        try:
            rows = (
                db.query(DataSourceProgress)
                .filter(DataSourceProgress.source_name.in_(evidence_names))
                .all()
            )
            for row in rows:
                if row.status == SourceStatus.completed:
                    self._completed_sources.add(row.source_name)
                elif row.status == SourceStatus.failed:
                    self._failed_sources.add(row.source_name)
            if self._completed_sources or self._failed_sources:
                logger.sync_info(
                    "Restored pipeline state from DB",
                    completed=list(self._completed_sources),
                    failed=list(self._failed_sources),
                )
        except Exception as e:
            logger.sync_warning(
                "Could not load pipeline state from DB — starting fresh",
                error=str(e),
            )
        finally:
            db.close()

    async def start_pipeline(self) -> None:
        """Start the full pipeline from evidence collection.

        On restart, recovers evidence source state from the database.
        If all evidence sources already finished, skips directly to
        seeding and annotations.
        """
        skip_evidence = False

        async with self._pipeline_lock:
            if self._current_stage != PipelineStage.IDLE:
                logger.sync_warning(
                    "Pipeline already running",
                    current_stage=self._current_stage.name,
                )
                return

            # Recover state from DB before deciding what to do
            self._completed_sources.clear()
            self._failed_sources.clear()
            self._load_state_from_db()

            all_evidence = set(self.EVIDENCE_SOURCES)
            done_sources = self._completed_sources | self._failed_sources

            if done_sources >= all_evidence:
                # All evidence sources already finished — skip to annotations
                if len(self._completed_sources) == 0:
                    logger.sync_error(
                        "All evidence sources failed in previous run — not starting pipeline",
                        failed_sources=list(self._failed_sources),
                    )
                    return
                self._current_stage = PipelineStage.ANNOTATIONS
                skip_evidence = True
                logger.sync_info(
                    "All evidence sources already done — skipping to seed + annotate",
                    completed=len(self._completed_sources),
                    failed=len(self._failed_sources),
                )
            else:
                self._current_stage = PipelineStage.EVIDENCE

        if skip_evidence:
            asyncio.create_task(self._seed_and_annotate())
        else:
            logger.sync_info("Pipeline started — Stage 1: Evidence collection")
            await self.task_manager.start_auto_updates()

    async def on_source_completed(self, source_name: str, success: bool = True) -> None:
        """
        Called when an evidence source finishes (success or failure).

        Automatically triggers annotations when all evidence sources are done.
        """
        if self._current_stage != PipelineStage.EVIDENCE:
            return

        if success:
            self._completed_sources.add(source_name)
            logger.sync_info(
                "Evidence source completed",
                source_name=source_name,
                completed=len(self._completed_sources),
                failed=len(self._failed_sources),
                total=len(self.EVIDENCE_SOURCES),
            )
        else:
            self._failed_sources.add(source_name)
            logger.sync_warning(
                "Evidence source failed",
                source_name=source_name,
                completed=len(self._completed_sources),
                failed=len(self._failed_sources),
                total=len(self.EVIDENCE_SOURCES),
            )

        # Check if all evidence sources are done
        all_sources = set(self.EVIDENCE_SOURCES)
        done_sources = self._completed_sources | self._failed_sources
        if done_sources >= all_sources:
            await self._advance_to_annotations()

    async def _advance_to_annotations(self) -> None:
        """Transition to Stage 2: Annotation pipeline."""
        async with self._pipeline_lock:
            if self._current_stage != PipelineStage.EVIDENCE:
                return
            self._current_stage = PipelineStage.ANNOTATIONS

        succeeded = len(self._completed_sources)
        failed = len(self._failed_sources)

        if succeeded == 0:
            logger.sync_error(
                "All evidence sources failed — skipping annotations",
                failed_sources=list(self._failed_sources),
            )
            self._current_stage = PipelineStage.IDLE
            return

        logger.sync_info(
            "All evidence sources done — seeding then annotating",
            succeeded=succeeded,
            failed=failed,
        )

        # Run seeding (DiagnosticPanels/Literature) + annotations in background
        asyncio.create_task(self._seed_and_annotate())

    async def _seed_and_annotate(self) -> None:
        """Seed static evidence, re-run PubTator, then run annotation pipeline."""
        from app.core.database import SessionLocal
        from app.core.initial_seeder import needs_initial_seeding, run_initial_seeding

        # Step 1: Seed DiagnosticPanels/Literature (creates missing genes too)
        db = SessionLocal()
        try:
            if needs_initial_seeding(db):
                logger.sync_info("Seeding DiagnosticPanels/Literature after evidence sources")
                seed_results = await run_initial_seeding(db)
                logger.sync_info("Seeding complete", results=seed_results)
            else:
                logger.sync_debug("Seeding not needed — evidence data already exists")
        except Exception as e:
            logger.sync_warning(
                "Initial seeding failed — continuing to annotations",
                error=str(e),
            )
        finally:
            db.close()

        # Step 2: Run initial aggregation + refresh views so frontend works immediately
        try:
            logger.sync_info("Running initial aggregation so frontend has data")
            await self._run_aggregation_only()
        except Exception as e:
            logger.sync_warning("Initial aggregation failed", error=str(e))

        # Step 3: Run annotations (will refresh views again at the end)
        await self._run_annotations()

    async def _run_annotations(self) -> None:
        """Execute the annotation pipeline, then advance to aggregation."""
        from app.core.database import SessionLocal
        from app.pipeline.annotation_pipeline import (
            AnnotationPipeline,
            UpdateStrategy,
        )

        db = SessionLocal()
        try:
            pipeline = AnnotationPipeline(db)
            results = await pipeline.run_update(
                strategy=UpdateStrategy.INCREMENTAL,
                force=False,
            )
            logger.sync_info(
                "Annotation pipeline completed",
                results=results,
            )
            await self._advance_to_aggregation()
        except Exception as e:
            logger.sync_error(
                "Annotation pipeline failed",
                error=str(e),
            )
            self._current_stage = PipelineStage.IDLE
        finally:
            db.close()

    async def _run_aggregation_only(self) -> None:
        """Run aggregation + refresh materialized views (no stage transition)."""
        from starlette.concurrency import run_in_threadpool

        from app.core.database import SessionLocal
        from app.pipeline.aggregate import update_all_curations

        def _aggregate_and_refresh() -> None:
            from sqlalchemy import text

            db = SessionLocal()
            try:
                update_all_curations(db)
                # Refresh gene_scores so the frontend can display data
                try:
                    db.execute(text("REFRESH MATERIALIZED VIEW gene_scores"))
                    db.commit()
                    logger.sync_info("Refreshed gene_scores materialized view")
                except Exception as e:
                    db.rollback()
                    logger.sync_warning(
                        "Failed to refresh gene_scores view",
                        error=str(e),
                    )
            finally:
                db.close()

        await run_in_threadpool(_aggregate_and_refresh)
        logger.sync_info("Aggregation and view refresh complete")

    async def _advance_to_aggregation(self) -> None:
        """Transition to Stage 3: Evidence aggregation + view refresh."""
        async with self._pipeline_lock:
            self._current_stage = PipelineStage.AGGREGATION

        logger.sync_info("Stage 3: Evidence aggregation")

        try:
            await self._run_aggregation_only()
            self._current_stage = PipelineStage.COMPLETE
            logger.sync_info(
                "Pipeline complete — all stages finished",
                completed_sources=list(self._completed_sources),
                failed_sources=list(self._failed_sources),
            )
        except Exception as e:
            logger.sync_error(
                "Evidence aggregation failed",
                error=str(e),
            )
            self._current_stage = PipelineStage.IDLE

    def reset(self) -> None:
        """Reset orchestrator to idle state."""
        self._current_stage = PipelineStage.IDLE
        self._completed_sources.clear()
        self._failed_sources.clear()
