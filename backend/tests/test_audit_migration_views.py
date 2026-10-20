"""Upgrade an existing 0001 database to head and check corrected view results.

Creates a disposable sibling database (<test db>_upg); skipped when the test
database is unreachable or the role cannot create databases.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.db import views

BACKEND = Path(__file__).resolve().parents[1]


def _alembic(url: str, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": url}
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def baseline_db():
    """A fresh database migrated to 0001 only; dropped afterwards."""
    from tests.conftest import get_test_database_url

    base = make_url(get_test_database_url())
    url = base.set(database=f"{base.database}_upg")
    admin = create_engine(base, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    except Exception as e:  # noqa: BLE001 - no server or no CREATEDB privilege
        admin.dispose()
        pytest.skip(f"cannot create disposable database: {type(e).__name__}")
    url_str = url.render_as_string(hide_password=False)
    _alembic(url_str, "upgrade", "0001")
    engine = create_engine(url)
    try:
        yield engine, url_str
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        admin.dispose()


def _add_gene(conn, symbol: str) -> int:
    return conn.execute(
        text(
            "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
            "VALUES (:h, :s, '{}') RETURNING id"
        ),
        {"h": f"HGNC:{symbol}", "s": symbol},
    ).scalar_one()


def _add_evidence(conn, gene_id: int, source: str, data: dict) -> int:
    return conn.execute(
        text(
            "INSERT INTO gene_evidence (gene_id, source_name, source_detail, evidence_data) "
            "VALUES (:g, :s, 'audit', CAST(:d AS jsonb)) RETURNING id"
        ),
        {"g": gene_id, "s": source, "d": json.dumps(data)},
    ).scalar_one()


def _clingen_scores(conn) -> dict[str, float]:
    rows = conn.execute(
        text("SELECT approved_symbol, source_scores->>'ClinGen' FROM gene_scores")
    ).all()
    return {sym: float(score) for sym, score in rows}


def _assert_view_matches_canonical(conn, view) -> None:
    """The migrated view must deparse identically to the canonical app.db.views text."""
    conn.execute(text(f"CREATE TEMP VIEW audit_canonical AS {view.sqltext}"))
    migrated, canonical = conn.execute(
        text(
            "SELECT pg_get_viewdef(CAST(:v AS regclass)), "
            "pg_get_viewdef(CAST('audit_canonical' AS regclass))"
        ),
        {"v": view.name},
    ).one()
    conn.execute(text("DROP VIEW audit_canonical"))
    assert migrated == canonical


@pytest.mark.integration
def test_upgrade_rescores_existing_clingen_arrays(baseline_db):
    engine, url = baseline_db
    arrays = {
        "AUDITUPG_LD": ["Limited", "Definitive"],
        "AUDITUPG_DL": ["Definitive", "Limited"],
    }
    with engine.begin() as conn:
        for symbol, classes in arrays.items():
            _add_evidence(conn, _add_gene(conn, symbol), "ClinGen", {"classifications": classes})
        conn.execute(text("REFRESH MATERIALIZED VIEW gene_scores"))
        assert _clingen_scores(conn) == {"AUDITUPG_LD": 0.4, "AUDITUPG_DL": 1.0}

    _alembic(url, "upgrade", "head")
    with engine.begin() as conn:
        assert _clingen_scores(conn) == {"AUDITUPG_LD": 1.0, "AUDITUPG_DL": 1.0}
        stored = dict(
            conn.execute(
                text(
                    "SELECT g.approved_symbol, ge.evidence_data->'classifications' "
                    "FROM gene_evidence ge JOIN genes g ON g.id = ge.gene_id"
                )
            ).all()
        )
        assert stored == arrays  # original assessments untouched
        _assert_view_matches_canonical(conn, views.evidence_classification_weights)

    _alembic(url, "downgrade", "0001")
    with engine.begin() as conn:
        assert _clingen_scores(conn)["AUDITUPG_LD"] == 0.4
    _alembic(url, "upgrade", "head")
    with engine.begin() as conn:
        assert _clingen_scores(conn)["AUDITUPG_LD"] == 1.0


@pytest.mark.integration
def test_upgrade_keeps_unassessed_hpo_null(baseline_db):
    engine, url = baseline_db
    with engine.begin() as conn:
        _add_gene(conn, "AUDITUPG_NOHPO")
        assessed = _add_gene(conn, "AUDITUPG_HPO")
        conn.execute(
            text(
                "INSERT INTO gene_annotations (gene_id, source, version, annotations) "
                "VALUES (:g, 'hpo', 'audit', "
                '\'{"classification": {"syndromic_assessment": {"is_syndromic": false}}}\')'
            ),
            {"g": assessed},
        )

    def syndromic(conn):
        return dict(
            conn.execute(
                text("SELECT gene_symbol, is_syndromic FROM gene_hpo_classifications")
            ).all()
        )

    with engine.begin() as conn:
        assert syndromic(conn) == {"AUDITUPG_NOHPO": False, "AUDITUPG_HPO": False}
    _alembic(url, "upgrade", "head")
    with engine.begin() as conn:
        assert syndromic(conn) == {"AUDITUPG_NOHPO": None, "AUDITUPG_HPO": False}
        _assert_view_matches_canonical(conn, views.gene_hpo_classifications)
    _alembic(url, "downgrade", "0002")
    with engine.begin() as conn:
        assert syndromic(conn)["AUDITUPG_NOHPO"] is False
    _alembic(url, "upgrade", "head")
    with engine.begin() as conn:
        assert syndromic(conn)["AUDITUPG_NOHPO"] is None
