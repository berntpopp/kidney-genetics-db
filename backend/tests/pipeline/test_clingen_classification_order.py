"""The stored ClinGen classifications array must be ordered deterministically.

`process_data` collects classifications in a Python set and used to convert it
straight to a list, so the stored order was arbitrary: DNAJB11, curated both
Limited and Definitive, could store Limited first and score 0.4 wherever
element 0 is read (issue #279). The order must be best-first and stable.
"""
import pytest

from app.pipeline.sources.unified.clingen import sort_classifications_best_first

WEIGHTS = {
    "Definitive": 1.0,
    "Strong": 0.8,
    "Moderate": 0.6,
    "Limited": 0.4,
    "Disputed": 0.2,
}


@pytest.mark.unit
class TestSortClassificationsBestFirst:
    def test_definitive_is_stored_before_limited(self):
        # The exact case from #279: Definitive must win regardless of the
        # set's iteration order.
        classifications = sort_classifications_best_first(
            {"Limited", "Definitive"}, WEIGHTS
        )

        assert classifications == ["Definitive", "Limited"]

    def test_order_is_deterministic_across_set_orders(self):
        first = sort_classifications_best_first({"Limited", "Definitive", "Moderate"}, WEIGHTS)
        second = sort_classifications_best_first({"Moderate", "Limited", "Definitive"}, WEIGHTS)

        assert first == second == ["Definitive", "Moderate", "Limited"]

    def test_ties_are_broken_by_name(self):
        # Same weight (0.0 for unknowns) — still a stable, reproducible order.
        classifications = sort_classifications_best_first({"zebra", "alpha"}, WEIGHTS)

        assert classifications == ["alpha", "zebra"]

    def test_single_classification_is_kept(self):
        assert sort_classifications_best_first({"Limited"}, WEIGHTS) == ["Limited"]

    def test_empty_set_gives_empty_list(self):
        assert sort_classifications_best_first(set(), WEIGHTS) == []
