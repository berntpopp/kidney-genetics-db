"""Migration 0008 applies DiStefano Level 3 GenCC conflicts; downgrade restores 0006 (#330)."""

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

VIEWDEF = "SELECT pg_get_viewdef('evidence_classification_weights'::regclass)"


def _gencc(conn) -> float:
    return float(
        conn.execute(
            text("SELECT source_scores->>'GenCC' FROM gene_scores WHERE approved_symbol = 'G330D'")
        ).scalar_one()
    )


@pytest.mark.integration
def test_upgrade_applies_distefano_conflict_and_downgrade_restores_0006(baseline_db):  # noqa: F811
    engine, url = baseline_db
    _alembic(url, "upgrade", "0007")
    # Definitive AR vs Limited AD: a conflict under 0006's >= 2-rank rule, not at Level 3.
    data = {
        "classifications": ["Definitive", "Limited"],
        "submissions": [
            {
                "classification": "Definitive",
                "submitter": "G2P",
                "raw_data": {"disease_curie": "MONDO:0000001", "moi_curie": "HP:0000007"},
            },
            {
                "classification": "Limited",
                "submitter": "Ambry Genetics",
                "raw_data": {"disease_curie": "MONDO:0000001", "moi_curie": "HP:0000006"},
            },
        ],
    }
    with engine.begin() as conn:
        _add_evidence(conn, _add_gene(conn, "G330D"), "GenCC", data)
        conn.execute(text("REFRESH MATERIALIZED VIEW gene_scores"))
        assert _gencc(conn) == 0.9
        v0006_viewdef = conn.execute(text(VIEWDEF)).scalar_one()

    _alembic(url, "upgrade", "0008")
    with engine.begin() as conn:
        assert _gencc(conn) == 1.0
        _assert_view_matches_canonical(conn, views.evidence_classification_weights)
        stored = conn.execute(
            text("SELECT evidence_data FROM gene_evidence WHERE source_name = 'GenCC'")
        ).scalar_one()
        assert stored == data  # evidence untouched

    _alembic(url, "downgrade", "0007")
    with engine.begin() as conn:
        assert conn.execute(text(VIEWDEF)).scalar_one() == v0006_viewdef
        assert _gencc(conn) == 0.9
