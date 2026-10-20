"""Transaction boundaries of the shared DataSourceClient evidence writer (#291, #292)."""

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.data_source_base import DataSourceClient

SOURCE = "AuditTxSource"


class _Source(DataSourceClient):
    """Minimal concrete source; ``payload`` (or an exception) is what the provider returns."""

    def __init__(self, payload: Any):
        super().__init__()
        self.payload = payload

    @property
    def source_name(self) -> str:
        return SOURCE

    @property
    def namespace(self) -> str:
        return "audit_tx"

    async def fetch_raw_data(self, tracker=None, mode: str = "smart") -> Any:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

    async def process_data(self, raw_data: Any) -> dict[str, Any]:
        return raw_data

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        return True


@pytest.fixture
def db(test_engine):
    """A real, independently committing session; rows created by the test are removed."""
    session = sessionmaker(bind=test_engine)()
    tag = uuid.uuid4().hex[:6].upper()
    yield session, tag
    session.rollback()
    session.close()
    with test_engine.begin() as conn:
        conn.execute(text("DELETE FROM gene_evidence WHERE source_name = :s"), {"s": SOURCE})
        conn.execute(text("DELETE FROM genes WHERE approved_symbol LIKE :p"), {"p": f"AUD{tag}%"})


def _normalized(symbols: list[str], tag: str) -> dict[str, dict[str, Any]]:
    return {
        s: {
            "status": "normalized",
            "approved_symbol": s,
            "hgnc_id": f"HGNC:AUD{tag}{i}",
        }
        for i, s in enumerate(symbols)
    }


def _normalizer(tag: str):
    async def fake(db, symbols, source_name):
        return _normalized(symbols, tag)

    return patch("app.core.gene_normalizer.normalize_genes_batch_async", fake)


def _evidence(test_engine, symbol: str) -> list[dict]:
    with test_engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT ge.evidence_data FROM gene_evidence ge JOIN genes g ON g.id = ge.gene_id "
                "WHERE ge.source_name = :s AND g.approved_symbol = :sym"
            ),
            {"s": SOURCE, "sym": symbol},
        ).fetchall()
    return [r[0] for r in rows]


def _gene_exists(test_engine, symbol: str) -> bool:
    with test_engine.connect() as conn:
        return (
            conn.execute(
                text("SELECT 1 FROM genes WHERE approved_symbol = :s"), {"s": symbol}
            ).first()
            is not None
        )


# --- #292: new genes get their evidence on the first pass ------------------------------


@pytest.mark.asyncio
async def test_new_gene_and_evidence_created_together_on_first_pass(test_engine, db):
    session, tag = db
    new_a, new_b = f"AUD{tag}A", f"AUD{tag}B"
    source = _Source({new_a: {"score": 1}, new_b: {"score": 2}})

    with _normalizer(tag):
        stats = await source.update_data(session, MagicMock(), mode="smart")

    assert stats["genes_created"] == 2
    assert stats["errors"] == 0
    assert stats["evidence_created"] == 2
    assert _evidence(test_engine, new_a) == [{"score": 1}]
    assert _evidence(test_engine, new_b) == [{"score": 2}]


@pytest.mark.asyncio
async def test_evidence_failure_rolls_back_the_new_gene_only(test_engine, db):
    session, tag = db
    ok, bad = f"AUD{tag}A", f"AUD{tag}B"
    source = _Source({ok: {"score": 1}, bad: {"score": 2}})
    real = DataSourceClient._create_or_update_evidence

    async def failing(self, db_, gene, data, stats):
        if gene.approved_symbol == bad:
            raise RuntimeError("evidence write failed")
        await real(self, db_, gene, data, stats)

    with _normalizer(tag), patch.object(_Source, "_create_or_update_evidence", failing):
        stats = await source.update_data(session, MagicMock(), mode="smart")

    assert stats["errors"] == 1
    assert _evidence(test_engine, ok) == [{"score": 1}]
    # The failing gene's savepoint (gene + evidence) is rolled back as one unit.
    assert not _gene_exists(test_engine, bad)
