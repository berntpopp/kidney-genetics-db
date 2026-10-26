"""gene_scores is refreshed after evidence tasks and before release export (#367)."""

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text

from app.core import arq_tasks, task_decorator
from app.services.release_service import ReleaseService


@pytest.fixture
def refreshed(monkeypatch) -> list:
    """Record refresh_score_views calls in the task modules; no DB needed."""
    calls: list = []
    for module in (task_decorator, arq_tasks):
        monkeypatch.setattr(module, "refresh_score_views", calls.append)
        monkeypatch.setattr(module, "ProgressTracker", MagicMock())

        @contextmanager
        def fake_db():
            yield MagicMock()

        monkeypatch.setattr(module, "get_db_context", fake_db)
    return calls


@pytest.mark.unit
async def test_managed_evidence_task_refreshes_scores_once(refreshed):
    class Manager(task_decorator.TaskMixin):
        broadcast_callback = None

        @task_decorator.managed_task("W4Source")
        async def _run(self, db, tracker, resume=False):
            return {"ok": True}

        @task_decorator.managed_task("W4Agg", refresh_scores=False)
        async def _run_agg(self, db, tracker, resume=False):
            return {"ok": True}

    assert await Manager()._run() == {"ok": True}
    assert len(refreshed) == 1
    await Manager()._run_agg()
    assert len(refreshed) == 1


@pytest.mark.unit
async def test_arq_evidence_task_refreshes_scores(refreshed, monkeypatch):
    source = MagicMock(update_data=AsyncMock(return_value={"added": 1}))
    monkeypatch.setattr("app.core.cache_service.get_cache_service", MagicMock())
    monkeypatch.setattr("app.core.cached_http_client.get_cached_http_client", MagicMock())
    monkeypatch.setattr(
        "app.pipeline.sources.unified.get_unified_source", MagicMock(return_value=source)
    )
    assert await arq_tasks.run_pipeline_task({}, "PanelApp") == {"added": 1}
    assert len(refreshed) == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    ("result", "failed"),
    [
        ({"sources_updated": 3, "errors": [{"source": "gtex"}]}, False),
        ({"sources_updated": 0, "errors": [{"source": "hgnc"}]}, True),
        ({"sources_updated": [], "errors": [], "message": "No sources"}, False),
    ],
)
async def test_annotation_pipeline_fails_only_when_no_source_succeeded(
    refreshed, monkeypatch, result, failed
):
    tracker = MagicMock()
    monkeypatch.setattr(task_decorator, "ProgressTracker", MagicMock(return_value=tracker))
    pipeline = MagicMock(run_update=AsyncMock(return_value=result))
    monkeypatch.setattr(
        "app.pipeline.annotation_pipeline.AnnotationPipeline", MagicMock(return_value=pipeline)
    )

    class Manager(task_decorator.TaskMixin):
        broadcast_callback = None

    await Manager()._run_annotation_pipeline()
    assert tracker.error.called is failed
    assert tracker.complete.called is not failed
    assert refreshed == []  # the pipeline refreshes its own views


@pytest.mark.integration
def test_release_export_uses_fresh_scores(db_session, tmp_path):
    gene = db_session.execute(
        text(
            "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
            "VALUES ('HGNC:W4REL', 'W4REL', '{}') RETURNING id"
        )
    ).scalar_one()
    db_session.execute(
        text(
            "INSERT INTO gene_evidence (gene_id, source_name, source_detail, evidence_data) "
            "VALUES (:g, 'ClinGen', 'w4', '{\"classifications\": [\"Definitive\"]}')"
        ),
        {"g": gene},
    )
    service = ReleaseService(db_session)
    service.export_dir = tmp_path
    path, _ = service._export_release_sync("w4", datetime.now(timezone.utc))
    genes = {g["approved_symbol"]: g for g in json.loads(path.read_text())["genes"]}
    assert genes["W4REL"]["scores"]["source_scores"] == {"ClinGen": 1.0}
