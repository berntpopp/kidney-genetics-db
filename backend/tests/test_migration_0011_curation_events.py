"""Migration 0011: every existing curated record starts its trace with an 'import' event (#376)."""

import pytest
from sqlalchemy import text

from tests.test_audit_migration_views import (
    _add_gene,
    _alembic,
    baseline_db,  # noqa: F401 - fixture
)
from tests.test_migration_gene_disease_associations import INSERT, _user


@pytest.mark.integration
def test_0011_backfills_one_import_event_per_record(baseline_db):  # noqa: F811
    engine, url = baseline_db
    _alembic(url, "upgrade", "0010")
    with engine.begin() as conn:
        gene, curator, reviewer = _add_gene(conn, "EVT11"), _user(conn, "c11"), _user(conn, "r11")
        conn.execute(
            INSERT,
            {
                "g": gene,
                "d": "MONDO:0005300",
                "c": '["PMID:1"]',
                "u": curator,
                "s": "published",
                "r": reviewer,
                "p": "2026-10-01",
            },
        )

    _alembic(url, "upgrade", "0011")
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT action, user_id, snapshot->>'status' FROM gene_disease_association_events")
        ).all()
        assert rows == [("import", curator, "published")]

    _alembic(url, "downgrade", "0010")
    with engine.begin() as conn:
        gone = conn.execute(text("SELECT to_regclass('gene_disease_association_events')"))
        assert gone.scalar() is None
        assert conn.execute(text("SELECT count(*) FROM gene_disease_associations")).scalar() == 1
    _alembic(url, "upgrade", "head")
