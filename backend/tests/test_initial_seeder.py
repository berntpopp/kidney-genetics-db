"""Tests for initial data seeder."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.mark.unit
class TestInitialSeeder:
    """Verify initial seeder detects empty DB and loads seed data."""

    def test_needs_seeding_when_no_dp_or_lit_evidence(self):
        """Should return True when neither DiagnosticPanels nor Literature has data."""
        from app.core.initial_seeder import needs_initial_seeding

        db = MagicMock()
        # Both filter chains return count() == 0
        db.query.return_value.filter.return_value.count.return_value = 0
        assert needs_initial_seeding(db) is True

    def test_no_seeding_when_dp_evidence_exists(self):
        """Should return False when DiagnosticPanels has data."""
        from app.core.initial_seeder import needs_initial_seeding

        db = MagicMock()
        # First call returns 100 (DiagnosticPanels), second returns 0 (Literature)
        db.query.return_value.filter.return_value.count.side_effect = [100, 0]
        assert needs_initial_seeding(db) is False

    def test_find_scraper_files_returns_paths(self):
        """Should find the latest date-stamped output directory."""
        from app.core.initial_seeder import find_latest_scraper_output

        with patch("app.core.initial_seeder.Path") as mock_path_cls:
            mock_dir = MagicMock()
            mock_path_cls.return_value = mock_dir
            mock_dir.exists.return_value = True

            mock_subdir = MagicMock()
            mock_subdir.is_dir.return_value = True
            mock_subdir.name = "2025-08-24"
            mock_dir.iterdir.return_value = [mock_subdir]

            result = find_latest_scraper_output(mock_dir)
            assert result is not None

    def test_seed_data_dir_exists(self):
        """Verify seed data directory exists with expected structure."""
        from app.core.initial_seeder import SEED_DATA_DIR

        assert SEED_DATA_DIR.exists(), f"Seed data dir missing: {SEED_DATA_DIR}"
        dp_dir = SEED_DATA_DIR / "diagnostic_panels"
        lit_dir = SEED_DATA_DIR / "literature"
        assert dp_dir.exists(), f"diagnostic_panels seed dir missing: {dp_dir}"
        assert lit_dir.exists(), f"literature seed dir missing: {lit_dir}"
        assert len(list(dp_dir.glob("*.json"))) > 0
        assert len(list(lit_dir.glob("*.json"))) > 0
