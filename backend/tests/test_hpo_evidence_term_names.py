"""HPO evidence stores term names; readers accept legacy bare-ID entries (#421)."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text

from app.api.endpoints.datasources import get_datasources
from app.core.hpo.models import HPOTerm
from app.core.hpo.pipeline import HPOPipeline
from app.pipeline.sources.unified.hpo import HPOUnifiedSource


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pipeline_stores_term_names():
    pipeline = HPOPipeline()
    pipeline.terms.get_descendants = AsyncMock(return_value={"HP:0000003", "HP:9999999"})
    gene = SimpleNamespace(name="HNF1B", entrez_id=6928)
    pipeline.annotations.batch_get_annotations = AsyncMock(
        return_value={t: SimpleNamespace(genes=[gene]) for t in ("HP:0000003", "HP:9999999")}
    )
    # HP:9999999 is not in the ontology (e.g. obsolete): stored with name None
    pipeline.terms.get_term = AsyncMock(
        side_effect=lambda t: (
            HPOTerm(id=t, name="Multicystic kidney dysplasia") if t == "HP:0000003" else None
        )
    )

    evidence = await pipeline.process_kidney_phenotypes()

    assert evidence["HNF1B"]["hpo_terms"] == [
        {"id": "HP:0000003", "name": "Multicystic kidney dysplasia"},
        {"id": "HP:9999999", "name": None},
    ]


def _insert_hpo(db_session, symbol: str, terms: list) -> int:
    gene_id = db_session.execute(
        text(
            "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
            "VALUES (:h, :s, '{}') RETURNING id"
        ),
        {"h": f"HGNC:{symbol}", "s": symbol},
    ).scalar_one()
    return db_session.execute(
        text(
            "INSERT INTO gene_evidence (gene_id, source_name, source_detail, evidence_data) "
            "VALUES (:g, 'HPO', 'test', CAST(:d AS jsonb)) RETURNING id"
        ),
        {"g": gene_id, "d": json.dumps({"hpo_terms": terms})},
    ).scalar_one()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_readers_accept_named_and_legacy_terms(db_session):
    db_session.execute(text("DELETE FROM gene_evidence WHERE source_name = 'HPO'"))
    legacy = _insert_hpo(db_session, "HPO421LEGACY", ["HP:0000003", "HP:0000107"])
    named = _insert_hpo(
        db_session,
        "HPO421NAMED",
        [{"id": "HP:0000003", "name": "Multicystic kidney dysplasia"}, {"id": "HP:0000107"}],
    )
    db_session.flush()

    # Scores only count terms, so both shapes score the same
    scores = dict(
        db_session.execute(
            text(
                "SELECT evidence_id, normalized_score FROM combined_evidence_scores "
                "WHERE evidence_id IN (:a, :b)"
            ),
            {"a": legacy, "b": named},
        ).all()
    )
    assert len(scores) == 2 and scores[legacy] == scores[named]

    # Distinct-term count sees the same two IDs in both shapes
    result = await get_datasources(db=db_session)
    hpo = next(s for s in result["data"]["sources"] if s.name == "HPO")
    assert hpo.stats.metadata["phenotype_terms"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_syndromic_descendants_loaded_once():
    source = HPOUnifiedSource(cache_service=MagicMock(), http_client=MagicMock())
    pipeline = MagicMock()
    pipeline.terms.get_descendants = AsyncMock(return_value={"HP:0001507"})
    with patch("app.core.hpo.pipeline.HPOPipeline", return_value=pipeline):
        await source._assess_syndromic_features({"HP:0000003"})
        calls = pipeline.terms.get_descendants.await_count
        await source._assess_syndromic_features({"HP:0000107"})
    assert calls > 0 and pipeline.terms.get_descendants.await_count == calls
