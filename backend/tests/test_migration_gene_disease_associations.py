"""Migration 0007 adds gene_disease_associations without touching evidence (#26).

Uses a disposable sibling database (<test db>_gda); skipped when the role
cannot create databases.
"""

import pytest
from sqlalchemy import create_engine, exc, text
from sqlalchemy.engine import make_url

from tests.test_audit_migration_views import _add_evidence, _add_gene, _alembic

INSERT = text(
    "INSERT INTO gene_disease_associations "
    "(gene_id, disease_id, disease_name, evidence_strength, citations, curator_id, status,"
    " reviewer_id, published_at) "
    "VALUES (:g, :d, 'x', 'Strong', CAST(:c AS jsonb), :u, :s, :r, :p)"
)


@pytest.fixture
def db_0006():
    from tests.conftest import get_test_database_url

    base = make_url(get_test_database_url())
    url = base.set(database=f"{base.database}_gda")
    admin = create_engine(base, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    except Exception as e:  # noqa: BLE001 - no server or no CREATEDB privilege
        admin.dispose()
        pytest.skip(f"cannot create disposable database: {type(e).__name__}")
    url_str = url.render_as_string(hide_password=False)
    _alembic(url_str, "upgrade", "0006")
    engine = create_engine(url)
    try:
        yield engine, url_str
    finally:
        engine.dispose()
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
        admin.dispose()


def _evidence(conn) -> list:
    return conn.execute(text("SELECT * FROM gene_evidence ORDER BY id")).all()


def _user(conn, name: str) -> int:
    return conn.execute(
        text(
            "INSERT INTO users (email, username, hashed_password, role, is_active, is_verified,"
            " failed_login_attempts) VALUES (:e, :n, 'x', 'curator', true, true, 0) RETURNING id"
        ),
        {"e": f"{name}@example.com", "n": name},
    ).scalar_one()


@pytest.mark.integration
def test_upgrade_downgrade_preserves_evidence(db_0006) -> None:
    engine, url = db_0006
    with engine.begin() as conn:
        gene = _add_gene(conn, "GDAMIG1")
        _add_evidence(conn, gene, "ClinGen", {"classifications": ["Definitive"]})
        author, reviewer = _user(conn, "mig_a"), _user(conn, "mig_r")
        before = _evidence(conn)

    _alembic(url, "upgrade", "0007")
    ok = {"g": gene, "u": author, "s": "draft", "r": None, "p": None, "c": '["PMID:1"]'}
    with engine.begin() as conn:
        assert _evidence(conn) == before
        conn.execute(INSERT, {**ok, "d": "MONDO:0005300"})
        conn.execute(INSERT, {**ok, "d": "OMIM:137920", "c": '["PMID:1", "PMID:22"]'})
        assert conn.execute(text("SELECT count(*) FROM gene_disease_associations")).scalar() == 2

    bad = [
        {"d": "HP:0000083"},
        {"d": "MONDO:0005301", "c": "[]"},
        {"d": "MONDO:0005301", "c": '["12345"]'},
        {"d": "MONDO:0005300"},  # duplicate gene/disease
        {"d": "MONDO:0005301", "r": author},  # reviewer == curator
        {"d": "MONDO:0005301", "s": "published"},  # published without reviewer
        {"d": "MONDO:0005301", "s": "published", "r": reviewer},  # no published_at
    ]
    for override in bad:
        with pytest.raises(exc.IntegrityError), engine.begin() as conn:
            conn.execute(INSERT, {**ok, **override})

    _alembic(url, "downgrade", "0006")
    with engine.begin() as conn:
        assert _evidence(conn) == before
        assert (
            conn.execute(text("SELECT to_regclass('gene_disease_associations')")).scalar() is None
        )
    _alembic(url, "upgrade", "0007")
