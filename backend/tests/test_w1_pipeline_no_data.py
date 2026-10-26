"""#360: '0/N genes updated' fails a source only for an outage, not for genes without data."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.security import create_access_token
from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation
from app.pipeline.annotation_pipeline import AnnotationPipeline
from tests.fixtures.auth import get_or_create_user


class _NoDataSource:
    """A source that has no data for any gene; fetch_batch may simulate an outage."""

    version = "1"
    cache_ttl_days = 7
    fetch_raises = False
    source_record = MagicMock()

    def __init__(self, session):
        pass

    @staticmethod
    def stale_annotation_filter():
        return None

    async def fetch_batch(self, genes):
        if self.fetch_raises:
            raise RuntimeError("upstream down")
        return {}

    async def update_gene(self, gene):
        return False


async def _update(db_session, gene_id: int, source_class=_NoDataSource):
    pipeline = AnnotationPipeline(db_session)
    pipeline.sources["w1nodata"] = source_class
    with patch("app.pipeline.annotation_pipeline.SessionLocal"):  # skip the cache clear
        return await pipeline._update_source_with_session("w1nodata", [gene_id], False, db_session)


def _gene(db_session) -> Gene:
    gene = Gene(approved_symbol="W1NODATA", hgnc_id="HGNC:99936001")
    db_session.add(gene)
    db_session.flush()
    return gene


@pytest.mark.asyncio
async def test_one_gene_without_data_completes_and_advances_source(db_session):
    gene = _gene(db_session)

    class _Tracked(_NoDataSource):
        source_record = MagicMock(next_update=None)

    result = await _update(db_session, gene.id, _Tracked)

    assert result["successful"] == 0
    assert _Tracked.source_record.next_update > datetime.utcnow()  # advanced, no longer due


@pytest.mark.asyncio
async def test_genes_that_had_data_and_now_get_none_still_fail(db_session):
    gene = _gene(db_session)
    db_session.add(GeneAnnotation(gene_id=gene.id, source="w1nodata", annotations={"x": 1}))
    db_session.flush()

    with pytest.raises(RuntimeError, match="0/1 genes updated"):
        await _update(db_session, gene.id)


@pytest.mark.asyncio
async def test_batch_fetch_outage_still_fails(db_session):
    gene = _gene(db_session)

    class _Down(_NoDataSource):
        fetch_raises = True

    with pytest.raises(RuntimeError, match="0/1 genes updated"):
        await _update(db_session, gene.id, _Down)


@pytest.mark.asyncio
async def test_update_failed_finds_genes_without_annotations(db_session, async_client):
    """#366 item 6: the old evidence_score > 0 filter never matched anything."""
    gene = _gene(db_session)
    admin = get_or_create_user(db_session, "w1_admin", "w1_admin@example.com", "Pw-1!", "admin")
    headers = {"Authorization": f"Bearer {create_access_token(subject=admin.username)}"}

    run = "app.api.endpoints.annotation_updates._run_pipeline_update"
    with patch(run, AsyncMock()) as background_run:  # never start a real pipeline here
        response = await async_client.post(
            "/api/annotations/pipeline/update-failed", headers=headers
        )

    assert response.status_code == 200
    assert response.json()["count"] >= 1
    assert gene.id in background_run.await_args.args[2]
