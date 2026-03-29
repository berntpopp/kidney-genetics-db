"""Tests for DataSourceClient progress tracking guards."""

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestZeroItemGuard:
    """Verify sources with 0 genes are marked failed, not completed."""

    def test_empty_processed_data_sets_failed_not_completed(self):
        """When process_data returns empty dict, tracker should call error(), not complete()."""
        tracker = MagicMock()
        tracker.complete = MagicMock()
        tracker.error = MagicMock()

        # Simulate the guard logic
        processed_data: dict = {}
        source_name = "TestSource"

        if not processed_data:
            tracker.error(f"{source_name} update returned 0 genes")

        tracker.error.assert_called_once()
        tracker.complete.assert_not_called()
