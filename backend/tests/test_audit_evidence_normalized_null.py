"""Gene evidence reports a missing normalized score as null, not 0.0 (#278)."""

import pytest
from sqlalchemy import text

from app.crud.evidence_transform import transform_evidence_to_jsonapi


class _Evidence:
    def __init__(self, evidence_id: int):
        self.id = evidence_id
        self.source_name = "HPO"
        self.source_detail = None
        self.evidence_data = {}
        self.evidence_date = None
        self.created_at = None


@pytest.mark.unit
def test_transform_keeps_scores_and_nulls_missing():
    data = transform_evidence_to_jsonapi([_Evidence(1), _Evidence(2)], 9, {1: 0.0})
    assert data[0]["attributes"]["normalized_score"] == 0.0
    assert data[1]["attributes"]["normalized_score"] is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_evidence_endpoint_null_for_unscored_evidence(async_client, db_session):
    gene_id = db_session.execute(
        text(
            "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
            "VALUES ('HGNC:AUDIT278', 'AUDITNORM278', '{}') RETURNING id"
        )
    ).scalar_one()
    # Scored: one HPO term -> evidence_count_percentiles row.
    # Unscored: zero terms/diseases -> source_count 0, absent from combined_evidence_scores.
    scored_id, unscored_id = (
        db_session.execute(
            text(
                "INSERT INTO gene_evidence (gene_id, source_name, source_detail, evidence_data) "
                "VALUES (:g, 'HPO', :detail, CAST(:d AS jsonb)) RETURNING id"
            ),
            {"g": gene_id, "detail": detail, "d": data},
        ).scalar_one()
        for detail, data in (
            ("scored", '{"hpo_terms": ["HP:0000107"]}'),
            ("unscored", '{"hpo_terms": []}'),
        )
    )
    db_session.flush()

    expected = db_session.execute(
        text("SELECT normalized_score FROM combined_evidence_scores WHERE evidence_id = :e"),
        {"e": scored_id},
    ).scalar_one()
    assert (
        db_session.execute(
            text("SELECT count(*) FROM combined_evidence_scores WHERE evidence_id = :e"),
            {"e": unscored_id},
        ).scalar_one()
        == 0
    )

    response = await async_client.get("/api/genes/AUDITNORM278/evidence")
    assert response.status_code == 200
    scores = {int(e["id"]): e["attributes"]["normalized_score"] for e in response.json()["data"]}
    assert scores[scored_id] == round(float(expected), 4)
    assert scores[unscored_id] is None
