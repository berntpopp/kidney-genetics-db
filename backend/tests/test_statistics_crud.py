"""Tests for statistics CRUD operations."""

import pytest

from app.crud.statistics import statistics_crud


@pytest.mark.integration
class TestGetPairwiseOverlapsFromView:
    """Tests for get_pairwise_overlaps_from_view method."""

    def test_returns_list(self, db_session):
        """Method returns a list (may be empty if view has no data)."""
        result = statistics_crud.get_pairwise_overlaps_from_view(db_session)
        assert isinstance(result, list)

    def test_row_structure(self, db_session):
        """Each row has the expected keys if data exists."""
        result = statistics_crud.get_pairwise_overlaps_from_view(db_session)
        if len(result) > 0:
            row = result[0]
            assert "source1" in row
            assert "source2" in row
            assert "overlap_count" in row
            assert "source1_total" in row
            assert "source2_total" in row
            assert "overlap_percentage" in row

    def test_no_duplicate_pairs(self, db_session):
        """No (source1, source2) pair appears more than once."""
        result = statistics_crud.get_pairwise_overlaps_from_view(db_session)
        pairs = [(r["source1"], r["source2"]) for r in result]
        assert len(pairs) == len(set(pairs))

    def test_source1_less_than_source2(self, db_session):
        """source1 is always alphabetically before source2 (no duplicates)."""
        result = statistics_crud.get_pairwise_overlaps_from_view(db_session)
        for row in result:
            assert row["source1"] < row["source2"]
