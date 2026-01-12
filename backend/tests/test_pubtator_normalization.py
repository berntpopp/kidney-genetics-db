"""
Tests for PubTator unified source implementation.

Note: The original tests were designed for the legacy PubTator client that used
process_genes(), _fetch_pubtator_data(), and integrated with normalize_genes_batch()
and gene_crud modules.

The new PubTatorUnifiedSource uses a streaming architecture with:
- fetch_raw_data() - streams data directly to database
- process_data() - no-op as data is processed during streaming
- update_data() - main entry point for pipeline runs

These tests have been updated to test the new API structure.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session

from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource


class TestPubTatorUnifiedSource:
    """Test PubTatorUnifiedSource implementation."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock(spec=Session)
        # Mock execute to return empty result for count queries
        mock_result = Mock()
        mock_result.fetchone.return_value = (0, 0)
        db.execute.return_value = mock_result
        return db

    @pytest.fixture
    def pubtator_source(self):
        """Create PubTator unified source for testing."""
        return PubTatorUnifiedSource()

    def test_source_name(self, pubtator_source):
        """Test source name property."""
        assert pubtator_source.source_name == "PubTator"

    def test_namespace(self, pubtator_source):
        """Test namespace property."""
        assert pubtator_source.namespace == "pubtator"

    def test_initialization_defaults(self, pubtator_source):
        """Test that source initializes with expected defaults."""
        assert pubtator_source.base_url is not None
        assert pubtator_source.kidney_query is not None
        assert pubtator_source.min_publications >= 0
        assert pubtator_source.chunk_size > 0
        assert pubtator_source.transaction_size > 0

    def test_rate_limiter_exists(self, pubtator_source):
        """Test that rate limiter is configured."""
        assert pubtator_source.rate_limiter is not None

    @pytest.mark.asyncio
    async def test_fetch_raw_data_returns_dict(self, pubtator_source):
        """Test fetch_raw_data returns expected structure."""
        mock_tracker = Mock()
        mock_tracker.update = Mock()

        # Mock the internal streaming method
        with patch.object(
            pubtator_source, "_stream_process_pubtator", new_callable=AsyncMock
        ) as mock_stream:
            mock_stream.return_value = {
                "genes_processed": 10,
                "processed_articles": 100,
            }

            result = await pubtator_source.fetch_raw_data(tracker=mock_tracker)

            assert isinstance(result, dict)
            assert "stats" in result
            assert "genes_found" in result
            assert "mode" in result
            assert result["genes_found"] == 10

    @pytest.mark.asyncio
    async def test_process_data_returns_empty_dict(self, pubtator_source):
        """Test process_data returns empty dict (data processed during streaming)."""
        result = await pubtator_source.process_data({"some": "data"})
        assert result == {}

    @pytest.mark.asyncio
    async def test_update_data_calls_stream_process(self, pubtator_source, mock_db):
        """Test update_data uses streaming architecture."""
        mock_tracker = Mock()
        mock_tracker.start = Mock()
        mock_tracker.update = Mock()
        mock_tracker.complete = Mock()
        mock_tracker.error = Mock()

        with patch.object(
            pubtator_source, "_stream_process_pubtator", new_callable=AsyncMock
        ) as mock_stream:
            mock_stream.return_value = {
                "genes_processed": 5,
                "processed_articles": 50,
                "genes_created": 2,
                "evidence_created": 10,
            }

            result = await pubtator_source.update_data(mock_db, mock_tracker)

            # Verify streaming was called
            mock_stream.assert_called_once()

            # Verify tracker was started and completed
            mock_tracker.start.assert_called_once()
            mock_tracker.complete.assert_called_once()

            # Verify result structure
            assert isinstance(result, dict)
            assert "data_fetched" in result
            assert result["data_fetched"] is True

    @pytest.mark.asyncio
    async def test_update_data_handles_errors(self, pubtator_source, mock_db):
        """Test update_data handles errors gracefully."""
        mock_tracker = Mock()
        mock_tracker.start = Mock()
        mock_tracker.update = Mock()
        mock_tracker.error = Mock()

        with patch.object(
            pubtator_source, "_stream_process_pubtator", new_callable=AsyncMock
        ) as mock_stream:
            mock_stream.side_effect = Exception("API error")

            with pytest.raises(Exception, match="API error"):
                await pubtator_source.update_data(mock_db, mock_tracker)

            # Verify error was tracked
            mock_tracker.error.assert_called_once()


class TestPubTatorFiltering:
    """Test filtering configuration for PubTator."""

    @pytest.fixture
    def pubtator_source(self):
        """Create PubTator unified source for testing."""
        return PubTatorUnifiedSource()

    def test_min_publications_configured(self, pubtator_source):
        """Test minimum publications threshold is configured."""
        assert hasattr(pubtator_source, "min_publications")
        assert isinstance(pubtator_source.min_publications, int)

    def test_filtering_enabled_flag(self, pubtator_source):
        """Test filtering enabled flag is configured."""
        assert hasattr(pubtator_source, "filtering_enabled")
        assert isinstance(pubtator_source.filtering_enabled, bool)

    def test_filter_after_complete_flag(self, pubtator_source):
        """Test filter after complete flag is configured."""
        assert hasattr(pubtator_source, "filter_after_complete")
        assert isinstance(pubtator_source.filter_after_complete, bool)


class TestPubTatorConfiguration:
    """Test PubTator configuration loading."""

    def test_base_url_default(self):
        """Test base URL has reasonable default."""
        source = PubTatorUnifiedSource()
        assert "pubtator" in source.base_url.lower()
        assert source.base_url.startswith("http")

    def test_kidney_query_configured(self):
        """Test kidney query is configured with kidney-related terms."""
        source = PubTatorUnifiedSource()
        assert "kidney" in source.kidney_query.lower() or "renal" in source.kidney_query.lower()

    def test_chunk_size_reasonable(self):
        """Test chunk size is reasonable for API requests."""
        source = PubTatorUnifiedSource()
        assert 1 <= source.chunk_size <= 1000

    def test_transaction_size_reasonable(self):
        """Test transaction size is reasonable for database operations."""
        source = PubTatorUnifiedSource()
        assert source.transaction_size >= source.chunk_size
