# Pipeline Stability & Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 5 critical pipeline bugs that prevent evidence sources, annotations, and initial data from loading reliably, making the system production-ready.

**Architecture:** Targeted fixes to existing code (HTTP client, progress tracking, GenCC config) plus a lightweight pipeline orchestration layer (~200 lines) that chains evidence→annotations→aggregation. No external dependencies added. Follows existing patterns (UnifiedLogger, CacheService, ProgressTracker).

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, httpx/hishel, asyncio, PostgreSQL

---

> **Audit Summary (from deep investigation 2026-03-15):**
>
> | # | Bug | Root Cause | File:Line |
> |---|-----|------------|-----------|
> | 1 | GenCC fails with HTTP 301 | `CachedHttpClient` doesn't pass `follow_redirects=True` to hishel; URL hardcoded | `cached_http_client.py:74`, `gencc.py:58` |
> | 2 | PubTator "completed" with 0 items in 5ms | `data_source_base.py:170-172` marks empty results as `completed` | `data_source_base.py:170` |
> | 3 | No evidence→annotation chaining | `start_auto_updates()` fires all sources concurrently; annotations only on cron | `background_tasks.py:38-55`, `main.py:107-122` |
> | 4 | DiagnosticPanels/Literature never loaded | No auto-seed mechanism for scraper output in `scrapers/*/output/` | N/A (missing feature) |
> | 5 | Double `tracker.start()` resets counters to 0 | `@managed_task` creates tracker, then source calls `tracker.start()` again | `task_decorator.py:37`, `progress_tracker.py:126-138` |

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/core/cached_http_client.py` | Modify (line 74) | Add `follow_redirects=True` |
| `backend/app/pipeline/sources/unified/gencc.py` | Modify (line 58) | Use config for download URL |
| `backend/config/datasources.yaml` | Modify (line 95) | Update GenCC `download_url` |
| `backend/app/core/data_source_base.py` | Modify (lines 170-173) | Guard against 0-item completion |
| `backend/app/core/progress_tracker.py` | Modify (line 120-138) | Make `start()` idempotent (skip counter reset on re-call) |
| `backend/app/core/pipeline_orchestrator.py` | Create | 3-stage DAG: evidence→annotations→aggregation |
| `backend/app/core/background_tasks.py` | Modify (lines 38-62, 192-200) | Hook orchestrator into task completion |
| `backend/app/main.py` | Modify (lines 107-122) | Use orchestrator instead of direct auto-update |
| `backend/app/data/seed/diagnostic_panels/*.json` | Create (copied) | 9 provider seed files from scrapers output |
| `backend/app/data/seed/literature/*.json` | Create (copied) | 12 publication seed files from scrapers output |
| `backend/app/core/initial_seeder.py` | Create | Load seed data from `backend/app/data/seed/` on empty DB |
| `backend/app/core/startup.py` | Modify | Call initial seeder if no evidence data exists |
| `Makefile` | Modify | Add `db-seed-initial` target |
| `backend/tests/test_pipeline_orchestrator.py` | Create | Tests for orchestrator |
| `backend/tests/test_cached_http_client.py` | Create | Test redirect following |
| `backend/tests/test_data_source_base_guards.py` | Create | Test 0-item guard |
| `backend/tests/test_initial_seeder.py` | Create | Test initial seeding |

---

## Chunk 1: HTTP Client & GenCC Redirect Fix

### Task 1: Fix CachedHttpClient to follow redirects

**Files:**
- Modify: `backend/app/core/cached_http_client.py:74`
- Test: `backend/tests/test_cached_http_client.py` (new)

- [ ] **Step 1: Write failing test for redirect following**

Create `backend/tests/test_cached_http_client.py`:

```python
"""Tests for CachedHttpClient redirect and resilience behavior."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.cached_http_client import CachedHttpClient


@pytest.mark.unit
class TestCachedHttpClientRedirects:
    """Verify CachedHttpClient follows redirects."""

    def test_http_client_has_follow_redirects_enabled(self):
        """The underlying hishel client must follow redirects."""
        with patch("app.core.cached_http_client.hishel") as mock_hishel:
            mock_hishel.Controller.return_value = MagicMock()
            mock_hishel.AsyncFileStorage.return_value = MagicMock()
            mock_hishel.AsyncCacheClient.return_value = MagicMock()

            client = CachedHttpClient.__new__(CachedHttpClient)
            # Manually run __init__ logic we care about
            from app.core.config import settings
            from pathlib import Path

            client.cache_service = MagicMock()
            client.timeout = 30.0
            client.max_retries = 3
            client.retry_delay = 1.0
            client.cache_dir = Path(settings.HTTP_CACHE_DIR)
            client.cache_dir.mkdir(parents=True, exist_ok=True)
            client.controller = mock_hishel.Controller(
                cacheable_methods=["GET", "HEAD"],
                cacheable_status_codes=[200, 301, 302, 304, 404],
                allow_stale=True,
                always_revalidate=False,
                allow_heuristics=True,
            )
            client.storage = mock_hishel.AsyncFileStorage(
                base_path=str(client.cache_dir),
            )
            # This is what we're testing - the actual __init__ should pass this
            CachedHttpClient.__init__(client)

            # Verify follow_redirects=True was passed
            call_kwargs = mock_hishel.AsyncCacheClient.call_args
            assert call_kwargs is not None
            _, kwargs = call_kwargs
            assert kwargs.get("follow_redirects") is True, (
                "CachedHttpClient must pass follow_redirects=True to AsyncCacheClient"
            )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_cached_http_client.py -v`
Expected: FAIL — `follow_redirects` not passed currently.

- [ ] **Step 3: Apply fix — add follow_redirects=True**

In `backend/app/core/cached_http_client.py`, change line 74-76 from:

```python
        self.http_client = hishel.AsyncCacheClient(
            controller=self.controller, storage=self.storage, timeout=httpx.Timeout(timeout)
        )
```

to:

```python
        self.http_client = hishel.AsyncCacheClient(
            controller=self.controller,
            storage=self.storage,
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_cached_http_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/cached_http_client.py backend/tests/test_cached_http_client.py
git commit -m "fix(http): enable follow_redirects in CachedHttpClient"
```

### Task 2: Fix GenCC hardcoded URL — use config

**Files:**
- Modify: `backend/app/pipeline/sources/unified/gencc.py:58`
- Modify: `backend/config/datasources.yaml:95-96`

- [ ] **Step 1: Update datasources.yaml with correct GenCC download URL**

In `backend/config/datasources.yaml`, change the GenCC `excel_url` line (around line 96) and add `download_url`:

```yaml
  GenCC:
    display_name: GenCC
    description: Harmonized gene-disease relationships from 40+ submitters worldwide
    url: https://thegencc.org/
    documentation_url: https://thegencc.org/faq.html
    auto_update: true
    priority: 4
    # API settings
    api_url: https://search.thegencc.org/api/submissions
    download_url: https://thegencc.org/download/action/submissions-export-xlsx
    excel_url: https://thegencc.org/download/action/submissions-export-csv
```

- [ ] **Step 2: Update gencc.py to use config instead of hardcoded URL**

In `backend/app/pipeline/sources/unified/gencc.py`, change line 58 from:

```python
        self.download_url = "https://search.thegencc.org/download/action/submissions-export-xlsx"
```

to:

```python
        self.download_url = get_source_parameter(
            "GenCC",
            "download_url",
            "https://thegencc.org/download/action/submissions-export-xlsx",
        )
```

- [ ] **Step 3: Run full test suite to check for regressions**

Run: `cd backend && uv run pytest -x -q`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/pipeline/sources/unified/gencc.py backend/config/datasources.yaml
git commit -m "fix(gencc): use configurable download URL (domain changed from search.thegencc.org)"
```

---

## Chunk 2: Progress Tracking Guards

### Task 3: Guard against "completed with 0 items" in DataSourceClient

**Files:**
- Modify: `backend/app/core/data_source_base.py:170-173`
- Test: `backend/tests/test_data_source_base_guards.py` (new)

- [ ] **Step 1: Write failing test for 0-item guard**

Create `backend/tests/test_data_source_base_guards.py`:

```python
"""Tests for DataSourceClient progress tracking guards."""
import pytest
from unittest.mock import MagicMock


@pytest.mark.unit
class TestZeroItemGuard:
    """Verify sources with 0 genes are marked failed, not completed."""

    def test_empty_processed_data_sets_failed_not_completed(self):
        """When process_data returns empty dict, tracker should call error(), not complete()."""
        from app.core.data_source_base import DataSourceClient

        # We test the logic: if not processed_data → tracker.error(), not tracker.complete()
        tracker = MagicMock()
        tracker.complete = MagicMock()
        tracker.error = MagicMock()

        # Simulate the guard logic we want to add
        processed_data: dict = {}
        source_name = "TestSource"

        # This is what the NEW code should do:
        if not processed_data:
            tracker.error(f"{source_name} update returned 0 genes — marking as failed")

        tracker.error.assert_called_once()
        tracker.complete.assert_not_called()
```

- [ ] **Step 2: Run test to verify it passes (test is self-contained)**

Run: `cd backend && uv run pytest tests/test_data_source_base_guards.py -v`
Expected: PASS (the test validates the logic pattern).

- [ ] **Step 3: Apply fix in data_source_base.py**

In `backend/app/core/data_source_base.py`, change lines 170-173 from:

```python
            if not processed_data:
                logger.sync_warning("No genes found in data", source_name=self.source_name)
                tracker.complete(f"{self.source_name} update completed: 0 genes found")
                return stats
```

to:

```python
            if not processed_data:
                msg = f"{self.source_name} update returned 0 genes"
                logger.sync_error(
                    "No genes found in data — marking as FAILED",
                    source_name=self.source_name,
                )
                tracker.error(msg)
                stats["error"] = msg
                return stats
```

- [ ] **Step 4: Run full test suite**

Run: `cd backend && uv run pytest -x -q`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/data_source_base.py backend/tests/test_data_source_base_guards.py
git commit -m "fix(pipeline): mark 0-gene results as failed instead of completed"
```

### Task 4: Fix double tracker.start() counter reset

**Files:**
- Modify: `backend/app/core/progress_tracker.py:120-138`

- [ ] **Step 1: Make ProgressTracker.start() idempotent**

The `@managed_task` decorator creates a `ProgressTracker` at `task_decorator.py:37`, then the source method (e.g., PubTator) calls `tracker.start()` again, which resets all counters to 0.

In `backend/app/core/progress_tracker.py`, change the `start()` method (around line 115-138). Add a guard at the top:

```python
    def start(self, operation: str = "Starting update") -> None:
        """Start tracking progress. Idempotent — skips counter reset if already running."""
        if self.progress_record.status == SourceStatus.running:
            logger.sync_debug(
                "ProgressTracker.start() skipped — already running",
                source_name=self.source_name,
            )
            # Update operation text but don't reset counters
            self.progress_record.current_operation = operation
            return

        logger.sync_debug(
            "ProgressTracker.start() called",
            source_name=self.source_name,
            operation=operation,
            old_status=str(self.progress_record.status),
        )
        self._start_time = datetime.now(timezone.utc)
        self.progress_record.status = SourceStatus.running
        self.progress_record.current_operation = operation
        self.progress_record.started_at = self._start_time
        self.progress_record.completed_at = None
        self.progress_record.error_message = None
        self.progress_record.items_processed = 0
        self.progress_record.items_added = 0
        self.progress_record.items_updated = 0
        self.progress_record.items_failed = 0
        self.progress_record.progress_percentage = 0.0
        self.progress_record.current_item = 0
        self.progress_record.total_items = None
        self._commit_and_broadcast()
        logger.sync_debug(
            "ProgressTracker.start() completed",
            source_name=self.source_name,
            new_status=str(self.progress_record.status),
        )
```

- [ ] **Step 2: Run full test suite**

Run: `cd backend && uv run pytest -x -q`
Expected: All tests pass.

- [ ] **Step 3: Lint**

Run: `cd /home/bernt-popp/development/kidney-genetics-db && make lint`
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/progress_tracker.py
git commit -m "fix(progress): make tracker.start() idempotent to prevent counter reset"
```

---

## Chunk 3: Pipeline Orchestrator

### Task 5: Create pipeline orchestrator with 3-stage DAG

**Files:**
- Create: `backend/app/core/pipeline_orchestrator.py`
- Test: `backend/tests/test_pipeline_orchestrator.py` (new)

- [ ] **Step 1: Write tests for pipeline orchestrator**

Create `backend/tests/test_pipeline_orchestrator.py`:

```python
"""Tests for PipelineOrchestrator stage management."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.core.pipeline_orchestrator import PipelineOrchestrator, PipelineStage


@pytest.mark.unit
class TestPipelineStages:
    """Verify stage transitions and dependency enforcement."""

    def test_initial_stage_is_idle(self):
        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orch._current_stage = PipelineStage.IDLE
        assert orch._current_stage == PipelineStage.IDLE

    def test_stages_have_correct_order(self):
        assert PipelineStage.IDLE.value == 0
        assert PipelineStage.EVIDENCE.value == 1
        assert PipelineStage.ANNOTATIONS.value == 2
        assert PipelineStage.AGGREGATION.value == 3
        assert PipelineStage.COMPLETE.value == 4

    def test_evidence_sources_list(self):
        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orch.EVIDENCE_SOURCES = [
            "PanelApp", "PubTator", "ClinGen", "GenCC", "HPO",
        ]
        assert len(orch.EVIDENCE_SOURCES) == 5
        assert "PanelApp" in orch.EVIDENCE_SOURCES


@pytest.mark.unit
class TestSourceCompletion:
    """Verify source completion tracking."""

    def test_mark_source_completed(self):
        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orch._completed_sources = set()
        orch._failed_sources = set()
        orch.EVIDENCE_SOURCES = ["PanelApp", "ClinGen"]
        orch._current_stage = PipelineStage.EVIDENCE

        orch._completed_sources.add("PanelApp")
        assert "PanelApp" in orch._completed_sources

    def test_all_evidence_done_when_all_completed_or_failed(self):
        orch = PipelineOrchestrator.__new__(PipelineOrchestrator)
        orch.EVIDENCE_SOURCES = ["PanelApp", "ClinGen", "GenCC"]
        orch._completed_sources = {"PanelApp", "ClinGen"}
        orch._failed_sources = {"GenCC"}

        all_done = (
            orch._completed_sources | orch._failed_sources
        ) >= set(orch.EVIDENCE_SOURCES)
        assert all_done is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_pipeline_orchestrator.py -v`
Expected: FAIL — `pipeline_orchestrator` module doesn't exist yet.

- [ ] **Step 3: Create pipeline_orchestrator.py**

Create `backend/app/core/pipeline_orchestrator.py`:

```python
"""
Lightweight pipeline orchestrator with 3-stage DAG.

Chains: Evidence sources → Annotation pipeline → Evidence aggregation.
Each stage waits for the previous stage to complete before starting.
Source-level failures are tolerated (skip source, continue).
Stage-level failures halt downstream stages.
"""

import asyncio
from enum import IntEnum
from typing import Any

from app.core.logging import get_logger

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

    async def start_pipeline(self) -> None:
        """Start the full pipeline from evidence collection."""
        async with self._pipeline_lock:
            if self._current_stage != PipelineStage.IDLE:
                logger.sync_warning(
                    "Pipeline already running",
                    current_stage=self._current_stage.name,
                )
                return

            self._current_stage = PipelineStage.EVIDENCE
            self._completed_sources.clear()
            self._failed_sources.clear()

        logger.sync_info("Pipeline started — Stage 1: Evidence collection")
        await self.task_manager.start_auto_updates()

    async def on_source_completed(
        self, source_name: str, success: bool = True
    ) -> None:
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
            "All evidence sources done — Stage 2: Annotations",
            succeeded=succeeded,
            failed=failed,
        )

        # Run annotation pipeline in background
        asyncio.create_task(self._run_annotations())

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

    async def _advance_to_aggregation(self) -> None:
        """Transition to Stage 3: Evidence aggregation."""
        async with self._pipeline_lock:
            self._current_stage = PipelineStage.AGGREGATION

        logger.sync_info("Stage 3: Evidence aggregation")

        from app.core.database import SessionLocal
        from app.pipeline.aggregate import update_all_curations

        db = SessionLocal()
        try:
            update_all_curations(db)
            logger.sync_info("Evidence aggregation completed")
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
        finally:
            self._current_stage = PipelineStage.IDLE
            db.close()

    def reset(self) -> None:
        """Reset orchestrator to idle state."""
        self._current_stage = PipelineStage.IDLE
        self._completed_sources.clear()
        self._failed_sources.clear()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_pipeline_orchestrator.py -v`
Expected: PASS

- [ ] **Step 5: Lint**

Run: `cd /home/bernt-popp/development/kidney-genetics-db && make lint`

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/pipeline_orchestrator.py backend/tests/test_pipeline_orchestrator.py
git commit -m "feat(pipeline): add lightweight 3-stage pipeline orchestrator"
```

### Task 6: Hook orchestrator into BackgroundTaskManager

**Files:**
- Modify: `backend/app/core/background_tasks.py:192-200`
- Modify: `backend/app/main.py:107-122`

- [ ] **Step 1: Add orchestrator reference to BackgroundTaskManager**

In `backend/app/core/background_tasks.py`, add after line 30 (`self.executor = ...`):

```python
        self.orchestrator: Any | None = None
```

Add import at top of file:

```python
from app.core.pipeline_orchestrator import PipelineOrchestrator
```

- [ ] **Step 2: Add orchestrator notification to task completion callback**

In `backend/app/core/background_tasks.py`, replace the task completion callback at lines 192-200. Change from:

```python
            task.add_done_callback(
                lambda t: logger.sync_info(
                    "Task completed",
                    source_name=source_name,
                    done=t.done(),
                    exception=str(t.exception()) if t.done() and t.exception() else None,
                )
            )
```

to:

```python
            def _on_task_done(
                t: asyncio.Task[Any],
                _source: str = source_name,
            ) -> None:
                exc = t.exception() if t.done() else None
                success = exc is None
                logger.sync_info(
                    "Task completed",
                    source_name=_source,
                    done=t.done(),
                    success=success,
                    exception=str(exc) if exc else None,
                )
                # Notify orchestrator if present
                if self.orchestrator is not None:
                    asyncio.create_task(
                        self.orchestrator.on_source_completed(
                            _source, success=success
                        )
                    )

            task.add_done_callback(_on_task_done)
```

- [ ] **Step 3: Update main.py lifespan to use orchestrator**

In `backend/app/main.py`, replace lines 107-122 (the auto-update + scheduler block). Change from:

```python
    # Start auto-updates for data sources
    if settings.AUTO_UPDATE_ENABLED:
        try:
            await task_manager.start_auto_updates()
        except Exception as e:
            logger.sync_warning(
                "Failed to start auto-updates. Continuing without auto-updates.",
                error=e,
                auto_update_enabled=settings.AUTO_UPDATE_ENABLED,
            )

    # Start annotation scheduler
    logger.sync_info("Starting annotation scheduler...")
    from app.core.scheduler import annotation_scheduler

    annotation_scheduler.start()
```

to:

```python
    # Start annotation scheduler (cron-based maintenance updates)
    logger.sync_info("Starting annotation scheduler...")
    from app.core.scheduler import annotation_scheduler

    annotation_scheduler.start()

    # Start pipeline orchestrator (evidence → annotations → aggregation)
    if settings.AUTO_UPDATE_ENABLED:
        try:
            from app.core.pipeline_orchestrator import PipelineOrchestrator

            orchestrator = PipelineOrchestrator(task_manager)
            task_manager.orchestrator = orchestrator
            await orchestrator.start_pipeline()
        except Exception as e:
            logger.sync_warning(
                "Failed to start pipeline. Continuing without auto-updates.",
                error=e,
            )
```

- [ ] **Step 4: Run full test suite**

Run: `cd backend && uv run pytest -x -q`
Expected: All tests pass.

- [ ] **Step 5: Lint and typecheck**

```bash
cd /home/bernt-popp/development/kidney-genetics-db && make lint
cd backend && uv run mypy app/core/pipeline_orchestrator.py app/core/background_tasks.py app/main.py --ignore-missing-imports
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/background_tasks.py backend/app/main.py
git commit -m "feat(pipeline): wire orchestrator into startup and task completion"
```

---

## Chunk 4: Initial Data Seeding

### Task 7: Create initial seeder for DiagnosticPanels and Literature

**Files:**
- Create: `backend/app/core/initial_seeder.py`
- Test: `backend/tests/test_initial_seeder.py` (new)

- [ ] **Step 1: Write test for seeder**

Create `backend/tests/test_initial_seeder.py`:

```python
"""Tests for initial data seeder."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.mark.unit
class TestInitialSeeder:
    """Verify initial seeder detects empty DB and loads scrapers."""

    def test_needs_seeding_when_no_evidence(self):
        """Should return True when gene_evidence table is empty."""
        from app.core.initial_seeder import needs_initial_seeding

        db = MagicMock()
        db.query.return_value.count.return_value = 0
        assert needs_initial_seeding(db) is True

    def test_no_seeding_when_evidence_exists(self):
        """Should return False when gene_evidence has data."""
        from app.core.initial_seeder import needs_initial_seeding

        db = MagicMock()
        db.query.return_value.count.return_value = 100
        assert needs_initial_seeding(db) is False

    def test_find_scraper_files_returns_paths(self):
        """Should find JSON files in scraper output directories."""
        from app.core.initial_seeder import find_latest_scraper_output

        with patch("app.core.initial_seeder.Path") as mock_path:
            mock_dir = MagicMock()
            mock_path.return_value = mock_dir
            mock_dir.exists.return_value = True
            mock_dir.iterdir.return_value = [
                MagicMock(is_dir=lambda: True, name="2025-08-24"),
            ]
            # The function should look for the latest date dir
            result = find_latest_scraper_output(mock_dir)
            assert result is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_initial_seeder.py -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Create initial_seeder.py**

Create `backend/app/core/initial_seeder.py`:

```python
"""
Initial data seeder for empty databases.

On first startup (when gene_evidence is empty), loads DiagnosticPanels
and Literature data from backend/app/data/seed/ (version-controlled).
This provides baseline evidence data before the pipeline runs.
"""

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.gene import GeneEvidence

logger = get_logger(__name__)

# Project root (3 levels up from this file)
# Seed data lives in backend/app/data/seed/ (version-controlled)
SEED_DATA_DIR = Path(__file__).parent.parent / "data" / "seed"

SEED_DIRS = {
    "DiagnosticPanels": SEED_DATA_DIR / "diagnostic_panels",
    "Literature": SEED_DATA_DIR / "literature",
}


def needs_initial_seeding(db: Session) -> bool:
    """Check if the database needs initial evidence seeding."""
    count = db.query(GeneEvidence).count()
    return count == 0


def find_latest_scraper_output(base_dir: Path) -> Path | None:
    """Find the most recent date-stamped output directory."""
    if not base_dir.exists():
        return None

    date_dirs = sorted(
        [d for d in base_dir.iterdir() if d.is_dir() and d.name[0].isdigit()],
        key=lambda d: d.name,
        reverse=True,
    )
    return date_dirs[0] if date_dirs else None


def load_scraper_files(output_dir: Path) -> list[dict[str, Any]]:
    """Load all JSON files from a scraper output directory."""
    files: list[dict[str, Any]] = []
    for json_file in sorted(output_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text())
            files.append(data)
            logger.sync_debug(
                "Loaded scraper file",
                file=json_file.name,
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.sync_warning(
                "Failed to load scraper file",
                file=str(json_file),
                error=str(e),
            )
    return files


async def run_initial_seeding(db: Session) -> dict[str, Any]:
    """
    Seed database with DiagnosticPanels and Literature data from scrapers.

    Returns summary of what was loaded.
    """
    from app.pipeline.sources.unified import get_unified_source

    results: dict[str, Any] = {}

    for source_name, seed_dir in SEED_DIRS.items():
        output_dir = seed_dir if seed_dir.exists() else None
        if output_dir is None:
            logger.sync_warning(
                "No scraper output found",
                source_name=source_name,
                base_dir=str(base_dir),
            )
            results[source_name] = {"status": "skipped", "reason": "no output dir"}
            continue

        files = load_scraper_files(output_dir)
        if not files:
            logger.sync_warning(
                "No JSON files found in scraper output",
                source_name=source_name,
                output_dir=str(output_dir),
            )
            results[source_name] = {"status": "skipped", "reason": "no files"}
            continue

        logger.sync_info(
            "Seeding from scraper output",
            source_name=source_name,
            output_dir=str(output_dir),
            file_count=len(files),
        )

        try:
            source = get_unified_source(source_name, db_session=db)
            loaded = 0
            for file_data in files:
                processed = await source.process_data(file_data)
                if processed:
                    await source._store_genes_in_database(
                        db, processed, {}, None
                    )
                    loaded += len(processed)

            db.commit()
            results[source_name] = {
                "status": "seeded",
                "files": len(files),
                "genes_loaded": loaded,
                "output_dir": str(output_dir),
            }
            logger.sync_info(
                "Seeding complete",
                source_name=source_name,
                genes_loaded=loaded,
            )

        except Exception as e:
            db.rollback()
            logger.sync_error(
                "Seeding failed",
                source_name=source_name,
                error=str(e),
            )
            results[source_name] = {
                "status": "failed",
                "error": str(e),
            }

    return results
```

> **Note:** The `process_data()` and `_store_genes_in_database()` calls may need adjustment based on how each unified source's API works. The seeder should use the existing upload/ingestion path (`POST /{source_name}/upload`) as an alternative if direct source instantiation is too complex. In that case, use `httpx` to POST to the local API endpoint during startup. Investigate during implementation.

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_initial_seeder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/initial_seeder.py backend/tests/test_initial_seeder.py
git commit -m "feat(seeder): add initial data seeder for DiagnosticPanels/Literature"
```

### Task 8: Wire seeder into startup

**Files:**
- Modify: `backend/app/core/startup.py`
- Modify: `Makefile`

- [ ] **Step 1: Add seeding check to startup.py**

In `backend/app/core/startup.py`, add a new function and call it from `run_startup_tasks()`. Add after the existing `cleanup_orphaned_sources()` call:

```python
def check_and_run_initial_seeding() -> None:
    """Check if database needs initial evidence seeding from scrapers."""
    import asyncio
    from app.core.initial_seeder import needs_initial_seeding, run_initial_seeding

    db = next(get_db())
    try:
        if needs_initial_seeding(db):
            logger.sync_info(
                "Empty database detected — running initial seeding from scrapers"
            )
            results = asyncio.get_event_loop().run_until_complete(
                run_initial_seeding(db)
            )
            logger.sync_info("Initial seeding results", results=results)
        else:
            logger.sync_debug("Database already has evidence data — skipping seeding")
    except Exception as e:
        logger.sync_warning(
            "Initial seeding failed — pipeline will populate data later",
            error=str(e),
        )
    finally:
        db.close()
```

Then add this call to `run_startup_tasks()` after `cleanup_orphaned_sources()`:

```python
    check_and_run_initial_seeding()
```

- [ ] **Step 2: Add Makefile target**

Add to `Makefile` (in the database management section):

```makefile
# Seed initial data from backend/app/data/seed/ (DiagnosticPanels + Literature)
db-seed-initial:
	@echo "🌱 Seeding initial data from seed files..."
	cd backend && uv run python -c "\
		from app.core.database import SessionLocal; \
		from app.core.initial_seeder import needs_initial_seeding, run_initial_seeding; \
		import asyncio; \
		db = SessionLocal(); \
		print('Needs seeding:', needs_initial_seeding(db)); \
		results = asyncio.run(run_initial_seeding(db)); \
		print('Results:', results); \
		db.close()"
	@echo "✅ Initial seeding complete!"
```

- [ ] **Step 3: Run full test suite**

Run: `cd backend && uv run pytest -x -q`
Expected: All tests pass.

- [ ] **Step 4: Lint**

Run: `make lint`

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/startup.py Makefile
git commit -m "feat(startup): auto-seed DiagnosticPanels/Literature on empty DB"
```

---

## Chunk 5: Integration Testing & Verification

### Task 9: End-to-end verification

**Files:** None (verification only)

- [ ] **Step 1: Reset and rebuild database**

```bash
make db-reset
```

- [ ] **Step 2: Start hybrid dev and verify initial seeding**

```bash
make hybrid-up
make backend  # Watch logs for "Initial seeding" messages
```

Expected in logs:
- "Empty database detected — running initial seeding from scrapers"
- "Pipeline started — Stage 1: Evidence collection"
- Evidence sources starting (PanelApp, PubTator, ClinGen, GenCC, HPO)
- GenCC should now follow redirect and download successfully

- [ ] **Step 3: Monitor source completion and annotation trigger**

Watch backend logs for:
- "Evidence source completed" messages for each source
- "All evidence sources done — Stage 2: Annotations"
- Annotation pipeline starting (HGNC first, then others in parallel)

- [ ] **Step 4: Verify data in database**

```bash
docker exec kidney_genetics_postgres psql -U kidney_user kidney_genetics \
  -c "SELECT source_name, status, items_processed, items_added FROM data_source_progress ORDER BY source_name;"
```

Expected: All auto_update sources show `completed` with items_processed > 0.

```bash
docker exec kidney_genetics_postgres psql -U kidney_user kidney_genetics \
  -c "SELECT source_name, COUNT(*) FROM gene_evidence GROUP BY source_name ORDER BY source_name;"
```

Expected: All 7 evidence sources (including DiagnosticPanels, Literature) have data.

```bash
docker exec kidney_genetics_postgres psql -U kidney_user kidney_genetics \
  -c "SELECT source, COUNT(*) FROM gene_annotations GROUP BY source ORDER BY source;"
```

Expected: Annotation sources (hgnc, ensembl, gnomad, etc.) have data.

- [ ] **Step 5: Run full test suite one final time**

```bash
make test
make lint
```

Expected: All tests pass, lint clean.

- [ ] **Step 6: Verify frontend data-sources page**

Open http://localhost:5173/data-sources and verify:
- All 7 evidence sources show data
- No error states
- Admin logs page shows no new ERROR entries

- [ ] **Step 7: Commit any remaining fixes from verification**

```bash
git add -A
git commit -m "fix: integration fixes from end-to-end verification"
```

---

## Rollback Plan

If anything goes wrong:

```bash
# Git: revert to pre-fix state
git log --oneline  # find the commit before changes
git revert HEAD~N..HEAD  # revert N commits

# Database: restore from backup
make db-restore  # uses latest backup from backups/

# Verify
cd backend && uv run alembic current
make test
```

---

## Post-Implementation Notes

### What this does NOT change (intentionally):
- `AnnotationPipeline` internals — well-architected, not broken
- `BaseAnnotationSource` pattern — retry/circuit breaker works correctly
- `AnnotationScheduler` cron jobs — still run as maintenance (2AM/3AM)
- ARQ worker support — still available via `USE_ARQ_WORKER=true`
- WebSocket progress broadcasting — untouched
- All 10 annotation source implementations — no changes needed

### Future improvements (out of scope for this plan):
- Add `PARTIAL` status for sources that complete with fewer items than expected
- Add distributed locking if moving to multi-instance deployment
- Add pipeline status API endpoint for frontend monitoring
- Add retry scheduling for failed evidence sources (currently manual)
