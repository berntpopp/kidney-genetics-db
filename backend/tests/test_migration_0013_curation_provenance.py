"""Migration 0013: relationship type, MOI, provenance and diagnostics columns (#437)."""

import subprocess

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.test_audit_migration_views import (
    _add_gene,
    _alembic,
    baseline_db,  # noqa: F401 - fixture
)
from tests.test_migration_gene_disease_associations import INSERT, _user

NEW = text(
    "INSERT INTO gene_disease_associations (gene_id, disease_id, disease_name,"
    " evidence_strength, citations, curator_id, relationship_type, moi, source, external_id,"
    " external_url, scores) VALUES (:g, :d, 'x', :st, '[\"PMID:1\"]', :u, :rt, :moi, :src,"
    " :xid, :xurl, CAST(:sc AS jsonb))"
)


def _row(**kw):
    return {
        "d": "MONDO:0005300",
        "st": "Strong",
        "rt": "mendelian",
        "moi": None,
        "src": "kgdb",
        "xid": None,
        "xurl": None,
        "sc": None,
        **kw,
    }


@pytest.fixture
def db_0013(baseline_db):  # noqa: F811
    engine, url = baseline_db
    _alembic(url, "upgrade", "0013")
    with engine.begin() as conn:
        gene, user = _add_gene(conn, "PRV13"), _user(conn, "c13")
    return engine, url, gene, user


@pytest.mark.integration
def test_0013_keeps_existing_rows(baseline_db):  # noqa: F811
    engine, url = baseline_db
    _alembic(url, "upgrade", "0012")
    with engine.begin() as conn:
        gene, curator, reviewer = _add_gene(conn, "KEEP13"), _user(conn, "k13"), _user(conn, "r13")
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
    _alembic(url, "upgrade", "0013")
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT status, reviewer_id, relationship_type, source, moi, methodology,"
                " external_id, scores, diagnostics, evidence_strength"
                " FROM gene_disease_associations WHERE gene_id = :g"
            ),
            {"g": gene},
        ).one()
    assert tuple(row) == (
        "published",
        reviewer,
        "mendelian",
        "kgdb",
        None,
        None,
        None,
        None,
        None,
        "Strong",
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "bad",
    [
        {"rt": "susceptibility", "st": "Strong"},
        {"st": "Likely association"},
        {"rt": "polygenic"},
        {"moi": "HP:6"},
        {"src": "gene_curator"},
        {"src": "gene_curator", "xid": "GC-1", "xurl": "javascript:alert(1)"},
        {"xurl": "javascript:alert(1)"},
        {"src": "elsewhere"},
        {"sc": "[1]"},
    ],
)
def test_0013_rejects_invalid_rows(db_0013, bad):
    engine, _, gene, user = db_0013
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(**bad)})


@pytest.mark.integration
def test_0013_accepts_new_vocabulary_and_moi_split(db_0013):
    engine, _, gene, user = db_0013
    with engine.begin() as conn:
        for row in (
            _row(moi="HP:0000006"),
            _row(moi="HP:0000007"),
            _row(d="MONDO:0000001", st="No Known Disease Relationship"),
            _row(d="MONDO:0000002", rt="susceptibility", st="Likely association"),
            _row(
                d="MONDO:0000003",
                src="gene_curator",
                xid="GC-1",
                xurl="https://example.org/c/1",
                sc='{"total": 12}',
            ),
        ):
            conn.execute(NEW, {"g": gene, "u": user, **row})


@pytest.mark.integration
@pytest.mark.parametrize("moi", [None, "HP:0000006"])
def test_0013_unique_per_gene_disease_moi(db_0013, moi):
    engine, _, gene, user = db_0013
    with engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(moi=moi)})
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(moi=moi)})


@pytest.mark.integration
def test_0013_external_id_unique_per_source(db_0013):
    engine, _, gene, user = db_0013
    gc = {"src": "gene_curator", "xid": "GC-9", "xurl": "https://example.org/c/9"}
    with engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(**gc)})
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(d="MONDO:0000009", **gc)})


@pytest.mark.integration
def test_0013_downgrade_restores_gene_disease_key(db_0013):
    engine, url, gene, user = db_0013
    with engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row()})
    _alembic(url, "downgrade", "0012")
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            INSERT,
            {
                "g": gene,
                "d": "MONDO:0005300",
                "c": '["PMID:2"]',
                "u": user,
                "s": "draft",
                "r": None,
                "p": None,
            },
        )


@pytest.mark.integration
def test_0013_downgrade_refuses_to_drop_susceptibility(db_0013):
    engine, url, gene, user = db_0013
    with engine.begin() as conn:
        conn.execute(
            NEW, {"g": gene, "u": user, **_row(rt="susceptibility", st="Likely association")}
        )
    with pytest.raises(subprocess.CalledProcessError) as err:
        _alembic(url, "downgrade", "0012")
    assert b"susceptibility" in err.value.stderr


@pytest.mark.integration
@pytest.mark.parametrize(
    "row",
    [
        {"moi": "HP:0000006"},
        {"src": "gene_curator", "xid": "GC-2", "xurl": "https://example.org/c/2"},
        {"sc": '{"total": 12}'},
    ],
)
def test_0013_downgrade_refuses_to_drop_moi_provenance_or_points(db_0013, row):
    engine, url, gene, user = db_0013
    with engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(**row)})
    with pytest.raises(subprocess.CalledProcessError) as err:
        _alembic(url, "downgrade", "0012")
    assert b"provenance" in err.value.stderr


# --- 0018: relationship type joins the key (#472) ---

SUSCEPTIBLE = {"rt": "susceptibility", "st": "Likely association"}


@pytest.fixture
def db_0018(db_0013):
    engine, url, gene, user = db_0013
    _alembic(url, "upgrade", "0018")
    return engine, url, gene, user


@pytest.mark.integration
@pytest.mark.parametrize("moi", [None, "HP:0000006"])
def test_0018_mendelian_and_susceptibility_coexist(db_0018, moi):
    engine, _, gene, user = db_0018
    with engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(moi=moi)})
        conn.execute(NEW, {"g": gene, "u": user, **_row(moi=moi, **SUSCEPTIBLE)})
    for rt in ({}, SUSCEPTIBLE):  # same-type duplicates still collide
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(NEW, {"g": gene, "u": user, **_row(moi=moi, **rt)})


@pytest.mark.integration
def test_0018_downgrade_refuses_to_merge_relationship_types(db_0018):
    engine, url, gene, user = db_0018
    with engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row()})
        conn.execute(NEW, {"g": gene, "u": user, **_row(**SUSCEPTIBLE)})
    with pytest.raises(subprocess.CalledProcessError) as err:
        _alembic(url, "downgrade", "0017")
    assert b"relationship type" in err.value.stderr


@pytest.mark.integration
def test_0018_downgrade_restores_gene_disease_moi_key(db_0018):
    engine, url, gene, user = db_0018
    with engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(moi="HP:0000006")})
    _alembic(url, "downgrade", "0017")
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(moi="HP:0000006", **SUSCEPTIBLE)})


# --- 0019: Refuted association (#473) ---

REFUTED = {"rt": "susceptibility", "st": "Refuted association"}


@pytest.mark.integration
def test_0019_accepts_refuted_association_for_susceptibility_only(db_0018):
    engine, url, gene, user = db_0018
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(**REFUTED)})
    _alembic(url, "upgrade", "0019")
    with engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(**REFUTED)})
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(st="Refuted association")})


@pytest.mark.integration
def test_0019_downgrade_refuses_while_refuted_association_is_used(db_0018):
    engine, url, gene, user = db_0018
    _alembic(url, "upgrade", "0019")
    with engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(**REFUTED)})
    with pytest.raises(subprocess.CalledProcessError) as err:
        _alembic(url, "downgrade", "0018")
    assert b"Refuted association" in err.value.stderr
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gene_disease_associations"))
    _alembic(url, "downgrade", "0018")
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(NEW, {"g": gene, "u": user, **_row(**REFUTED)})


ALLELE = text(
    "INSERT INTO gene_disease_associations (gene_id, disease_id, disease_name, evidence_strength,"
    " citations, curator_id, relationship_type, source, external_id, external_url, risk_allele,"
    " ai_agents) VALUES (:g, 'MONDO:0013860', 'x', 'Likely association', '[\"PMID:1\"]', :u,"
    " 'susceptibility', 'gene_curator', :xid, 'https://gc.example/c', :allele,"
    " CAST(:ai AS jsonb))"
)


@pytest.mark.integration
def test_0020_keys_alleles_and_guards_its_downgrade(db_0018):
    engine, url, gene, user = db_0018
    _alembic(url, "upgrade", "0020")
    row = {"g": gene, "u": user, "ai": None}
    with engine.begin() as conn:  # two alleles of one gene, disease and MOI are two entities
        conn.execute(ALLELE, {**row, "xid": "a", "allele": "rs1 A"})
        conn.execute(ALLELE, {**row, "xid": "b", "allele": "rs2 G"})
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(ALLELE, {**row, "xid": "c", "allele": "rs1 A"})
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gene_disease_associations"))
        conn.execute(ALLELE, {**row, "xid": "d", "allele": None, "ai": '["model-x"]'})
    with pytest.raises(subprocess.CalledProcessError) as err:  # never drop AI credit silently
        _alembic(url, "downgrade", "0019")
    assert b"credit AI" in err.value.stderr
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gene_disease_associations"))
    _alembic(url, "downgrade", "0019")


# --- 0021: headline odds ratio of a susceptibility record (#482) ---

ODDS = text(
    "INSERT INTO gene_disease_associations (gene_id, disease_id, disease_name, evidence_strength,"
    " citations, curator_id, relationship_type, odds_ratio, odds_ratio_ci_low,"
    " odds_ratio_ci_high) VALUES (:g, :d, 'x', :st, '[\"PMID:1\"]', :u, :rt, :v, :lo, :hi)"
)


@pytest.mark.integration
def test_0021_odds_ratio_check_and_downgrade(db_0018):
    engine, url, gene, user = db_0018
    _alembic(url, "upgrade", "0021")
    ok = {"g": gene, "u": user, "d": "MONDO:0000001", **SUSCEPTIBLE, "v": 1.6}
    ok |= {"lo": None, "hi": None}
    with engine.begin() as conn:
        conn.execute(ODDS, ok)
        conn.execute(ODDS, {**ok, "d": "MONDO:0000002", "lo": 1.2, "hi": 2.1})
    for bad in (
        {"rt": "mendelian", "st": "Strong"},
        {"v": 0},
        {"v": None, "lo": 1.0, "hi": 2.0},
        {"lo": 1.2},  # one bound only
        {"lo": 1.7, "hi": 2.1},  # value outside its CI
    ):
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(ODDS, {**ok, "d": "MONDO:0000003", **bad})
    with pytest.raises(subprocess.CalledProcessError) as err:
        _alembic(url, "downgrade", "0020")
    assert b"odds ratio" in err.value.stderr
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gene_disease_associations"))
    _alembic(url, "downgrade", "0020")
