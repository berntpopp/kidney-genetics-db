"""#447: renal-neoplasia flag and filter on /api/genes, from the HPO clinical group."""

import json

import pytest
from sqlalchemy import text

# symbol -> HPO clinical_group (None: no HPO annotation)
CASES = {
    "RNLYNCH": {"primary": "neoplasia", "scores": {"neoplasia": 1.0}},  # MLH1-like
    "RNSDHA": {  # SDHA-like: secondary neoplasia just above the threshold
        "primary": "glomerulopathy",
        "scores": {"glomerulopathy": 0.746, "neoplasia": 0.254},
    },
    "RNEDGE": {"primary": "cakut", "scores": {"cakut": 0.75, "neoplasia": 0.25}},
    "RNBELOW": {"primary": "cakut", "scores": {"cakut": 0.751, "neoplasia": 0.249}},
    "RNNONE": None,
}
EXPECTED = {"RNLYNCH", "RNSDHA", "RNEDGE"}


@pytest.fixture
def genes(db_session):
    for symbol, group in CASES.items():
        gene_id = db_session.execute(
            text(
                "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
                "VALUES (:h, :s, '{}') RETURNING id"
            ),
            {"h": f"HGNC:{symbol}", "s": symbol},
        ).scalar_one()
        if group:
            db_session.execute(
                text(
                    "INSERT INTO gene_annotations (gene_id, source, annotations) "
                    "VALUES (:g, 'hpo', CAST(:a AS jsonb))"
                ),
                {"g": gene_id, "a": json.dumps({"classification": {"clinical_group": group}})},
            )
    db_session.flush()


async def _symbols(async_client, **filters) -> dict[str, bool]:
    params = {"filter[search]": "RN", "filter[hide_zero_scores]": "false", "page[size]": 100}
    response = await async_client.get("/api/genes/", params={**params, **filters})
    assert response.status_code == 200
    return {
        g["attributes"]["approved_symbol"]: g["attributes"]["renal_neoplasia"]
        for g in response.json()["data"]
        if g["attributes"]["approved_symbol"] in CASES
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_flag_follows_primary_or_score_threshold(async_client, genes):
    flags = await _symbols(async_client)
    assert flags == {s: s in EXPECTED for s in CASES}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_filter_only_and_exclude(async_client, genes):
    only = await _symbols(async_client, **{"filter[renal_neoplasia]": "true"})
    excluded = await _symbols(async_client, **{"filter[renal_neoplasia]": "false"})
    assert set(only) == EXPECTED
    assert set(excluded) == set(CASES) - EXPECTED


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gene_detail_carries_flag(async_client, genes):
    for symbol in ("RNSDHA", "RNBELOW"):
        response = await async_client.get(f"/api/genes/{symbol}")
        assert response.status_code == 200
        assert response.json()["data"]["attributes"]["renal_neoplasia"] is (symbol in EXPECTED)
