"""Pin the ClinGen branch of evidence_classification_weights to best-element scoring.

The view used to score `(evidence_data -> 'classifications') ->> 0` — whatever
element the set-to-list conversion stored first — so DNAJB11 (Limited +
Definitive) could score 0.4 instead of 1.0 (#279). It must score the best
element of the array, as the GenCC branch already does, and fall back to the
scalar `classification` only when no array exists. These tests pin the SQL
text without needing a database.
"""
import pytest

from app.db.views import evidence_classification_weights

SQL = evidence_classification_weights.sqltext


@pytest.mark.unit
class TestClinGenWeightsView:
    def test_clingen_branch_scores_the_best_element(self):
        assert "FROM jsonb_array_elements" in SQL
        assert "(SELECT MAX(" in SQL

    def test_clingen_branch_no_longer_reads_element_zero(self):
        clingen_part = SQL.split("clingen_weights AS (")[1]
        assert "->> 0" not in clingen_part

    def test_scalar_classification_fallback_is_kept(self):
        clingen_part = SQL.split("clingen_weights AS (")[1]
        assert "WHEN (ge.evidence_data ->> 'classification'::text) IS NOT NULL THEN" in clingen_part

    def test_non_array_evidence_uses_an_empty_array_not_the_first_element(self):
        # When 'classifications' is not an array, the elements source is empty
        # (MAX is NULL), so the scalar fallback applies instead of an error.
        clingen_part = SQL.split("clingen_weights AS (")[1]
        assert "ELSE '[]'::jsonb" in clingen_part
