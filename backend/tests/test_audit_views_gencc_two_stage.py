"""GenCC weight: quality, agreeing-submitter count and conflict penalty (#330)."""

import json
import math

import pytest
from sqlalchemy import text


def _subs(*pairs):
    return {
        "classifications": sorted({c for c, _ in pairs}),
        "submissions": [{"classification": c, "submitter": s} for c, s in pairs],
    }


CASES = {
    # Regression anchor: unchanged from the MAX view.
    "single": _subs(("Strong", "Orphanet")),
    "two_agree": _subs(("Strong", "Orphanet"), ("Strong", "G2P")),
    "three_agree": _subs(("Moderate", "Orphanet"), ("Moderate", "G2P"), ("Moderate", "Illumina")),
    # Same submitter twice (two diseases) counts once.
    "same_submitter_twice": _subs(("Strong", "Orphanet"), ("Strong", "Orphanet")),
    # ClinGen agrees but is not counted: n = 2, not 3.
    "clingen_not_counted": _subs(("Strong", "Orphanet"), ("Strong", "G2P"), ("Strong", "ClinGen")),
    # Top class only from ClinGen: n = 1, Q kept; others are 1 rank apart.
    "clingen_only_top": _subs(("Definitive", "ClinGen"), ("Strong", "Orphanet")),
    # ClinGen's Limited does not create a conflict among counted submitters.
    "clingen_no_conflict": _subs(("Strong", "Orphanet"), ("Strong", "G2P"), ("Limited", "ClinGen")),
    "conflict": _subs(("Strong", "Orphanet"), ("Limited", "G2P")),
    "one_rank_apart": _subs(("Strong", "Orphanet"), ("Strong", "G2P"), ("Moderate", "Illumina")),
    "agree_and_conflict": _subs(
        ("Definitive", "Orphanet"), ("Definitive", "G2P"), ("Limited", "Illumina")
    ),
    # Supportive (Orphanet/OMIM's ungraded term) is unranked: no conflict with Strong.
    "strong_and_orphanet_supportive": _subs(
        ("Strong", "Ambry Genetics"), ("Supportive", "Orphanet")
    ),
    # Definitive vs Moderate is 2 ranks apart: a conflict under the >= 2-rank rule.
    "definitive_vs_moderate": _subs(("Definitive", "Ambry Genetics"), ("Moderate", "G2P")),
    # Cannot differ from MAX (both 1.0); guards the min(1, ...) cap.
    "cap": _subs(*[("Definitive", f"Lab{i}") for i in range(4)]),
    # A submitter's strongest class is used: Strong+Limited from one submitter is no conflict.
    "within_submitter_spread": _subs(("Strong", "Orphanet"), ("Limited", "Orphanet")),
    # Unranked classes are ignored for agreement and conflict.
    "unknown_ignored": _subs(("Moderate", "Orphanet"), ("Not A Class", "G2P")),
    "floor_zero": _subs(("No Known Disease Relationship", "Orphanet"), ("", "G2P")),
    "legacy_no_submissions": {"classifications": ["Limited", "Definitive"]},
    "legacy_empty": {},
}
EXPECTED = {
    "single": 0.8,
    "two_agree": 0.8 * (1 + 0.1 * math.log(2)),
    "three_agree": 0.6 * (1 + 0.1 * math.log(3)),
    "same_submitter_twice": 0.8,
    "clingen_not_counted": 0.8 * (1 + 0.1 * math.log(2)),
    "clingen_only_top": 1.0,
    "clingen_no_conflict": 0.8 * (1 + 0.1 * math.log(2)),
    "conflict": 0.7,
    "one_rank_apart": 0.8 * (1 + 0.1 * math.log(2)),
    "agree_and_conflict": 0.9,  # capped at 1.0 before the penalty
    "strong_and_orphanet_supportive": 0.8,
    "definitive_vs_moderate": 0.9,
    "cap": 1.0,
    "within_submitter_spread": 0.8,
    "unknown_ignored": 0.6,
    "floor_zero": 0.0,
    "legacy_no_submissions": 1.0,
    "legacy_empty": 0.0,
}


@pytest.mark.integration
def test_gencc_two_stage_weight(db_session):
    ids = {}
    for i, (name, data) in enumerate(CASES.items()):
        gene_id = db_session.execute(
            text(
                "INSERT INTO genes (hgnc_id, approved_symbol, aliases) "
                "VALUES (:h, :s, '{}') RETURNING id"
            ),
            {"h": f"HGNC:AUDIT330{i}", "s": f"AUDIT330_{name.upper()}"},
        ).scalar_one()
        ids[name] = db_session.execute(
            text(
                "INSERT INTO gene_evidence (gene_id, source_name, source_detail, evidence_data) "
                "VALUES (:g, 'GenCC', 'audit', CAST(:d AS jsonb)) RETURNING id"
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
    got = {name: weights[eid] for name, eid in ids.items()}
    assert got == pytest.approx(EXPECTED, abs=1e-9)

    # The scored breakdown follows the new weight.
    normalized = db_session.execute(
        text("SELECT normalized_score FROM combined_evidence_scores WHERE evidence_id = :e"),
        {"e": ids["two_agree"]},
    ).scalar_one()
    assert float(normalized) == pytest.approx(EXPECTED["two_agree"], abs=1e-9)
