"""Staging approvals are used, and a pending text is not staged twice (#366)."""

from unittest.mock import AsyncMock

import pytest

from app.core.gene_normalizer import GeneNormalizer
from app.models.gene_staging import GeneNormalizationStaging

SOURCE = "W3StagingSource"


def _normalizer(text: str) -> GeneNormalizer:
    normalizer = GeneNormalizer()
    normalizer.hgnc_client = AsyncMock()
    normalizer.hgnc_client.standardize_symbols_parallel = AsyncMock(
        return_value={text: {"approved_symbol": None, "hgnc_id": None}}
    )
    return normalizer


def _rows(db, text):
    return (
        db.query(GeneNormalizationStaging).filter_by(original_text=text, source_name=SOURCE).all()
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_approved_staging_record_resolves_the_text(db_session):
    db_session.add(
        GeneNormalizationStaging(
            original_text="KGTW3OLD",
            source_name=SOURCE,
            normalization_log={},
            status="approved",
            manual_approved_symbol="KGTW3NEW",
            manual_hgnc_id="HGNC:9936605",
        )
    )
    db_session.flush()

    result = await _normalizer("KGTW3OLD").normalize_batch_async(db_session, ["KGTW3OLD"], SOURCE)

    assert result["KGTW3OLD"]["status"] == "normalized"
    assert result["KGTW3OLD"]["approved_symbol"] == "KGTW3NEW"
    assert result["KGTW3OLD"]["hgnc_id"] == "HGNC:9936605"
    assert len(_rows(db_session, "KGTW3OLD")) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pending_text_is_not_staged_twice(db_session):
    for _ in range(2):
        result = await _normalizer("KGTW3UNK").normalize_batch_async(
            db_session, ["KGTW3UNK"], SOURCE
        )
        assert result["KGTW3UNK"]["status"] == "requires_manual_review"

    assert len(_rows(db_session, "KGTW3UNK")) == 1
