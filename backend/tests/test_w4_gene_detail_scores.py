"""#363: gene detail reads its score breakdown from gene_scores, not live rescoring."""

import pytest
from sqlalchemy import event, text


@pytest.mark.integration
async def test_gene_detail_breakdown_matches_live_scores_without_rescoring(
    async_client, db_session
):
    gene = db_session.execute(
        text(
            "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
            "VALUES ('HGNC:W4DET', 'W4DET', '{}') RETURNING id"
        )
    ).scalar_one()
    for source, data in (
        ("ClinGen", '{"classifications": ["Moderate"]}'),
        ("PubTator", '{"publication_count": 7}'),
    ):
        db_session.execute(
            text(
                "INSERT INTO gene_evidence (gene_id, source_name, source_detail, evidence_data) "
                "VALUES (:g, :s, 'w4', CAST(:d AS jsonb))"
            ),
            {"g": gene, "s": source, "d": data},
        )
    db_session.execute(text("REFRESH MATERIALIZED VIEW gene_scores"))
    # What the endpoint used to compute per request
    expected = {
        name: round(float(score), 4)
        for name, score in db_session.execute(
            text(
                "SELECT source_name, normalized_score FROM combined_evidence_scores "
                "WHERE gene_id = :g ORDER BY source_name"
            ),
            {"g": gene},
        )
    }

    statements: list[str] = []
    conn = db_session.connection()
    listener = lambda *args: statements.append(args[2])  # noqa: E731
    event.listen(conn, "before_cursor_execute", listener)
    try:
        resp = await async_client.get("/api/genes/W4DET")
    finally:
        event.remove(conn, "before_cursor_execute", listener)

    assert resp.status_code == 200, resp.text
    attrs = resp.json()["data"]["attributes"]
    assert attrs["score_breakdown"] == expected
    assert list(attrs["score_breakdown"]) == ["ClinGen", "PubTator"]
    assert attrs["source_scores"] == expected
    assert attrs["sources"] == ["ClinGen", "PubTator"]
    assert not [s for s in statements if "combined_evidence_scores" in s]
