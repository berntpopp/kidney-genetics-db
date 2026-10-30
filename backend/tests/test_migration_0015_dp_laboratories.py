"""0015: the DiagnosticPanels score counts laboratories; 0016: DLX4 gets HGNC:2917 back."""

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

COUNTS = (
    "SELECT approved_symbol, source_count FROM evidence_source_counts "
    "WHERE source_name = 'DiagnosticPanels'"
)


@pytest.mark.integration
def test_count_switches_to_laboratories_and_back(baseline_db):  # noqa: F811
    engine, url = baseline_db
    _alembic(url, "upgrade", "0014")
    with engine.begin() as conn:
        one_lab = _add_gene(conn, "G15ONELAB")  # one lab, many sub-panels
        _add_evidence(
            conn,
            one_lab,
            "DiagnosticPanels",
            {"panels": [f"P{i}" for i in range(24)], "panel_count": 24, "provider_count": 1},
        )
        three = _add_gene(conn, "G15THREE")  # legacy row: no provider_count
        _add_evidence(
            conn, three, "DiagnosticPanels", {"panels": ["K"], "providers": ["A", "B", "C"]}
        )
        conn.execute(text("REFRESH MATERIALIZED VIEW gene_scores"))
        conn.execute(text("CREATE MATERIALIZED VIEW g15_dep AS SELECT * FROM gene_scores"))
        before = dict(conn.execute(text(COUNTS)).all())
    assert before == {"G15ONELAB": 24, "G15THREE": 1}

    _alembic(url, "upgrade", "0015")
    with engine.begin() as conn:
        assert dict(conn.execute(text(COUNTS)).all()) == {"G15ONELAB": 1, "G15THREE": 3}
        _assert_view_matches_canonical(conn, views.evidence_source_counts)
        scores = dict(
            conn.execute(
                text("SELECT approved_symbol, source_scores->>'DiagnosticPanels' FROM g15_dep")
            ).all()
        )
        assert float(scores["G15THREE"]) > float(scores["G15ONELAB"])  # dependent refreshed
        assert conn.execute(text("SELECT count(*) FROM gene_list_detailed")).scalar_one() == 2

    _alembic(url, "downgrade", "0014")
    with engine.begin() as conn:
        assert dict(conn.execute(text(COUNTS)).all()) == before
    _alembic(url, "upgrade", "head")


@pytest.mark.integration
def test_dlx4_repair_touches_only_the_wrong_row(baseline_db):  # noqa: F811
    engine, url = baseline_db
    _alembic(url, "upgrade", "0015")
    with engine.begin() as conn:
        for symbol, hgnc_id in (("DLX4", "HGNC:15673"), ("PKD1", "HGNC:9008")):
            gene = _add_gene(conn, symbol)
            conn.execute(
                text("UPDATE genes SET hgnc_id = :h WHERE id = :g"), {"h": hgnc_id, "g": gene}
            )
    ids = "SELECT approved_symbol, hgnc_id FROM genes WHERE approved_symbol IN ('DLX4', 'PKD1')"
    for _ in range(2):  # re-running (downgrade is a no-op) changes nothing more
        _alembic(url, "upgrade", "0016")
        with engine.begin() as conn:
            assert dict(conn.execute(text(ids)).all()) == {
                "DLX4": "HGNC:2917",
                "PKD1": "HGNC:9008",
            }
        _alembic(url, "downgrade", "0015")
    _alembic(url, "upgrade", "head")
