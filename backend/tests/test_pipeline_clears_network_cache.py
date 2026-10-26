"""#336 follow-up: a successful source update clears cached network/enrichment responses."""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from app.api.endpoints.network_analysis import network_service  # the instance the API serves
from app.pipeline.annotation_pipeline import AnnotationPipeline
from tests.test_audit_pipeline_annotation_failures import OLD, SOURCE, _source_class


@pytest.fixture
def gene_id(test_engine):
    tag = uuid.uuid4().hex[:6].upper()
    with test_engine.begin() as conn:
        gid = conn.execute(
            text(
                "INSERT INTO genes (approved_symbol, hgnc_id, aliases) "
                "VALUES ('NWC' || :t, 'HGNC:NWC' || :t, '{}') RETURNING id"
            ),
            {"t": tag},
        ).scalar()
    yield gid
    with test_engine.begin() as conn:
        conn.execute(text("DELETE FROM gene_annotations WHERE gene_id = :g"), {"g": gid})
        conn.execute(text("DELETE FROM genes WHERE id = :g"), {"g": gid})


@pytest.mark.asyncio
async def test_source_update_clears_network_analysis_namespace(gene_id):
    record = SimpleNamespace(last_update=OLD, next_update=OLD, config={})
    pipeline = AnnotationPipeline(MagicMock())
    pipeline.sources = {SOURCE: _source_class({gene_id: {"ok": 1}}, record)}  # type: ignore[dict-item]
    cache = MagicMock()
    network_service._graph_cache["stale"] = object()  # warm in-process graph cache
    with patch("app.core.cache_service.get_cache_service", return_value=cache):
        results = await pipeline._update_sources_parallel([SOURCE], [gene_id], force=True)

    assert "error" not in results[SOURCE]
    cleared = [c.args[0] for c in cache.clear_namespace_sync.call_args_list]
    assert "network_analysis" in cleared
    assert "hpo_classifications" in cleared  # gene-list clinical-group cache (genes.py)
    # The in-process graph cache must not outlive the update, or a stale graph is re-cached
    assert "stale" not in network_service._graph_cache
