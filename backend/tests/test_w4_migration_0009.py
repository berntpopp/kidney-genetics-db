"""Migration 0009: statistics/summary matviews, gene_scores divisor once (#367)."""

import pytest
from sqlalchemy import text

from app.db import views
from tests.test_audit_migration_views import (  # noqa: F401 - baseline_db is a fixture
    _add_evidence,
    _add_gene,
    _alembic,
    _assert_view_matches_canonical,
    baseline_db,
)

DIFF = (
    "SELECT count(*) FROM ((SELECT * FROM gene_scores EXCEPT SELECT * FROM w4_snapshot) "
    "UNION ALL (SELECT * FROM w4_snapshot EXCEPT SELECT * FROM gene_scores)) d"
)
MATVIEWS = ("gene_scores", "source_overlap_statistics", "gene_annotations_summary")


def _seed(conn) -> None:
    clingen = ["Definitive", "Moderate", "Limited", None, "Strong", None]
    for i, cls in enumerate(clingen):
        gene = _add_gene(conn, f"W4G{i}")
        _add_evidence(conn, gene, "PubTator", {"publication_count": i * 3 + 1})
        if cls:
            _add_evidence(conn, gene, "ClinGen", {"classifications": [cls]})
        if i % 2 == 0:
            _add_evidence(conn, gene, "GenCC", {"classifications": ["Definitive"]})
        conn.execute(
            text(
                "INSERT INTO gene_annotations (gene_id, source, version, annotations) "
                "VALUES (:g, 'gnomad', 'w4', CAST(:a AS jsonb))"
            ),
            {"g": gene, "a": f'{{"pLI": 0.{i}}}'},
        )


@pytest.mark.integration
def test_0009_keeps_gene_scores_and_adds_refreshable_matviews(baseline_db):  # noqa: F811
    engine, url = baseline_db
    _alembic(url, "upgrade", "0008")
    with engine.begin() as conn:
        _seed(conn)
        conn.execute(text("REFRESH MATERIALIZED VIEW gene_scores"))
        conn.execute(text("CREATE TABLE w4_snapshot AS SELECT * FROM gene_scores"))
        # Production-like leftovers: ad hoc summary without index, extra dependent matview.
        conn.execute(
            text("CREATE MATERIALIZED VIEW gene_annotations_summary AS SELECT 1 AS gene_id")
        )
        conn.execute(
            text(
                "CREATE MATERIALIZED VIEW w4_dependent AS "
                "SELECT evidence_tier, count(*) AS n FROM gene_scores GROUP BY evidence_tier"
            )
        )
        conn.execute(text("CREATE UNIQUE INDEX w4_dependent_tier ON w4_dependent (evidence_tier)"))
        assert conn.execute(text(DIFF)).scalar_one() == 0
        tiers = conn.execute(text("SELECT count(DISTINCT evidence_tier) FROM gene_scores"))
        assert tiers.scalar_one() >= 3  # data actually exercises the tier branches

    for _ in range(2):  # upgrade, then downgrade -1 and upgrade again
        _alembic(url, "upgrade", "head")
        with engine.begin() as conn:
            assert conn.execute(text(DIFF)).scalar_one() == 0
            _assert_view_matches_canonical(conn, views.gene_scores)
            assert conn.execute(text("SELECT count(*) FROM gene_list_detailed")).scalar() == 6
            assert conn.execute(text("SELECT sum(n) FROM w4_dependent")).scalar() == 6
            for mv in MATVIEWS:
                conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}"))
            pli = conn.execute(
                text("SELECT pli FROM gene_annotations_summary WHERE approved_symbol = 'W4G3'")
            )
            assert pli.scalar_one() == 0.3
            overlap = conn.execute(
                text(
                    "SELECT overlap_count FROM source_overlap_statistics "
                    "WHERE source1 = 'ClinGen' AND source2 = 'PubTator'"
                )
            )
            assert overlap.scalar_one() == 4
        _alembic(url, "downgrade", "-1")
        with engine.begin() as conn:
            assert conn.execute(text(DIFF)).scalar_one() == 0
            for mv in MATVIEWS[1:]:
                assert conn.execute(text(f"SELECT to_regclass('{mv}')")).scalar() is None


@pytest.mark.integration
async def test_statistics_summary_works_on_alembic_database(async_client):
    resp = await async_client.get("/api/statistics/summary")
    assert resp.status_code == 200, resp.text
