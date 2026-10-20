"""PubTator full refresh must not drop committed evidence before streaming succeeds (#291)."""

import json
import uuid
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.models.gene import Gene, GeneEvidence
from app.models.progress import DataSourceProgress
from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource


@pytest.fixture
def db(test_engine):
    session = sessionmaker(bind=test_engine)()
    tag = uuid.uuid4().hex[:6].upper()
    # Startup may already have registered PubTator; restore its checkpoint afterwards.
    with test_engine.connect() as conn:
        saved = conn.execute(
            text("SELECT metadata FROM data_source_progress WHERE source_name = 'PubTator'")
        ).first()
    yield session, tag
    session.rollback()
    session.close()
    with test_engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM gene_evidence WHERE gene_id IN "
                "(SELECT id FROM genes WHERE approved_symbol LIKE :p)"
            ),
            {"p": f"AUD{tag}%"},
        )
        conn.execute(text("DELETE FROM genes WHERE approved_symbol LIKE :p"), {"p": f"AUD{tag}%"})
        if saved is None:
            conn.execute(text("DELETE FROM data_source_progress WHERE source_name = 'PubTator'"))
        else:
            conn.execute(
                text(
                    "UPDATE data_source_progress SET metadata = CAST(:m AS jsonb) "
                    "WHERE source_name = 'PubTator'"
                ),
                {"m": json.dumps(saved[0])},
            )


def _article(pmid: str, symbol: str) -> dict[str, Any]:
    return {
        "pmid": pmid,
        "score": 1.0,
        "title": "t",
        "text_hl": f"@GENE_{symbol} @GENE_1 @@@{symbol}@@@",
    }


def _pmids(test_engine, symbol: str) -> set[str] | None:
    with test_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT ge.evidence_data FROM gene_evidence ge JOIN genes g ON g.id = ge.gene_id "
                "WHERE ge.source_name = 'PubTator' AND g.approved_symbol = :s"
            ),
            {"s": symbol},
        ).first()
    return set(row[0]["pmids"]) if row else None


@pytest.mark.asyncio
async def test_full_refresh_failing_mid_stream_keeps_existing_evidence(test_engine, db):
    session, tag = db
    old, new = f"AUD{tag}OLD", f"AUD{tag}NEW"

    gene = Gene(approved_symbol=old, hgnc_id=f"HGNC:AUD{tag}0")
    session.add(gene)
    session.flush()
    session.add(
        GeneEvidence(
            gene_id=gene.id,
            source_name="PubTator",
            evidence_data={"pmids": ["1", "2", "3"], "publication_count": 3},
        )
    )
    # A previous smart run left a checkpoint, so requesting full is a mode switch.
    progress = session.query(DataSourceProgress).filter_by(source_name="PubTator").first()
    if progress is None:
        progress = DataSourceProgress(source_name="PubTator")
        session.add(progress)
    progress.progress_metadata = {"last_page": 9, "mode": "smart"}
    session.commit()

    source = PubTatorUnifiedSource(db_session=session)
    source.chunk_size = 1  # flush page 1 before page 2 fails
    source.filtering_enabled = False

    async def fetch_page(page: int, query: str) -> dict | None:
        if page == 1:
            return {"results": [_article("10", new), _article("11", old)], "total_pages": 2}
        return {"results": [None]}  # malformed page 2: processing raises

    async def normalize(db_, symbols, source_name):
        return {
            s: {"status": "normalized", "approved_symbol": s, "hgnc_id": f"HGNC:AUD{tag}{i + 1}"}
            for i, s in enumerate(symbols)
        }

    with (
        patch.object(source, "_fetch_page", fetch_page),
        patch("app.core.gene_normalizer.normalize_genes_batch_async", normalize),
        pytest.raises(AttributeError),
    ):
        await source.update_data(session, None, mode="full")

    assert _pmids(test_engine, old) == {"1", "2", "3", "11"}  # survived, merged with page 1
    assert _pmids(test_engine, new) == {"10"}  # page 1 upserted before the failure
