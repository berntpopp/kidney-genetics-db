"""Tests for statistics source overlap computation."""

import inspect

import pytest

from app.crud import statistics
from app.crud.statistics import statistics_crud


@pytest.mark.unit
class TestSourceOverlapBitmask:
    """Verify source overlap uses single-query bitmask approach."""

    def test_source_overlap_does_not_use_combinations(self):
        """Verify itertools.combinations is no longer used in statistics.py."""
        source = inspect.getsource(statistics)
        assert "from itertools import combinations" not in source
        assert "combinations(" not in source

    def test_source_overlap_returns_expected_structure(self, db_session):
        """Verify the overlap endpoint returns sets + intersections."""
        result = statistics_crud.get_source_overlaps(db_session)
        assert "sets" in result
        assert "intersections" in result
        assert isinstance(result["sets"], list)
        assert isinstance(result["intersections"], list)
