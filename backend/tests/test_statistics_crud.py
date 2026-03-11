"""Tests for statistics CRUD operations."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.crud.statistics import statistics_crud


def _view_exists(db_session) -> bool:
    """Check if the source_overlap_statistics materialized view exists."""
    try:
        db_session.execute(text("SELECT 1 FROM source_overlap_statistics LIMIT 0"))
        return True
    except ProgrammingError:
        db_session.rollback()
        return False


@pytest.mark.integration
class TestGetPairwiseOverlapsFromView:
    """Tests for get_pairwise_overlaps_from_view method.

    These tests require the source_overlap_statistics materialized view,
    which is created by `make db-refresh-views`, not by Alembic migrations.
    They are skipped when the view does not exist (e.g., in CI).
    """

    def test_returns_list(self, db_session):
        """Method returns a list (may be empty if view has no data)."""
        if not _view_exists(db_session):
            pytest.skip("source_overlap_statistics view does not exist")
        result = statistics_crud.get_pairwise_overlaps_from_view(db_session)
        assert isinstance(result, list)

    def test_row_structure(self, db_session):
        """Each row has the expected keys if data exists."""
        if not _view_exists(db_session):
            pytest.skip("source_overlap_statistics view does not exist")
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
        if not _view_exists(db_session):
            pytest.skip("source_overlap_statistics view does not exist")
        result = statistics_crud.get_pairwise_overlaps_from_view(db_session)
        pairs = [(r["source1"], r["source2"]) for r in result]
        assert len(pairs) == len(set(pairs))

    def test_source1_less_than_source2(self, db_session):
        """source1 is always alphabetically before source2 (no duplicates)."""
        if not _view_exists(db_session):
            pytest.skip("source_overlap_statistics view does not exist")
        result = statistics_crud.get_pairwise_overlaps_from_view(db_session)
        for row in result:
            assert row["source1"] < row["source2"]
