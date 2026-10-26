"""No DB transaction may stay open across a network await (#249).

The engine kills sessions idle in a transaction (idle_in_transaction_session_timeout); here the
timeout is 1s and the mocked network call sleeps 2s, so a held transaction breaks the session.
"""

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation
from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource
from app.pipeline.sources.annotations.mpo_mgi import MPOMGIAnnotationSource


@pytest.fixture
def db(test_engine):
    engine = create_engine(
        test_engine.url,
        poolclass=NullPool,
        connect_args={"options": "-c idle_in_transaction_session_timeout=1000"},
    )
    session = sessionmaker(bind=engine)()
    tag = uuid.uuid4().hex[:6].upper()
    gene = Gene(approved_symbol=f"AUD{tag}TX", hgnc_id=f"HGNC:AUD{tag}")
    session.add(gene)
    session.commit()
    gene_id = gene.id
    yield session, gene_id
    session.close()
    engine.dispose()
    with test_engine.begin() as conn:
        conn.execute(text("DELETE FROM gene_annotations WHERE gene_id = :g"), {"g": gene_id})
        conn.execute(text("DELETE FROM annotation_history WHERE gene_id = :g"), {"g": gene_id})
        conn.execute(text("DELETE FROM genes WHERE id = :g"), {"g": gene_id})
        conn.execute(
            text("DELETE FROM cache_entries WHERE cache_key LIKE :p"), {"p": f"%AUD{tag}%"}
        )


async def _slow_fetch(*args, **kwargs):
    await asyncio.sleep(2)
    return {"symbol": "X", "note": "fetched"}


@pytest.mark.asyncio
async def test_update_gene_does_not_hold_transaction_across_fetch(db):
    session, gene_id = db
    source = HGNCAnnotationSource(session)
    gene = session.get(Gene, gene_id)  # opens a read transaction, as the endpoints do

    with patch.object(source, "fetch_annotation", _slow_fetch):
        assert await source.update_gene(gene)

    assert session.query(GeneAnnotation).filter_by(gene_id=gene_id, source="hgnc").count() == 1


@pytest.mark.asyncio
async def test_mpo_mgi_update_gene_does_not_hold_transaction_across_fetch(db):
    session, gene_id = db
    source = MPOMGIAnnotationSource(session)
    gene = session.get(Gene, gene_id)

    async def version():
        return "test"

    with (
        patch.object(source, "fetch_annotation", _slow_fetch),
        patch.object(source, "_get_mousemine_version", version),
    ):
        assert await source.update_gene(gene)


@pytest.mark.asyncio
async def test_update_endpoint_releases_request_transaction(db):
    from app.api.endpoints.annotation_updates import update_gene_annotations as endpoint

    session, gene_id = db

    admin = SimpleNamespace(id=0, username="audit")
    await endpoint(gene_id, BackgroundTasks(), ["hgnc"], session, admin)

    # The request session must not idle in a transaction while the response is sent and the
    # background tasks run their network fetches.
    assert not session.in_transaction()


def test_pipeline_session_override_does_not_leak_to_pool(test_engine):
    from app.pipeline.annotation_pipeline import _close_pipeline_session

    engine = create_engine(test_engine.url, pool_size=1, max_overflow=0)
    try:
        session = sessionmaker(bind=engine)()
        session.execute(text("SET idle_in_transaction_session_timeout = '7s'"))
        session.commit()
        _close_pipeline_session(session)

        with engine.connect() as conn:  # the same pooled connection
            value = conn.execute(text("SHOW idle_in_transaction_session_timeout")).scalar()
        assert value != "7s"
    finally:
        engine.dispose()


def test_pipeline_session_close_discards_uncommitted_writes(test_engine, db):
    from app.pipeline.annotation_pipeline import _close_pipeline_session

    session, gene_id = db
    session.get(Gene, gene_id).approved_symbol = "AUDNOTCOMMITTED"
    session.flush()
    _close_pipeline_session(session)

    with test_engine.connect() as conn:
        symbol = conn.execute(
            text("SELECT approved_symbol FROM genes WHERE id = :g"), {"g": gene_id}
        ).scalar()
    assert symbol != "AUDNOTCOMMITTED"  # a failed/cancelled run's leftovers are rolled back


def test_pipeline_session_invalidated_when_reset_fails():
    from app.pipeline.annotation_pipeline import _close_pipeline_session

    session = MagicMock()
    session.execute.side_effect = RuntimeError("connection gone")
    _close_pipeline_session(session)

    session.invalidate.assert_called_once()
