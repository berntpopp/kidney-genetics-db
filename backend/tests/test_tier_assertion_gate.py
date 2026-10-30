"""Established support needs an assertion source; HPO counts most-specific terms (#450)."""

import pytest
from sqlalchemy import text

from app.db import views
from app.pipeline.sources.unified.hpo import most_specific_terms
from tests.test_audit_migration_views import (  # noqa: F401 - baseline_db is a fixture
    _add_evidence,
    _add_gene,
    _alembic,
    _assert_view_matches_canonical,
    baseline_db,
)


@pytest.mark.unit
def test_deep_term_and_its_ancestors_count_once():
    # Renal artery stenosis -> Abnormal renal artery morphology -> Abnormality of the kidney
    parents = {
        "HP:0001920": {"HP:0008776"},
        "HP:0008776": {"HP:0000077"},
        "HP:0000077": {"HP:0010935"},
        "HP:0000107": {"HP:0000077"},
    }
    terms = [{"id": t} for t in ("HP:0000077", "HP:0001920", "HP:0008776", "HP:0010935")]
    assert most_specific_terms(terms, parents) == [{"id": "HP:0001920"}]
    # A sibling leaf is independent and kept; a term missing from the ontology is kept
    terms += [{"id": "HP:0000107"}, {"id": "HP:9999999"}]
    assert [t["id"] for t in most_specific_terms(terms, parents)] == [
        "HP:0001920",
        "HP:0000107",
        "HP:9999999",
    ]


TIER_COUNTS = "SELECT evidence_tier, count(*) AS n FROM gene_scores GROUP BY evidence_tier"


def _scores(conn) -> dict[str, tuple]:
    rows = conn.execute(
        text(
            "SELECT approved_symbol, evidence_tier, evidence_group, round(percentage_score::numeric, 2) "
            "FROM gene_scores"
        )
    ).all()
    return {r[0]: tuple(r[1:]) for r in rows}


@pytest.mark.integration
def test_soft_only_gene_caps_at_preliminary(baseline_db):  # noqa: F811
    engine, url = baseline_db
    _alembic(url, "upgrade", "0013")
    hpo = {"hpo_terms": [f"HP:{i:07d}" for i in range(20)]}
    with engine.begin() as conn:
        soft = _add_gene(conn, "G450SOFT")  # LDLR-like: HPO + PubTator only
        _add_evidence(conn, soft, "HPO", hpo)
        _add_evidence(conn, soft, "PubTator", {"publication_count": 140})
        both = _add_gene(conn, "G450PANEL")  # same soft scores plus one assertion source
        _add_evidence(conn, both, "HPO", hpo)
        _add_evidence(conn, both, "PubTator", {"publication_count": 140})
        _add_evidence(conn, both, "PanelApp", {"panels": [{"id": 1}]})
        conn.execute(text("REFRESH MATERIALIZED VIEW gene_scores"))
        before = _scores(conn)
        # Ad hoc dependent matview (production-like) must survive the drop and recreate
        conn.execute(text(f"CREATE MATERIALIZED VIEW g450_dep AS {TIER_COUNTS}"))
        conn.execute(text("CREATE UNIQUE INDEX g450_dep_tier ON g450_dep (evidence_tier)"))
    assert before["G450SOFT"][:2] == ("established_support", "well_supported")

    _alembic(url, "upgrade", "0014")
    with engine.begin() as conn:
        after = _scores(conn)
        _assert_view_matches_canonical(conn, views.gene_scores)
        assert conn.execute(text("SELECT count(*) FROM gene_list_detailed")).scalar_one() == 2
        assert set(conn.execute(text("SELECT * FROM g450_dep")).all()) == {
            ("preliminary_evidence", 1),
            ("multi_source_support", 1),
        }
        conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY g450_dep"))  # index kept
    assert after["G450SOFT"] == ("preliminary_evidence", "emerging_evidence", before["G450SOFT"][2])
    assert after["G450PANEL"] == before["G450PANEL"]
    assert after["G450PANEL"][:2] == ("multi_source_support", "well_supported")

    _alembic(url, "downgrade", "0013")
    with engine.begin() as conn:
        assert _scores(conn) == before
        assert (
            conn.execute(
                text("SELECT count(*) FROM g450_dep WHERE evidence_tier = 'established_support'")
            ).scalar_one()
            == 1
        )
    _alembic(url, "upgrade", "head")
