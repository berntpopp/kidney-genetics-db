"""Migration 0006 rescores GenCC two-stage; downgrade restores the MAX view (#330)."""

import math

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
            text("SELECT source_scores->>'GenCC' FROM gene_scores WHERE approved_symbol = 'G330'")
        ).scalar_one()
    )


@pytest.mark.integration
def test_upgrade_rescores_gencc_and_downgrade_restores_max(baseline_db):  # noqa: F811
    engine, url = baseline_db
    _alembic(url, "upgrade", "0005")
    data = {
        "classifications": ["Strong"],
        "submissions": [
            {"classification": "Strong", "submitter": "Orphanet"},
            {"classification": "Strong", "submitter": "G2P"},
        ],
    }
    with engine.begin() as conn:
        _add_evidence(conn, _add_gene(conn, "G330"), "GenCC", data)
        conn.execute(text("REFRESH MATERIALIZED VIEW gene_scores"))
        assert _gencc(conn) == 0.8
        max_viewdef = conn.execute(text(VIEWDEF)).scalar_one()

    _alembic(url, "upgrade", "head")
    with engine.begin() as conn:
        # gene_scores rounds source scores to 4 decimals
        assert _gencc(conn) == round(0.8 * (1 + 0.1 * math.log(2)), 4)
        _assert_view_matches_canonical(conn, views.evidence_classification_weights)
        stored = conn.execute(
            text("SELECT evidence_data FROM gene_evidence WHERE source_name = 'GenCC'")
        ).scalar_one()
        assert stored == data  # evidence untouched

    _alembic(url, "downgrade", "0005")
    with engine.begin() as conn:
        assert conn.execute(text(VIEWDEF)).scalar_one() == max_viewdef
        assert _gencc(conn) == 0.8
