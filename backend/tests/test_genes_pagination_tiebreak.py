"""Paginating /api/genes over tied sort values neither repeats nor skips genes."""

import pytest
from sqlalchemy import text

N_GENES = 30
PAGE_SIZE = 4


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("sort", ["-score", "count", "approved_symbol", None])
async def test_pagination_over_ties_is_complete_and_unique(async_client, db_session, sort):
    # Same symbol, no evidence -> every gene ties on every sort key except id.
    ids = [
        db_session.execute(
            text(
                "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
                "VALUES (:h, 'TIEBREAKZZ', '{}') RETURNING id"
            ),
            {"h": f"HGNC:TIE{i}"},
        ).scalar_one()
        for i in range(N_GENES)
    ]
    db_session.flush()

    seen: list[int] = []
    for page in range(1, N_GENES // PAGE_SIZE + 2):
        params = {
            "filter[search]": "TIEBREAKZZ",
            "filter[hide_zero_scores]": "false",
            "page[number]": page,
            "page[size]": PAGE_SIZE,
        }
        if sort:
            params["sort"] = sort
        response = await async_client.get("/api/genes/", params=params)
        assert response.status_code == 200
        seen += [int(g["id"]) for g in response.json()["data"]]

    assert len(seen) == len(set(seen)), "a gene repeated across pages"
    assert sorted(seen) == sorted(ids), "a gene was skipped"
