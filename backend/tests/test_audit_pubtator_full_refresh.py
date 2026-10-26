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

    # Full run replaces a gene on first touch; the row survives and no prune ran (#291).
    assert _pmids(test_engine, old) == {"11"}
    assert _pmids(test_engine, new) == {"10"}  # page 1 upserted before the failure


def _source(
    session, pages: dict[int, list[dict]], fetched: list[int], fail: set[int] = frozenset()
):
    """PubTator source over fake pages; pages missing from ``pages`` are empty (end of stream)."""
    source = PubTatorUnifiedSource(db_session=session)
    source.chunk_size = 1
    source.filtering_enabled = False
    source.max_pages = None

    async def fetch_page(page: int, query: str) -> dict | None:
        fetched.append(page)
        if page in fail:
            raise TimeoutError("provider down")
        return {"results": pages.get(page, []), "total_pages": len(pages)}

    patch.object(source, "_fetch_page", fetch_page).start()
    patch.object(source, "_check_resources", return_value=True).start()
    return source


def _normalize(tag: str):
    async def normalize(db_, symbols, source_name):
        return {
            s: {"status": "normalized", "approved_symbol": s, "hgnc_id": f"HGNC:{s}"}
            for s in symbols
        }

    return patch("app.core.gene_normalizer.normalize_genes_batch_async", normalize)


@pytest.mark.asyncio
async def test_second_full_run_restarts_from_page_one_after_complete_run(test_engine, db):
    session, tag = db
    gene = f"AUD{tag}A"
    pages = {1: [_article("21", gene)], 2: [_article("22", gene)]}

    for _ in range(2):
        fetched: list[int] = []
        source = _source(session, pages, fetched)
        with _normalize(tag):
            await source.update_data(session, None, mode="full")
        patch.stopall()
        assert fetched[0] == 1  # never resumes past the end of a finished run

    assert _pmids(test_engine, gene) == {"21", "22"}


def _seed(session, symbol: str, pmids: list[str]) -> None:
    gene = Gene(approved_symbol=symbol, hgnc_id=f"HGNC:{symbol}")
    session.add(gene)
    session.flush()
    session.add(
        GeneEvidence(
            gene_id=gene.id,
            source_name="PubTator",
            evidence_data={"pmids": pmids, "publication_count": len(pmids)},
        )
    )
    session.commit()


async def _full_run(session, tag, pages, fail=frozenset(), max_pages=None, memory=False):
    fetched: list[int] = []
    source = _source(session, pages, fetched, fail)
    source.max_pages = max_pages
    if memory:  # resource guard trips before page 2
        patch.object(source, "_check_resources", side_effect=[True, False]).start()
    try:
        with _normalize(tag):
            await source.update_data(session, None, mode="full")
    finally:
        patch.stopall()
    return fetched


@pytest.mark.asyncio
async def test_complete_full_run_replaces_touched_and_prunes_untouched(test_engine, db):
    session, tag = db
    kept, stale = f"AUD{tag}KEPT", f"AUD{tag}STALE"
    _seed(session, kept, ["1", "2"])
    _seed(session, stale, ["3"])

    await _full_run(session, tag, {1: [_article("30", kept)], 2: [_article("31", kept)]})

    assert _pmids(test_engine, kept) == {"30", "31"}  # replaced on first touch, then merged
    assert _pmids(test_engine, stale) is None  # untouched by the complete run: pruned


@pytest.mark.parametrize(
    "case",
    [
        {"fail": {2}},  # a page failed after retries and was skipped
        {"max_pages": 1},  # early stop on max_pages
        {"memory": True},  # early stop on the resource guard
    ],
)
@pytest.mark.asyncio
async def test_incomplete_full_run_does_not_prune(test_engine, db, case):
    session, tag = db
    kept, stale = f"AUD{tag}KEPT", f"AUD{tag}STALE"
    _seed(session, kept, ["1"])
    _seed(session, stale, ["3"])
    pages = {1: [_article("40", kept)], 2: [_article("41", kept)], 3: [_article("42", kept)]}

    await _full_run(session, tag, pages, **case)

    assert _pmids(test_engine, stale) == {"3"}
    if not case.get("fail"):  # early stop keeps the checkpoint for resume
        progress = session.query(DataSourceProgress).filter_by(source_name="PubTator").one()
        session.refresh(progress)
        assert progress.progress_metadata["last_page"] == 1
        assert progress.progress_metadata["run_started_at"]


@pytest.mark.asyncio
async def test_rolled_back_batch_counts_as_error_and_blocks_prune(test_engine, db):
    session, tag = db
    kept, stale = f"AUD{tag}KEPT", f"AUD{tag}STALE"
    _seed(session, kept, ["1"])
    _seed(session, stale, ["3"])

    real_commit = session.commit
    state = {"failed": False}

    def flaky_commit():
        # Fail the first gene-batch commit only (inside _store_genes_without_tracker).
        import inspect

        if not state["failed"] and any(
            f.function == "_store_genes_without_tracker" for f in inspect.stack()
        ):
            state["failed"] = True
            raise RuntimeError("commit failed")
        return real_commit()

    with patch.object(session, "commit", flaky_commit):
        await _full_run(session, tag, {1: [_article("50", kept)], 2: [_article("51", kept)]})

    assert state["failed"]
    assert _pmids(test_engine, stale) == {"3"}


@pytest.mark.asyncio
async def test_resumed_full_run_keeps_pmids_from_before_interruption(test_engine, db):
    session, tag = db
    kept, stale = f"AUD{tag}KEPT", f"AUD{tag}STALE"
    _seed(session, kept, ["1"])
    _seed(session, stale, ["3"])
    pages = {1: [_article("60", kept)], 2: [_article("61", kept)]}

    await _full_run(session, tag, pages, max_pages=1)  # interrupted after page 1
    fetched = await _full_run(session, tag, pages)  # resume completes the same run

    assert fetched[0] == 2
    assert _pmids(test_engine, kept) == {"60", "61"}  # page-1 PMIDs not replaced again
    assert _pmids(test_engine, stale) is None


@pytest.mark.asyncio
async def test_crash_with_unflushed_pages_resumes_before_them(test_engine, db):
    """Pages buffered but not stored when a run crashes are re-fetched, never skipped."""
    session, tag = db
    early = f"AUD{tag}EARLY"
    _seed(session, early, ["1"])
    pages = {1: [_article("41", early)], 2: [_article("42", f"AUD{tag}B")]}

    fetched: list[int] = []
    source = _source(session, {**pages, 3: [None]}, fetched)  # page 3 malformed: raises
    source.chunk_size = 10  # pages 1-2 stay buffered
    try:
        with _normalize(tag), pytest.raises(AttributeError):
            await source.update_data(session, None, mode="full")
    finally:
        patch.stopall()

    fetched = await _full_run(session, tag, pages)
    assert fetched[0] == 1
    assert _pmids(test_engine, early) == {"41"}  # replaced, not pruned


@pytest.mark.asyncio
async def test_early_stop_does_not_filter_partially_replaced_genes(test_engine, db):
    """The min-publications filter waits for a complete run (#291)."""
    session, tag = db
    gene = f"AUD{tag}FEW"
    _seed(session, gene, ["1", "2", "3", "4"])
    pages = {1: [_article("51", gene)], 2: [_article("52", gene)]}

    fetched: list[int] = []
    source = _source(session, pages, fetched)
    source.max_pages = 1
    source.filtering_enabled = True
    source.filter_after_complete = True
    source.min_publications = 3
    try:
        with _normalize(tag):
            await source.update_data(session, None, mode="full")
    finally:
        patch.stopall()

    assert _pmids(test_engine, gene) == {"51"}  # replaced on first touch, not filtered out


async def _hgnc_run(session, tag, make_request):
    """Full run whose new gene goes through the real normalizer with HGNC patched."""
    from app.core.hgnc_client import HGNCClientCached

    kept, stale, new = f"AUD{tag}KEPT", f"AUD{tag}STALE", f"AUD{tag}NEW"
    _seed(session, kept, ["1"])
    _seed(session, stale, ["3"])
    fetched: list[int] = []
    source = _source(session, {1: [_article("60", kept), _article("61", new)]}, fetched)
    try:
        with patch.object(HGNCClientCached, "_make_request", make_request):
            await source.update_data(session, None, mode="full")
    finally:
        patch.stopall()
        with session.bind.begin() as conn:
            conn.execute(
                text("DELETE FROM gene_normalization_staging WHERE original_text LIKE :p"),
                {"p": f"AUD{tag}%"},
            )
    return stale


@pytest.mark.asyncio
async def test_hgnc_outage_counts_as_error_and_blocks_prune(test_engine, db):
    session, tag = db

    async def outage(self, endpoint, params=None, method="GET"):
        raise ConnectionError("HGNC down")

    stale = await _hgnc_run(session, tag, outage)

    assert _pmids(test_engine, stale) == {"3"}  # an outage is not "not found" (#291)


@pytest.mark.asyncio
async def test_hgnc_not_found_is_staged_and_does_not_block_prune(test_engine, db):
    session, tag = db

    async def not_found(self, endpoint, params=None, method="GET"):
        return {"response": {"docs": []}}

    stale = await _hgnc_run(session, tag, not_found)

    assert _pmids(test_engine, stale) is None  # genuine not-found keeps today's behaviour


@pytest.mark.asyncio
async def test_store_genes_counts_normalization_errors(db):
    from unittest.mock import MagicMock

    session, tag = db
    source = PubTatorUnifiedSource(db_session=session)
    stats = source._initialize_stats()

    async def normalize(db_, symbols, source_name):
        return {
            symbols[0]: {"status": "error", "error": "HGNC down"},
            symbols[1]: {"status": "requires_manual_review"},
        }

    with patch("app.core.gene_normalizer.normalize_genes_batch_async", normalize):
        await source._store_genes_in_database(
            session, {f"AUD{tag}E": {}, f"AUD{tag}S": {}}, stats, MagicMock()
        )

    assert stats["errors"] == 1  # staged (not-found) symbols stay uncounted
