"""Paginating /api/genes over tied sort values neither repeats nor skips genes."""

import json

import pytest
from sqlalchemy import text

N_GENES = 30
PAGE_SIZE = 4


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "evidence",
    [
        None,  # no evidence: no gene_scores row, score NULL
        # evidence that scores 0: a gene_scores row and evidence_agg row per gene (#337)
        ("GenCC", {"classifications": ["No Known Disease Relationship"]}),
    ],
    ids=["no-evidence", "gencc-zero"],
)
@pytest.mark.parametrize("sort", ["-score", "count", "approved_symbol", None])
async def test_pagination_over_ties_is_complete_and_unique(
    async_client, db_session, sort, evidence
):
    # Same symbol and evidence -> every gene ties on every sort key except id.
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
    if evidence:
        source, data = evidence
        for gene_id in ids:
            db_session.execute(
                text(
                    "INSERT INTO gene_evidence (gene_id, source_name, source_detail, "
                    "evidence_data) VALUES (:g, :s, 'tiebreak', CAST(:d AS jsonb))"
                ),
                {"g": gene_id, "s": source, "d": json.dumps(data)},
            )
        db_session.execute(text("REFRESH MATERIALIZED VIEW gene_scores"))
        scores = db_session.execute(
            text("SELECT percentage_score FROM gene_scores WHERE gene_id = ANY(:ids)"),
            {"ids": ids},
        ).scalars()
        assert list(scores) == [0] * N_GENES, "each gene must have one zero-score row"
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
