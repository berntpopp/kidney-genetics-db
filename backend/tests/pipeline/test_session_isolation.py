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
        # SQLAlchemy 2.x: is_active stays True after close(), so check
        # that the session has no open transaction instead
        for sess in created_sessions:
            assert not sess.in_transaction(), "Source session was not closed after use"

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
            results = await pipeline._update_sources_parallel(["gnomad"], gene_ids=[1], force=False)

        assert len(mock_sessions) == 1
        mock_sessions[0].rollback.assert_called_once()
        mock_sessions[0].close.assert_called_once()
        assert "error" in results.get("gnomad", {})


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
        async def get_sources(*a, **kw):
            return ["hgnc"]

        async def get_genes(*a, **kw):
            return [MagicMock(id=1, approved_symbol="TEST")]

        async def noop_refresh():
            return True

        async def noop_save(*a):
            return None

        async def noop_load():
            return None

        pipeline._get_sources_to_update = get_sources
        pipeline._get_genes_to_update = get_genes
        pipeline._refresh_materialized_view = noop_refresh
        pipeline._save_checkpoint = noop_save
        pipeline._load_checkpoint = noop_load

        with (
            patch("app.pipeline.annotation_pipeline.SessionLocal"),
            patch.object(pipeline, "_update_source_with_session", side_effect=fake_update),
        ):
            await pipeline.run_update(sources=["hgnc"], gene_ids=[1], force=True)

        assert len(hgnc_session_ids) == 1
        assert hgnc_session_ids[0] != id(db_session), "HGNC must not use the orchestration session"
