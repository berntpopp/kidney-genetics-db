"""ClinGen weight uses the strongest classification regardless of array order (#279)."""

import json

import pytest
from sqlalchemy import text

CASES = {
    "limited_first": {"classifications": ["Limited", "Definitive"]},
    "definitive_first": {"classifications": ["Definitive", "Limited"]},
    "repeated": {"classifications": ["Limited", "Definitive", "Limited", "Definitive"]},
    "single": {"classifications": ["Moderate"]},
    "scalar": {"classification": "Strong"},
    "empty": {"classifications": []},
    "absent": {},
    "unknown": {"classifications": ["Not A Class"]},
    "unknown_plus_limited": {"classifications": ["Not A Class", "Limited"]},
    "nkdr": {"classifications": ["No Known Disease Relationship*"]},
}
EXPECTED = {
    "limited_first": 1.0,
    "definitive_first": 1.0,
    "repeated": 1.0,
    "single": 0.6,
    "scalar": 0.8,
    "empty": 0.0,
    "absent": 0.0,
    "unknown": 0.0,
    "unknown_plus_limited": 0.4,
    "nkdr": 0.0,
}


@pytest.mark.integration
def test_clingen_weight_is_order_independent_max(db_session):
    ids = {}
    for i, (name, data) in enumerate(CASES.items()):
        gene_id = db_session.execute(
            text(
                "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
                "VALUES (:h, :s, '{}') RETURNING id"
            ),
            {"h": f"HGNC:AUDIT279{i}", "s": f"AUDIT279_{name.upper()}"},
        ).scalar_one()
        ids[name] = db_session.execute(
            text(
                "INSERT INTO gene_evidence (gene_id, source_name, source_detail, evidence_data) "
                "VALUES (:g, 'ClinGen', 'audit', CAST(:d AS jsonb)) RETURNING id"
            ),
            {"g": gene_id, "d": json.dumps(data)},
        ).scalar_one()
    db_session.flush()

    rows = db_session.execute(
        text(
            "SELECT evidence_id, classification_weight FROM evidence_classification_weights "
            "WHERE evidence_id = ANY(:ids)"
        ),
        {"ids": list(ids.values())},
    ).all()
    weights = {eid: float(w) for eid, w in rows}
    assert {name: weights[eid] for name, eid in ids.items()} == EXPECTED

    # The scored breakdown (normalized score) follows the corrected weight.
    normalized = db_session.execute(
        text("SELECT normalized_score FROM combined_evidence_scores WHERE evidence_id = :e"),
        {"e": ids["limited_first"]},
    ).scalar_one()
    assert float(normalized) == 1.0
