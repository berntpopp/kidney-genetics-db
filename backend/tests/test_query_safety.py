"""Tests for query safety — no unbounded .all() queries."""

import inspect

import pytest

from app.crud.gene_staging import GeneNormalizationLogCRUD, GeneNormalizationStagingCRUD


@pytest.mark.unit
class TestQuerySafety:
    """Verify no unbounded .distinct().all() queries exist."""

    def test_staging_crud_has_limits(self):
        """All .distinct().all() queries in staging CRUD should have .limit() applied."""
        source = inspect.getsource(GeneNormalizationStagingCRUD)
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if ".all()" in line and ".limit(" not in line and ".distinct()" in line:
                pytest.fail(f"Unbounded .distinct().all() at line ~{i}: {line.strip()}")

    def test_log_crud_has_limits(self):
        """All .distinct().all() queries in log CRUD should have .limit() applied."""
        source = inspect.getsource(GeneNormalizationLogCRUD)
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if ".all()" in line and ".limit(" not in line and ".distinct()" in line:
                pytest.fail(f"Unbounded .distinct().all() at line ~{i}: {line.strip()}")
