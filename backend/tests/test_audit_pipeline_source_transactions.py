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


# --- #291: full refresh keeps old evidence until the replacement succeeded ---------------

OTHER = "AuditTxOtherSource"


@pytest.fixture
def seeded(test_engine, db):
    """Committed genes KEEP (still reported) and GONE (no longer reported), each with
    old evidence for SOURCE, plus KEEP evidence for another source."""
    session, tag = db
    keep, gone = f"AUD{tag}KEEP", f"AUD{tag}GONE"
    with test_engine.begin() as conn:
        for i, sym in enumerate((keep, gone)):
            gid = conn.execute(
                text(
                    "INSERT INTO genes (approved_symbol, hgnc_id, aliases) "
                    "VALUES (:s, :h, '{}') RETURNING id"
                ),
                {"s": sym, "h": f"HGNC:AUD{tag}S{i}"},
            ).scalar()
            for src in (SOURCE, OTHER) if sym == keep else (SOURCE,):
                conn.execute(
                    text(
                        "INSERT INTO gene_evidence (gene_id, source_name, evidence_data) "
                        "VALUES (:g, :s, CAST('{\"old\": true}' AS jsonb))"
                    ),
                    {"g": gid, "s": src},
                )
    yield session, tag, keep, gone
    with test_engine.begin() as conn:
        conn.execute(text("DELETE FROM gene_evidence WHERE source_name = :s"), {"s": OTHER})


def _db_normalizer(test_engine, tag: str):
    """Resolve symbols like the real normalizer does for genes already in the DB."""

    async def fake(db, symbols, source_name):
        out = {}
        with test_engine.connect() as conn:
            for i, s in enumerate(symbols):
                hgnc = conn.execute(
                    text("SELECT hgnc_id FROM genes WHERE approved_symbol = :s"), {"s": s}
                ).scalar()
                out[s] = {
                    "status": "normalized",
                    "approved_symbol": s,
                    "hgnc_id": hgnc or f"HGNC:AUD{tag}N{i}",
                }
        return out

    return patch("app.core.gene_normalizer.normalize_genes_batch_async", fake)


def _old_intact(test_engine, keep: str, gone: str) -> bool:
    return _evidence(test_engine, keep) == [{"old": True}] and _evidence(test_engine, gone) == [
        {"old": True}
    ]


@pytest.mark.asyncio
async def test_full_refresh_fetch_failure_keeps_old_evidence(test_engine, seeded):
    session, tag, keep, gone = seeded
    source = _Source(TimeoutError("provider timeout"))

    with _db_normalizer(test_engine, tag), pytest.raises(TimeoutError):
        await source.update_data(session, MagicMock(), mode="full")
    session.rollback()

    assert _old_intact(test_engine, keep, gone)


@pytest.mark.asyncio
async def test_full_refresh_empty_result_keeps_old_evidence(test_engine, seeded):
    session, tag, keep, gone = seeded
    source = _Source({})

    with _db_normalizer(test_engine, tag):
        stats = await source.update_data(session, MagicMock(), mode="full")

    assert "error" in stats
    assert _old_intact(test_engine, keep, gone)


@pytest.mark.asyncio
async def test_full_refresh_persistence_failure_keeps_old_evidence(test_engine, seeded):
    session, tag, keep, gone = seeded
    source = _Source({keep: {"new": 1}})

    async def boom(*args, **kwargs):
        raise RuntimeError("database write failed")

    with (
        _db_normalizer(test_engine, tag),
        patch.object(_Source, "_create_or_update_evidence", boom),
    ):
        await source.update_data(session, MagicMock(), mode="full")

    # KEEP's replacement failed; GONE must not be pruned on a failed replacement either.
    assert _old_intact(test_engine, keep, gone)


@pytest.mark.asyncio
async def test_full_refresh_store_crash_keeps_old_evidence(test_engine, seeded):
    session, tag, keep, gone = seeded
    source = _Source({keep: {"new": 1}})

    async def crash(*args, **kwargs):
        raise RuntimeError("connection lost")

    with (
        _db_normalizer(test_engine, tag),
        patch.object(_Source, "_store_genes_in_database", crash),
        pytest.raises(RuntimeError),
    ):
        await source.update_data(session, MagicMock(), mode="full")
    session.rollback()

    assert _old_intact(test_engine, keep, gone)


@pytest.mark.asyncio
async def test_full_refresh_success_replaces_and_prunes_only_this_source(test_engine, seeded):
    session, tag, keep, gone = seeded
    source = _Source({keep: {"new": 1}})

    with _db_normalizer(test_engine, tag):
        stats = await source.update_data(session, MagicMock(), mode="full")

    assert stats["entries_deleted"] == 1
    assert _evidence(test_engine, keep) == [{"new": 1}]
    assert _evidence(test_engine, gone) == []
    with test_engine.connect() as conn:
        other = conn.execute(
            text("SELECT count(*) FROM gene_evidence WHERE source_name = :s"), {"s": OTHER}
        ).scalar()
    assert other == 1


# --- #292 boundary: an evidence writer collision only rolls back its own savepoint -------


@pytest.mark.asyncio
async def test_evidence_collision_keeps_rest_of_batch(test_engine, db):
    session, tag = db
    first, racing = f"AUD{tag}A", f"AUD{tag}B"
    source = _Source({first: {"score": 1}, racing: {"score": 2}})
    real_clean = DataSourceClient._clean_data_for_json

    def clean_after_competitor_insert(self, data):
        # Runs after the existence check: a concurrent writer commits RACING's evidence now.
        if data == {"score": 2}:
            with test_engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO gene_evidence (gene_id, source_name, source_detail, "
                        "evidence_data) SELECT id, :s, :d, CAST('{\"other\": 1}' AS jsonb) "
                        "FROM genes WHERE approved_symbol = :sym"
                    ),
                    {"s": SOURCE, "d": f"Data from {SOURCE}", "sym": racing},
                )
        return real_clean(self, data)

    with test_engine.begin() as conn:  # both genes exist, so only evidence can collide
        for i, sym in enumerate((first, racing)):
            conn.execute(
                text("INSERT INTO genes (approved_symbol, hgnc_id, aliases) VALUES (:s, :h, '{}')"),
                {"s": sym, "h": f"HGNC:AUD{tag}{i}"},
            )

    with (
        _db_normalizer(test_engine, tag),
        patch.object(_Source, "_clean_data_for_json", clean_after_competitor_insert),
    ):
        stats = await source.update_data(session, MagicMock(), mode="smart")

    assert stats["errors"] == 0
    assert _evidence(test_engine, first) == [{"score": 1}]  # earlier pending work survives
    assert _evidence(test_engine, racing) == [{"score": 2}]  # collision resolved by update
