"""Unit tests for filtering utilities."""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.pipeline.sources.unified.filtering_utils import (
    FilteringStats,
    apply_database_filter,
    apply_memory_filter,
    validate_threshold_config,
)


class TestFilteringStats:
    """Test FilteringStats class."""

    def test_init(self):
        """Test FilteringStats initialization."""
        stats = FilteringStats("TestSource", "items", 5)
        assert stats.source_name == "TestSource"
        assert stats.entity_name == "items"
        assert stats.threshold == 5
        assert stats.total_before == 0
        assert stats.total_after == 0
        assert stats.filtered_count == 0
        assert stats.filtered_genes == []
        assert stats.start_time is not None
        assert stats.end_time is None

    def test_filter_rate_zero_division(self):
        """Test filter rate with no items."""
        stats = FilteringStats("TestSource", "items", 5)
        assert stats.filter_rate == 0.0

    def test_filter_rate_calculation(self):
        """Test filter rate calculation."""
        stats = FilteringStats("TestSource", "items", 5)
        stats.total_before = 100
        stats.filtered_count = 25
        assert stats.filter_rate == 25.0

    def test_duration_seconds(self):
        """Test duration calculation."""
        stats = FilteringStats("TestSource", "items", 5)
        # Initially no end time
        assert stats.duration_seconds == 0.0

        # After completion
        stats.complete()
        assert stats.duration_seconds > 0
        assert stats.end_time is not None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        stats = FilteringStats("TestSource", "items", 5)
        stats.total_before = 100
        stats.total_after = 75
        stats.filtered_count = 25
        stats.filtered_genes = [{"symbol": "GENE1", "count": 2}]
        stats.complete()

        result = stats.to_dict()
        assert result["source_name"] == "TestSource"
        assert result["entity_name"] == "items"
        assert result["threshold"] == 5
        assert result["total_before"] == 100
        assert result["total_after"] == 75
        assert result["filtered_count"] == 25
        assert result["filter_rate"] == "25.0%"
        assert result["timestamp"] is not None
        assert len(result["filtered_sample"]) == 1


class TestMemoryFilter:
    """Test apply_memory_filter function."""

    def test_basic_filtering(self):
        """Test basic filtering logic."""
        data = {
            "GENE1": {"panel_count": 1, "panels": ["A"]},
            "GENE2": {"panel_count": 2, "panels": ["A", "B"]},
            "GENE3": {"panel_count": 3, "panels": ["A", "B", "C"]},
        }

        filtered, stats = apply_memory_filter(
            data_dict=data,
            count_field="panel_count",
            min_threshold=2,
            entity_name="panels",
            source_name="Test",
            enabled=True
        )

        assert len(filtered) == 2
        assert "GENE1" not in filtered
        assert "GENE2" in filtered
        assert "GENE3" in filtered
        assert stats.filtered_count == 1
        assert stats.filter_rate == pytest.approx(33.3, 0.1)

    def test_filter_disabled(self):
        """Test that filtering can be disabled."""
        data = {
            "GENE1": {"panel_count": 1},
            "GENE2": {"panel_count": 2},
        }

        filtered, stats = apply_memory_filter(
            data_dict=data,
            count_field="panel_count",
            min_threshold=2,
            entity_name="panels",
            source_name="Test",
            enabled=False  # Disabled
        )

        assert len(filtered) == 2
        assert stats.filtered_count == 0
        assert stats.total_before == 2
        assert stats.total_after == 2

    def test_threshold_one_no_filtering(self):
        """Test that threshold of 1 means no filtering."""
        data = {
            "GENE1": {"count": 1},
            "GENE2": {"count": 2},
        }

        filtered, stats = apply_memory_filter(
            data_dict=data,
            count_field="count",
            min_threshold=1,
            entity_name="items",
            source_name="Test",
            enabled=True
        )

        assert len(filtered) == 2
        assert stats.filtered_count == 0

    def test_missing_count_field(self):
        """Test handling of missing count field."""
        data = {
            "GENE1": {"other_field": 5},  # Missing count field
            "GENE2": {"panel_count": 2},
        }

        filtered, stats = apply_memory_filter(
            data_dict=data,
            count_field="panel_count",
            min_threshold=2,
            entity_name="panels",
            source_name="Test",
            enabled=True
        )

        # GENE1 should be filtered out (count = 0)
        assert len(filtered) == 1
        assert "GENE2" in filtered
        assert stats.filtered_count == 1

    def test_empty_data(self):
        """Test filtering empty data."""
        filtered, stats = apply_memory_filter(
            data_dict={},
            count_field="count",
            min_threshold=5,
            entity_name="items",
            source_name="Test",
            enabled=True
        )

        assert len(filtered) == 0
        assert stats.total_before == 0
        assert stats.total_after == 0
        assert stats.filtered_count == 0


class TestValidateThreshold:
    """Test validate_threshold_config function."""

    def test_valid_integer(self):
        """Test validation of valid integer."""
        assert validate_threshold_config(3, "test", "Test") == 3
        assert validate_threshold_config(100, "test", "Test") == 100

    def test_zero_returns_minimum(self):
        """Test that zero returns minimum value of 1."""
        assert validate_threshold_config(0, "test", "Test") == 1

    def test_negative_returns_minimum(self):
        """Test that negative values return minimum."""
        assert validate_threshold_config(-5, "test", "Test") == 1
        assert validate_threshold_config(-100, "test", "Test") == 1

    def test_string_number(self):
        """Test string that can be converted to int."""
        assert validate_threshold_config("5", "test", "Test") == 5
        assert validate_threshold_config("1", "test", "Test") == 1

    def test_invalid_string(self):
        """Test invalid string returns minimum."""
        assert validate_threshold_config("invalid", "test", "Test") == 1
        assert validate_threshold_config("abc", "test", "Test") == 1

    def test_none_returns_minimum(self):
        """Test None returns minimum."""
        assert validate_threshold_config(None, "test", "Test") == 1

    def test_float_conversion(self):
        """Test float gets converted to int."""
        assert validate_threshold_config(3.7, "test", "Test") == 3
        assert validate_threshold_config(5.2, "test", "Test") == 5


class TestDatabaseFilter:
    """Test apply_database_filter function."""

    @patch('app.pipeline.sources.unified.filtering_utils.logger')
    def test_filter_disabled(self, mock_logger):
        """Test database filtering when disabled."""
        mock_db = Mock(spec=Session)

        stats = apply_database_filter(
            db=mock_db,
            source_name="TestSource",
            count_field="count",
            min_threshold=5,
            entity_name="items",
            enabled=False
        )

        assert stats.total_before == 0
        assert stats.total_after == 0
        assert stats.filtered_count == 0
        mock_db.execute.assert_not_called()

    @patch('app.pipeline.sources.unified.filtering_utils.logger')
    def test_threshold_one_no_filtering(self, mock_logger):
        """Test that threshold <= 1 means no filtering."""
        mock_db = Mock(spec=Session)

        stats = apply_database_filter(
            db=mock_db,
            source_name="TestSource",
            count_field="count",
            min_threshold=1,
            entity_name="items",
            enabled=True
        )

        assert stats.total_before == 0
        assert stats.total_after == 0
        assert stats.filtered_count == 0
        mock_db.execute.assert_not_called()

    @patch('app.pipeline.sources.unified.filtering_utils.logger')
    def test_no_records_to_filter(self, mock_logger):
        """Test filtering when no records exist."""
        mock_db = Mock(spec=Session)
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        stats = apply_database_filter(
            db=mock_db,
            source_name="TestSource",
            count_field="count",
            min_threshold=5,
            entity_name="items",
            enabled=True
        )

        assert stats.total_before == 0
        assert stats.total_after == 0
        assert stats.filtered_count == 0
        # Should have called execute once for the count
        assert mock_db.execute.call_count == 1

    @patch('app.pipeline.sources.unified.filtering_utils.logger')
    def test_exception_handling(self, mock_logger):
        """Test exception handling in database filtering."""
        mock_db = Mock(spec=Session)
        mock_db.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            apply_database_filter(
                db=mock_db,
                source_name="TestSource",
                count_field="count",
                min_threshold=5,
                entity_name="items",
                enabled=True
            )

        assert str(exc_info.value) == "Database error"
        mock_logger.sync_error.assert_called_once()


class TestIntegration:
    """Integration tests for filtering scenarios."""

    def test_aggressive_filtering_warning(self):
        """Test that aggressive filtering (>50%) triggers warning."""
        data = {f"GENE{i}": {"count": 1} for i in range(100)}
        data["GENE_KEEPER"] = {"count": 10}

        with patch('app.pipeline.sources.unified.filtering_utils.logger') as mock_logger:
            filtered, stats = apply_memory_filter(
                data_dict=data,
                count_field="count",
                min_threshold=5,
                entity_name="items",
                source_name="Test",
                enabled=True
            )

            assert len(filtered) == 1  # Only GENE_KEEPER
            assert stats.filter_rate > 50

            # Check that warning was logged
            warning_calls = [
                call for call in mock_logger.sync_warning.call_args_list
                if "filtered >50% of genes" in str(call)
            ]
            assert len(warning_calls) > 0

    def test_filtered_genes_tracking(self):
        """Test that filtered genes are properly tracked."""
        data = {
            "GENE1": {"publication_count": 1, "pmids": ["123"]},
            "GENE2": {"publication_count": 2, "pmids": ["456", "789"]},
            "GENE3": {"publication_count": 5, "pmids": ["a", "b", "c", "d", "e"]},
        }

        filtered, stats = apply_memory_filter(
            data_dict=data,
            count_field="publication_count",
            min_threshold=3,
            entity_name="publications",
            source_name="PubTator",
            enabled=True
        )

        assert len(stats.filtered_genes) == 2
        assert stats.filtered_genes[0]["symbol"] == "GENE1"
        assert stats.filtered_genes[0]["publication_count"] == 1
        assert stats.filtered_genes[0]["threshold"] == 3
        assert stats.filtered_genes[1]["symbol"] == "GENE2"
        assert stats.filtered_genes[1]["publication_count"] == 2

