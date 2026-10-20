"""Unassessed genes stay NULL in HPO syndromic classifications (#253)."""

import json

import pytest
from sqlalchemy import text

# symbol -> hpo annotation (None = no gene_annotations row)
CASES = {
    "AUDIT253_MISSING": None,
    "AUDIT253_EMPTY": {"classification": {}},
    "AUDIT253_TRUE": {"classification": {"syndromic_assessment": {"is_syndromic": True}}},
    "AUDIT253_FALSE": {"classification": {"syndromic_assessment": {"is_syndromic": False}}},
}
EXPECTED = {
    "AUDIT253_MISSING": None,
    "AUDIT253_EMPTY": None,
    "AUDIT253_TRUE": True,
    "AUDIT253_FALSE": False,
}


def _seed(db_session) -> dict[str, int]:
    ids = {}
    for symbol, annotation in CASES.items():
        ids[symbol] = db_session.execute(
            text(
                "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
                "VALUES (:h, :s, '{}') RETURNING id"
            ),
            {"h": f"HGNC:{symbol}", "s": symbol},
        ).scalar_one()
        if annotation is not None:
            db_session.execute(
                text(
                    "INSERT INTO gene_annotations (gene_id, source, version, annotations) "
                    "VALUES (:g, 'hpo', 'audit', CAST(:a AS jsonb))"
                ),
                {"g": ids[symbol], "a": json.dumps(annotation)},
            )
    db_session.flush()
    return ids


@pytest.mark.integration
def test_view_keeps_unassessed_null(db_session):
    ids = _seed(db_session)
    rows = db_session.execute(
        text(
            "SELECT gene_symbol, is_syndromic FROM gene_hpo_classifications "
            "WHERE gene_id = ANY(:ids)"
        ),
        {"ids": list(ids.values())},
    ).all()
    assert dict(rows) == EXPECTED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_endpoint_serializes_null(async_client, db_session):
    ids = _seed(db_session)
    response = await async_client.post(
        "/api/genes/hpo-classifications", json={"gene_ids": list(ids.values())}
    )
    assert response.status_code == 200, response.text
    got = {item["gene_symbol"]: item["is_syndromic"] for item in response.json()["data"]}
    assert got == EXPECTED
