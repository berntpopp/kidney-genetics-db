"""#294: a failed bulk annotation write must surface as a source error, not success."""

import uuid
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from app.pipeline.annotation_pipeline import AnnotationPipeline

SOURCE = "_audit294"
OLD = datetime(2020, 1, 1)


@pytest.fixture
def genes(test_engine):
    """1501 committed genes (one more than the bulk chunk size)."""
    tag = uuid.uuid4().hex[:6].upper()
    with test_engine.begin() as conn:
        ids = [
            r[0]
            for r in conn.execute(
                text(
                    "INSERT INTO genes (approved_symbol, hgnc_id, aliases) "
                    "SELECT 'AUD' || :t || n, 'HGNC:AUD' || :t || n, '{}' "
                    "FROM generate_series(1, 1501) n RETURNING id"
                ),
                {"t": tag},
            )
        ]
    yield sorted(ids)
    with test_engine.begin() as conn:
        conn.execute(text("DELETE FROM genes WHERE approved_symbol LIKE :p"), {"p": f"AUD{tag}%"})


def _source_class(batch: dict[int, dict[str, Any]], record: SimpleNamespace):
    class FakeSource:
        version = "1"
        cache_ttl_days = 7
        batch_mode = False
        source_record = record

        def __init__(self, session):
            self.session = session

        async def fetch_batch(self, genes):
            return batch

        async def update_gene(self, gene):
            raise AssertionError("no per-gene fallback expected")

    return FakeSource


def _annotated(test_engine) -> int:
    with test_engine.connect() as conn:
        return conn.execute(
            text("SELECT count(*) FROM gene_annotations WHERE source = :s"), {"s": SOURCE}
        ).scalar()


async def _run(gene_ids: list[int], batch: dict[int, dict[str, Any]]):
    record = SimpleNamespace(last_update=OLD, next_update=OLD)
    pipeline = AnnotationPipeline(MagicMock())
    pipeline.sources = {SOURCE: _source_class(batch, record)}  # type: ignore[dict-item]
    with patch("app.core.cache_service.get_cache_service"):
        results = await pipeline._update_sources_parallel([SOURCE], gene_ids, force=True)
    return results[SOURCE], record


@pytest.mark.asyncio
async def test_failed_single_write_is_an_error_and_keeps_freshness(test_engine, genes):
    gene_id = genes[0]
    # PostgreSQL rejects \u0000 in jsonb: a real, recoverable write failure.
    result, record = await _run([gene_id], {gene_id: {"bad": "\u0000"}})

    assert "error" in result
    assert (record.last_update, record.next_update) == (OLD, OLD)
    assert _annotated(test_engine) == 0


@pytest.mark.asyncio
async def test_failed_final_chunk_is_not_silently_dropped(test_engine, genes):
    batch = {gid: {"i": i} for i, gid in enumerate(genes)}
    batch[genes[-1]] = {"bad": "\u0000"}  # only the 1501st item (second chunk) fails

    result, record = await _run(genes, batch)

    assert "error" in result
    assert (record.last_update, record.next_update) == (OLD, OLD)
    # Earlier chunks may persist; a retry re-upserts them idempotently.
    assert _annotated(test_engine) == 1500


@pytest.mark.asyncio
async def test_failed_fallback_commit_is_an_error_and_keeps_freshness(test_engine, genes):
    from app.models.gene_annotation import GeneAnnotation

    gene_id = genes[0]
    record = SimpleNamespace(last_update=OLD, next_update=OLD)

    class FallbackSource(_source_class({}, record)):  # batch fetch returns nothing
        async def update_gene(self, gene):
            # Batch mode: the write stays pending until the pipeline's fallback commit.
            self.session.add(
                GeneAnnotation(gene_id=gene.id, source=SOURCE, annotations={"bad": "\u0000"})
            )
            return True

    pipeline = AnnotationPipeline(MagicMock())
    pipeline.sources = {SOURCE: FallbackSource}  # type: ignore[dict-item]
    with patch("app.core.cache_service.get_cache_service"):
        results = await pipeline._update_sources_parallel([SOURCE], [gene_id], force=True)

    assert "error" in results[SOURCE]
    assert (record.last_update, record.next_update) == (OLD, OLD)
    assert _annotated(test_engine) == 0


@pytest.mark.asyncio
async def test_source_that_updates_no_gene_is_an_error_and_keeps_freshness(test_engine, genes):
    """An outage (e.g. pinned HPO files unavailable) fails every gene: no 90-day skip (#338)."""
    record = SimpleNamespace(last_update=OLD, next_update=OLD)

    class DownSource(_source_class({}, record)):
        async def fetch_batch(self, genes):
            raise RuntimeError("upstream down")

        async def update_gene(self, gene):
            return False

    pipeline = AnnotationPipeline(MagicMock())
    pipeline.sources = {SOURCE: DownSource}  # type: ignore[dict-item]
    with patch("app.core.cache_service.get_cache_service"):
        results = await pipeline._update_sources_parallel([SOURCE], genes[:2], force=True)

    assert "error" in results[SOURCE]
    assert (record.last_update, record.next_update) == (OLD, OLD)
