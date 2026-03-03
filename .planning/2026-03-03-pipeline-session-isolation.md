# Pipeline Session Isolation Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix cascading SQLAlchemy session errors during parallel annotation pipeline updates by giving each concurrent source its own database session.

**Architecture:** The `AnnotationPipeline` currently passes a single `Session` to all parallel source updates running under `asyncio.gather`. SQLAlchemy sessions are not thread-safe or concurrency-safe — concurrent commits on a shared session poison it for all tasks. The fix creates a fresh `SessionLocal()` per source inside `_update_sources_parallel`, keeps `self.db` for sequential orchestration only, and adds a fresh session for materialized view refreshes.

**Tech Stack:** Python 3.13, SQLAlchemy 2.x (sync ORM), FastAPI, PostgreSQL, pytest

---

### Task 1: Write failing test — parallel sources get separate sessions

**Files:**
- Create: `backend/tests/pipeline/test_session_isolation.py`

**Step 1: Write the failing test**

```python
"""Tests for pipeline session isolation during parallel source updates."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.pipeline.annotation_pipeline import AnnotationPipeline


@pytest.mark.unit
class TestParallelSessionIsolation:
    """Verify each parallel source gets its own database session."""

    def _make_pipeline(self, db_session: Session) -> AnnotationPipeline:
        return AnnotationPipeline(db_session)

    @pytest.mark.asyncio
    async def test_parallel_sources_get_separate_sessions(self, db_session: Session):
        """Each parallel source must receive a unique SessionLocal() instance."""
        pipeline = self._make_pipeline(db_session)

        created_sessions: list[Session] = []

        # Patch SessionLocal to track every session created
        real_session_local = None

        def tracking_session_local():
            from app.core.database import SessionLocal as RealSessionLocal

            sess = RealSessionLocal()
            created_sessions.append(sess)
            return sess

        # Patch _update_source_with_recovery to be a no-op that records its db arg
        source_sessions: list[int] = []

        async def fake_update(source_name, gene_ids, force, source_db):
            source_sessions.append(id(source_db))
            return {"successful": 0, "failed": 0, "total": 0}

        with (
            patch(
                "app.pipeline.annotation_pipeline.SessionLocal",
                side_effect=tracking_session_local,
            ),
            patch.object(
                pipeline,
                "_update_source_with_session",
                side_effect=fake_update,
            ),
        ):
            await pipeline._update_sources_parallel(
                ["gnomad", "gtex", "clinvar"], gene_ids=[1, 2, 3], force=False
            )

        # Each source must have received a different session object
        assert len(source_sessions) == 3, f"Expected 3 source sessions, got {len(source_sessions)}"
        assert len(set(source_sessions)) == 3, "Sources must NOT share session objects"

        # All tracking sessions must have been closed
        for sess in created_sessions:
            assert not sess.is_active, "Source session was not closed after use"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/pipeline/test_session_isolation.py::TestParallelSessionIsolation::test_parallel_sources_get_separate_sessions -v`
Expected: FAIL — `_update_source_with_session` does not exist yet, and `SessionLocal` is not imported in `annotation_pipeline.py`.

---

### Task 2: Write failing test — source failure does not cascade

**Files:**
- Modify: `backend/tests/pipeline/test_session_isolation.py`

**Step 1: Append the failing test**

Add to the `TestParallelSessionIsolation` class:

```python
    @pytest.mark.asyncio
    async def test_source_failure_does_not_cascade(self, db_session: Session):
        """One source raising an exception must not affect other sources."""
        pipeline = self._make_pipeline(db_session)

        call_log: list[str] = []

        async def fake_update(source_name, gene_ids, force, source_db):
            call_log.append(source_name)
            if source_name == "gtex":
                raise RuntimeError("GTEx API timeout")
            return {"successful": 1, "failed": 0, "total": 1}

        with (
            patch("app.pipeline.annotation_pipeline.SessionLocal"),
            patch.object(
                pipeline,
                "_update_source_with_session",
                side_effect=fake_update,
            ),
        ):
            results = await pipeline._update_sources_parallel(
                ["gnomad", "gtex", "clinvar"], gene_ids=[1], force=False
            )

        # All three sources must have been attempted
        assert set(call_log) == {"gnomad", "gtex", "clinvar"}

        # gnomad and clinvar succeed; gtex has an error
        assert "error" not in results.get("gnomad", {}), "gnomad should succeed"
        assert "error" not in results.get("clinvar", {}), "clinvar should succeed"
        assert "error" in results.get("gtex", {}), "gtex should report error"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/pipeline/test_session_isolation.py::TestParallelSessionIsolation::test_source_failure_does_not_cascade -v`
Expected: FAIL — same reason (missing `_update_source_with_session` and `SessionLocal` import).

---

### Task 3: Write failing test — session cleanup on error

**Files:**
- Modify: `backend/tests/pipeline/test_session_isolation.py`

**Step 1: Append the failing test**

Add to the `TestParallelSessionIsolation` class:

```python
    @pytest.mark.asyncio
    async def test_session_cleanup_on_source_error(self, db_session: Session):
        """Source sessions must be rolled back and closed even when the source raises."""
        pipeline = self._make_pipeline(db_session)

        mock_sessions: list[MagicMock] = []

        def tracking_session_local():
            mock_sess = MagicMock(spec=Session)
            mock_sessions.append(mock_sess)
            return mock_sess

        async def exploding_update(source_name, gene_ids, force, source_db):
            raise ValueError("Simulated source crash")

        with (
            patch(
                "app.pipeline.annotation_pipeline.SessionLocal",
                side_effect=tracking_session_local,
            ),
            patch.object(
                pipeline,
                "_update_source_with_session",
                side_effect=exploding_update,
            ),
        ):
            results = await pipeline._update_sources_parallel(
                ["gnomad"], gene_ids=[1], force=False
            )

        assert len(mock_sessions) == 1
        mock_sessions[0].rollback.assert_called_once()
        mock_sessions[0].close.assert_called_once()
        assert "error" in results.get("gnomad", {})
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/pipeline/test_session_isolation.py::TestParallelSessionIsolation::test_session_cleanup_on_source_error -v`
Expected: FAIL

---

### Task 4: Write failing test — materialized view refresh uses fresh session

**Files:**
- Modify: `backend/tests/pipeline/test_session_isolation.py`

**Step 1: Append the failing test**

Add a new test class:

```python
@pytest.mark.unit
class TestMaterializedViewRefresh:
    """Verify materialized view refresh uses a dedicated session."""

    @pytest.mark.asyncio
    async def test_refresh_uses_fresh_session(self, db_session: Session):
        """_refresh_materialized_view must create its own session, not reuse self.db."""
        pipeline = AnnotationPipeline(db_session)

        created_sessions: list[MagicMock] = []

        def tracking_session_local():
            mock_sess = MagicMock(spec=Session)
            mock_sess.execute = MagicMock()
            mock_sess.commit = MagicMock()
            created_sessions.append(mock_sess)
            return mock_sess

        with patch(
            "app.pipeline.annotation_pipeline.SessionLocal",
            side_effect=tracking_session_local,
        ):
            await pipeline._refresh_materialized_view()

        # Must have created at least one fresh session
        assert len(created_sessions) >= 1, "Expected a fresh session for view refresh"
        # The fresh session must have been closed
        for sess in created_sessions:
            sess.close.assert_called_once()

        # self.db must NOT have been used for the refresh
        # (We can't easily assert this on a real session, but the mock-based
        # approach ensures the new code path is exercised)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/pipeline/test_session_isolation.py::TestMaterializedViewRefresh::test_refresh_uses_fresh_session -v`
Expected: FAIL — current `_refresh_materialized_view` uses `self.db`, not `SessionLocal`.

---

### Task 5: Implement session-per-source in `_update_sources_parallel`

**Files:**
- Modify: `backend/app/pipeline/annotation_pipeline.py:1-31` (imports)
- Modify: `backend/app/pipeline/annotation_pipeline.py:561-608` (`_update_sources_parallel`)

**Step 1: Add `SessionLocal` import**

At `annotation_pipeline.py` line 12 (after `from sqlalchemy.orm import Session`), add:

```python
from app.core.database import SessionLocal
```

**Step 2: Rewrite `_update_sources_parallel` to create session-per-source**

Replace the method body (lines 561-608) with:

```python
    async def _update_sources_parallel(
        self, sources: list[str], gene_ids: list[int], force: bool = False
    ) -> dict[str, Any]:
        """Update multiple sources with controlled parallelism.

        Each source gets its own dedicated SQLAlchemy session to prevent
        concurrent-commit errors on a shared session.  The orchestration
        session (self.db) is NOT used inside parallel tasks.

        Args:
            sources: List of source names to update
            gene_ids: List of gene IDs (not Gene objects) to avoid session conflicts
            force: Whether to force update existing annotations
        """
        results: dict[str, Any] = {}

        # Limit concurrent sources to respect API limits
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent sources

        async def rate_limited_update(source_name: str) -> tuple[str, dict]:
            """Update single source with its own isolated session."""
            async with semaphore:
                source_db = SessionLocal()
                try:
                    # Health-check on the NEW session
                    source_db.execute(text("SELECT 1"))
                    source_db.commit()

                    logger.sync_info(f"Starting parallel update for {source_name}")
                    result = await self._update_source_with_session(
                        source_name, gene_ids, force, source_db
                    )
                    return (source_name, result)
                except Exception as e:
                    source_db.rollback()
                    logger.sync_error(f"Error in parallel update for {source_name}: {e}")
                    return (source_name, {"error": str(e)})
                finally:
                    source_db.close()

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
```

**Step 3: Run tests to check progress**

Run: `cd backend && uv run pytest tests/pipeline/test_session_isolation.py -v`
Expected: Tests that depend on `_update_source_with_session` still fail (method not yet created), but import errors are resolved.

---

### Task 6: Extract `_update_source_with_session` method

**Files:**
- Modify: `backend/app/pipeline/annotation_pipeline.py:610-791` (`_update_source_with_recovery`)

**Step 1: Create `_update_source_with_session` that accepts an explicit `db` parameter**

Add this new method immediately after `_update_sources_parallel`. It is essentially `_update_source_with_recovery` but takes an explicit `db` session parameter instead of using `self.db`.

```python
    async def _update_source_with_session(
        self,
        source_name: str,
        gene_ids: list[int],
        force: bool,
        source_db: Session,
    ) -> dict[str, Any]:
        """Run a single source update with a dedicated session.

        Identical logic to ``_update_source_with_recovery`` but uses the
        provided ``source_db`` session instead of ``self.db``, ensuring
        full isolation from other concurrent source updates.

        Args:
            source_name: Name of the annotation source to update
            gene_ids: List of gene IDs
            force: Whether to force update existing annotations
            source_db: Dedicated session for this source (caller manages lifecycle)
        """
        logger.sync_info(
            f"Starting batch update for {source_name}",
            source_name=source_name,
            gene_count=len(gene_ids),
            force=force,
        )

        # Re-fetch genes using the source-local session
        genes = source_db.query(Gene).filter(Gene.id.in_(gene_ids)).all()
        source_db.commit()  # Release read lock before long fetch

        if len(genes) != len(gene_ids):
            logger.sync_warning(
                f"Gene count mismatch: requested {len(gene_ids)}, found {len(genes)}"
            )

        source_class = self.sources[source_name]
        source = source_class(source_db)  # Source gets the dedicated session
        source.batch_mode = True

        total_genes = len(genes)
        successful = 0
        failed = 0
        failed_genes: list[Gene] = []

        # Phase 1: Batch fetch
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

        # Phase 2: Bulk upsert using the source-local session
        if batch_data:
            if self.progress_tracker:
                self.progress_tracker.update(
                    current_item=0,
                    operation=f"Writing {source_name}: {len(batch_data)} annotations (bulk)",
                )

            upsert_count = self._bulk_upsert_annotations_with_session(
                source_name, source.version, batch_data, source_db
            )
            successful = upsert_count
            logger.sync_info(
                f"Bulk upsert complete for {source_name}",
                upserted=upsert_count,
            )

        source_db.commit()  # Release between phases

        # Phase 3: Per-gene fallback
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
                            f"Updating {source_name}: fallback {i}/{len(missed_genes)} genes"
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
                source_db.commit()
            except Exception as e:
                logger.sync_warning(f"Fallback commit failed: {e}")
                source_db.rollback()

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

        # Clear caches in background using a dedicated session
        try:
            from concurrent.futures import ThreadPoolExecutor

            from app.core.cache_service import get_cache_service

            if not hasattr(self, "_executor"):
                self._executor = ThreadPoolExecutor(max_workers=2)

            def clear_cache_sync() -> None:
                thread_db = SessionLocal()
                try:
                    cache_service = get_cache_service(thread_db)
                    if cache_service:
                        cache_service.clear_namespace_sync(source_name.lower())
                        cache_service.clear_namespace_sync("annotations")
                        logger.sync_debug(f"Cleared cache for {source_name}")
                finally:
                    thread_db.close()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, clear_cache_sync)
        except Exception as e:
            logger.sync_debug(f"Cache clear failed: {e}")

        # Update source metadata using the source-local session
        source_record = source.source_record
        source_record.last_update = datetime.utcnow()
        source_record.next_update = datetime.utcnow() + timedelta(days=source.cache_ttl_days)
        source_db.commit()

        return {
            "successful": successful,
            "failed": failed,
            "total": total_genes,
            "recovery_attempted": len(failed_genes) > 0,
        }
```

**Step 2: Run tests to check progress**

Run: `cd backend && uv run pytest tests/pipeline/test_session_isolation.py -v`
Expected: Session isolation tests pass; bulk upsert test still fails (needs `_bulk_upsert_annotations_with_session`).

---

### Task 7: Extract `_bulk_upsert_annotations_with_session`

**Files:**
- Modify: `backend/app/pipeline/annotation_pipeline.py:793-860` (after `_bulk_upsert_annotations`)

**Step 1: Add session-parameterized bulk upsert**

Add this method immediately after `_bulk_upsert_annotations`:

```python
    def _bulk_upsert_annotations_with_session(
        self,
        source_name: str,
        version: str | None,
        batch_data: dict[int, dict[str, Any]],
        db: Session,
    ) -> int:
        """Bulk upsert using a caller-provided session.

        Identical to ``_bulk_upsert_annotations`` but uses the passed ``db``
        session instead of ``self.db``.  This keeps each parallel source's
        writes fully isolated.
        """
        if not batch_data:
            return 0

        now = datetime.utcnow()
        metadata_json = json.dumps({"retrieved_at": now.isoformat(), "batch_fetch": True})

        upserted = 0
        chunk_size = 500
        items = list(batch_data.items())

        for chunk_start in range(0, len(items), chunk_size):
            chunk = items[chunk_start : chunk_start + chunk_size]

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
                db.execute(sql, params)
                db.commit()
                upserted += len(chunk)
            except Exception as e:
                logger.sync_error(f"Bulk upsert failed for {source_name} chunk: {e}")
                db.rollback()

        return upserted
```

**Step 2: Run session isolation tests**

Run: `cd backend && uv run pytest tests/pipeline/test_session_isolation.py -v`
Expected: All 4 session isolation tests pass (except possibly the materialized view test — Task 8 handles that).

**Step 3: Commit**

```bash
git add backend/tests/pipeline/test_session_isolation.py
git add backend/app/pipeline/annotation_pipeline.py
git commit -m "$(cat <<'EOF'
feat: session-per-source isolation for parallel pipeline updates

Each parallel annotation source now gets its own SessionLocal() instance
instead of sharing self.db. This prevents cascading SQLAlchemy "prepared
state" errors when one source commits while another is executing.

Adds _update_source_with_session() and _bulk_upsert_annotations_with_session()
that accept an explicit db parameter.
EOF
)"
```

---

### Task 8: Rewrite `_refresh_materialized_view` to use fresh session

**Files:**
- Modify: `backend/app/pipeline/annotation_pipeline.py:862-898` (`_refresh_materialized_view`)

**Step 1: Rewrite the method**

Replace the entire `_refresh_materialized_view` method with:

```python
    async def _refresh_materialized_view(self) -> bool:
        """Refresh all materialized views using a dedicated session.

        Uses a fresh SessionLocal() instead of self.db to avoid inheriting
        any poisoned state from the parallel source phase.
        """
        view_db = SessionLocal()
        try:

            def refresh_sync() -> bool:
                views_to_refresh = ["gene_scores", "gene_annotations_summary"]
                all_success = True

                for view_name in views_to_refresh:
                    try:
                        view_db.execute(
                            text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}")
                        )
                        view_db.commit()
                        logger.sync_info(
                            f"Materialized view {view_name} refreshed concurrently"
                        )
                    except Exception:
                        view_db.rollback()
                        try:
                            view_db.execute(
                                text(f"REFRESH MATERIALIZED VIEW {view_name}")
                            )
                            view_db.commit()
                            logger.sync_info(
                                f"Materialized view {view_name} refreshed (non-concurrent)"
                            )
                        except Exception as e:
                            logger.sync_error(
                                f"Failed to refresh materialized view {view_name}: {e}"
                            )
                            view_db.rollback()
                            all_success = False

                return all_success

            if not hasattr(self, "_executor"):
                from concurrent.futures import ThreadPoolExecutor

                self._executor = ThreadPoolExecutor(max_workers=2)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self._executor, refresh_sync)
            return result
        except Exception as e:
            logger.sync_error(f"Materialized view refresh failed: {e}")
            try:
                view_db.rollback()
            except Exception:
                pass
            return False
        finally:
            view_db.close()
```

**Step 2: Run the materialized view test**

Run: `cd backend && uv run pytest tests/pipeline/test_session_isolation.py::TestMaterializedViewRefresh -v`
Expected: PASS

**Step 3: Run all session isolation tests**

Run: `cd backend && uv run pytest tests/pipeline/test_session_isolation.py -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add backend/app/pipeline/annotation_pipeline.py
git commit -m "$(cat <<'EOF'
fix: materialized view refresh uses fresh session

Prevents view refresh from failing when the parallel phase left
self.db in a poisoned state.
EOF
)"
```

---

### Task 9: Update HGNC phase-1 to also use `_update_source_with_session`

**Files:**
- Modify: `backend/app/pipeline/annotation_pipeline.py:192-204` (Phase 1 in `run_update`)

**Step 1: Write failing test**

Add to `test_session_isolation.py`:

```python
@pytest.mark.unit
class TestHGNCPhaseIsolation:
    """HGNC (Phase 1) should also use a dedicated session."""

    @pytest.mark.asyncio
    async def test_hgnc_uses_dedicated_session(self, db_session: Session):
        """Phase 1 HGNC must not use self.db for the actual source update."""
        pipeline = AnnotationPipeline(db_session)

        hgnc_session_ids: list[int] = []

        async def fake_update(source_name, gene_ids, force, source_db):
            hgnc_session_ids.append(id(source_db))
            return {"successful": 1, "failed": 0, "total": 1}

        # Stub out methods that we don't want to exercise
        pipeline._get_sources_to_update = lambda *a, **kw: asyncio.coroutine(
            lambda: ["hgnc"]
        )()
        pipeline._get_genes_to_update = lambda *a, **kw: asyncio.coroutine(
            lambda: [MagicMock(id=1, approved_symbol="TEST")]
        )()
        pipeline._refresh_materialized_view = lambda: asyncio.coroutine(lambda: True)()
        pipeline._save_checkpoint = lambda *a: asyncio.coroutine(lambda: None)()
        pipeline._load_checkpoint = lambda: asyncio.coroutine(lambda: None)()

        with (
            patch("app.pipeline.annotation_pipeline.SessionLocal"),
            patch.object(pipeline, "_update_source_with_session", side_effect=fake_update),
        ):
            await pipeline.run_update(sources=["hgnc"], gene_ids=[1], force=True)

        assert len(hgnc_session_ids) == 1
        assert hgnc_session_ids[0] != id(db_session), "HGNC must not use the orchestration session"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/pipeline/test_session_isolation.py::TestHGNCPhaseIsolation -v`
Expected: FAIL — HGNC currently uses `_update_source_with_recovery` with `self.db`.

**Step 3: Modify Phase 1 to use session-per-source**

In `run_update`, replace the HGNC phase (lines ~192-204) with:

```python
            # Phase 1: HGNC must complete first (provides Ensembl IDs)
            if "hgnc" in sources_to_update:
                logger.sync_info("Processing HGNC first (dependency for other sources)")
                hgnc_db = SessionLocal()
                try:
                    hgnc_results = await self._update_source_with_session(
                        "hgnc", gene_ids_to_update, force, hgnc_db
                    )
                    results["hgnc"] = hgnc_results
                    sources_completed.append("hgnc")
                    sources_to_update.remove("hgnc")
                except Exception as e:
                    hgnc_db.rollback()
                    logger.sync_error(f"HGNC update failed - critical dependency: {e}")
                    errors.append({"source": "hgnc", "error": str(e), "critical": True})
                finally:
                    hgnc_db.close()
```

**Step 4: Run test**

Run: `cd backend && uv run pytest tests/pipeline/test_session_isolation.py::TestHGNCPhaseIsolation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/pipeline/annotation_pipeline.py backend/tests/pipeline/test_session_isolation.py
git commit -m "$(cat <<'EOF'
fix: HGNC phase-1 uses dedicated session for consistency

All source updates now use session-per-source, including the
sequential HGNC dependency phase.
EOF
)"
```

---

### Task 10: Add connection pool monitoring to pipeline start/end

**Files:**
- Modify: `backend/app/pipeline/annotation_pipeline.py` (inside `run_update`)

**Step 1: Add pool status logging at pipeline start and end**

At the top of `run_update`, after the `start_time` line (~line 100), add:

```python
        # Log connection pool status at pipeline start
        try:
            from app.core.database import get_pool_status

            pool_status = get_pool_status()
            logger.sync_info(
                "Connection pool status at pipeline start",
                checked_out=pool_status.get("checked_out"),
                overflow=pool_status.get("overflow"),
                total=pool_status.get("total"),
            )
        except Exception:
            pass
```

At the end of `run_update`, just before `return summary` (~line 285), add:

```python
            # Log connection pool status at pipeline end
            try:
                pool_status = get_pool_status()
                logger.sync_info(
                    "Connection pool status at pipeline end",
                    checked_out=pool_status.get("checked_out"),
                    overflow=pool_status.get("overflow"),
                    total=pool_status.get("total"),
                )
            except Exception:
                pass
```

**Step 2: Run full test suite to confirm no regressions**

Run: `cd backend && uv run pytest tests/pipeline/ -v`
Expected: All existing pipeline tests PASS

**Step 3: Commit**

```bash
git add backend/app/pipeline/annotation_pipeline.py
git commit -m "feat: log connection pool status at pipeline start/end"
```

---

### Task 11: Run lint, typecheck, and full test suite

**Files:** None (verification only)

**Step 1: Lint**

Run: `make lint`
Expected: No errors

**Step 2: Typecheck the modified file**

Run: `cd backend && uv run mypy app/pipeline/annotation_pipeline.py --ignore-missing-imports`
Expected: No errors (or only pre-existing ones)

**Step 3: Run all tests**

Run: `make test`
Expected: All tests PASS

**Step 4: Fix any issues found and re-run until clean**

If lint/typecheck/test failures are found, fix them and re-run.

**Step 5: Final commit if any fixes were needed**

```bash
git add -u
git commit -m "style: fix lint/type issues from session isolation refactor"
```

---

### Task 12: Verify the old `_update_source_with_recovery` still works for direct callers

**Files:**
- Modify: `backend/app/pipeline/annotation_pipeline.py`

**Step 1: Verify `_update_source_with_recovery` is no longer called from parallel paths**

Search the codebase for any remaining callers:

Run: `cd backend && grep -rn "_update_source_with_recovery" app/`

If the only caller was from `_update_sources_parallel` (now removed) and from the HGNC phase (now replaced), then `_update_source_with_recovery` is dead code.

**Step 2: Decide — keep or remove**

- If no callers remain, **remove** `_update_source_with_recovery` entirely to avoid confusion.
- If external callers exist (e.g., ARQ tasks), keep it but add a deprecation comment pointing to `_update_source_with_session`.

**Step 3: Commit if changes were made**

```bash
git add backend/app/pipeline/annotation_pipeline.py
git commit -m "refactor: remove unused _update_source_with_recovery method"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `backend/app/pipeline/annotation_pipeline.py` | Import `SessionLocal`; rewrite `_update_sources_parallel` with session-per-source; add `_update_source_with_session`; add `_bulk_upsert_annotations_with_session`; rewrite `_refresh_materialized_view` with fresh session; update HGNC phase; add pool monitoring; remove dead code |
| `backend/tests/pipeline/test_session_isolation.py` | New test file with 5+ tests covering session isolation, error cascading, cleanup, and view refresh |

## Risk Assessment

- **Connection pool exhaustion**: Peak concurrent connections increases from 1 to 4 (orchestrator + 3 sources). Current pool config (`pool_size=10, max_overflow=15`) handles this easily.
- **Backward compatibility**: The `_update_source_with_recovery` method (uses `self.db`) is either removed or kept as a deprecated fallback. No external API changes.
- **Data integrity**: Each source's session commits independently. If one source fails mid-update, only that source's data is affected — exactly the same as the current behavior when it happens to work.
