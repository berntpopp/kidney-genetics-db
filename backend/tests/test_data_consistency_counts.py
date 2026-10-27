"""Counts agree across /datasources and /statistics; API timestamps carry UTC.

Runs against real PostgreSQL via the rolled-back ``db_session`` fixture.
"""

import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from pydantic import TypeAdapter
from sqlalchemy import text

from app.api.endpoints.datasources import get_datasources
from app.crud.statistics import statistics_crud

# gene -> {source: evidence_data}; KGTDC1 has two ClinGen classifications
GENES = {
    "KGTDC1": {
        "ClinGen": {"classifications": ["Definitive", "Limited"]},
        "GenCC": {"submissions": []},
    },
    "KGTDC2": {"ClinGen": {"classifications": ["Moderate"]}},
    "KGTDC3": {"Literature": {"publications": ["111", "222"]}},
    "KGTDC4": {"Literature": {"publications": ["222"]}},
}


def _seed(db):
    for i, (symbol, sources) in enumerate(GENES.items()):
        gene_id = db.execute(
            text(
                "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
                "VALUES (:h, :s, '{}') RETURNING id"
            ),
            {"h": f"HGNC:KGTDC{i}", "s": symbol},
        ).scalar_one()
        for source, data in sources.items():
            db.execute(
                text(
                    "INSERT INTO gene_evidence (gene_id, source_name, source_detail, evidence_data)"
                    " VALUES (:g, :src, 'test', CAST(:d AS jsonb))"
                ),
                {"g": gene_id, "src": source, "d": json.dumps(data)},
            )
    db.flush()


@pytest.fixture
def no_score_filter():
    # gene_scores is a materialized view; count over gene_evidence directly
    with patch("app.core.gene_filters.should_hide_zero_scores", return_value=False):
        yield


@pytest.mark.integration
def test_distribution_total_is_distinct_genes(db_session):
    before = statistics_crud.get_source_distributions(db_session, hide_zero_scores=False)
    _seed(db_session)
    after = statistics_crud.get_source_distributions(db_session, hide_zero_scores=False)

    def total(result, source):
        return result.get(source, {}).get("metadata", {}).get("total_genes", 0)

    # Two ClinGen genes, three classification rows: the total counts genes
    assert total(after, "ClinGen") - total(before, "ClinGen") == 2


@pytest.mark.integration
def test_upset_counts_single_source_genes(db_session):
    _seed(db_session)
    result = statistics_crud.get_source_overlaps(
        db_session, selected_sources=["ClinGen", "GenCC", "Literature"], hide_zero_scores=False
    )
    stats = result["overlap_statistics"]
    singles = [i for i in result["intersections"] if len(i["sets"]) == 1]
    assert stats["single_source_genes"] == sum(i["size"] for i in singles)
    assert stats["single_source_combinations"] == len(singles)
    ours = {g for i in singles for g in i["genes"] if g.startswith("KGTDC")}
    assert ours == {"KGTDC2", "KGTDC3", "KGTDC4"}


@pytest.mark.integration
def test_evidence_composition_has_no_presentation_colours(db_session):
    result = statistics_crud.get_evidence_composition(db_session, hide_zero_scores=False)
    for tier in result["evidence_tier_distribution"]:
        assert "color" not in tier


@pytest.mark.integration
@pytest.mark.asyncio
async def test_datasources_literature_and_coverage(db_session, no_score_filter):
    before = (await get_datasources(db=db_session))["data"]
    _seed(db_session)
    data = (await get_datasources(db=db_session))["data"]

    literature = next(s for s in data["sources"] if s.name == "Literature")
    assert literature.stats.metadata["publications"] >= 2  # "111", "222" deduplicated
    assert data["multi_source_genes"] - before["multi_source_genes"] == 1  # KGTDC1
    assert data["total_unique_genes"] - before["total_unique_genes"] == 4
    expected = round(data["multi_source_genes"] * 100 / data["total_unique_genes"])
    assert data["source_coverage"] == expected
    assert data["total_active"] == sum(s.status == "active" for s in data["sources"])


@pytest.mark.integration
def test_last_login_round_trips_as_utc(db_session, test_user):
    login = datetime(2026, 10, 27, 15, 29, 3, tzinfo=timezone.utc)
    test_user.last_login = login
    db_session.flush()
    db_session.expire(test_user)

    assert test_user.last_login == login
    assert test_user.last_login.tzinfo is not None
    # Pydantic, as in UserResponse, emits the offset only for aware values
    assert TypeAdapter(datetime).dump_json(test_user.last_login) == b'"2026-10-27T15:29:03Z"'
