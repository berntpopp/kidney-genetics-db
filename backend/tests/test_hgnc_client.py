"""
Tests for HGNC client functionality.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from app.core.hgnc_client import HGNCClient


class TestHGNCClient:
    """Test cases for HGNCClient class."""

    @pytest.fixture
    def client(self):
        """Create HGNCClient instance for testing."""
        return HGNCClient(
            timeout=10,
            max_retries=2,
            retry_delay=0.1,  # Fast retries for tests
            batch_size=50,
            max_workers=2
        )

    @pytest.fixture
    def mock_successful_response(self):
        """Mock successful HGNC API response."""
        return {
            "response": {
                "docs": [
                    {
                        "symbol": "PKD1",
                        "hgnc_id": "HGNC:8945",
                        "name": "polycystin 1, transient receptor potential channel interacting",
                        "status": "Approved"
                    }
                ]
            }
        }

    @pytest.fixture
    def mock_empty_response(self):
        """Mock empty HGNC API response."""
        return {
            "response": {
                "docs": []
            }
        }

    @pytest.fixture
    def mock_batch_response(self):
        """Mock batch HGNC API response."""
        return {
            "response": {
                "docs": [
                    {
                        "symbol": "PKD1",
                        "hgnc_id": "HGNC:8945"
                    },
                    {
                        "symbol": "PKD2",
                        "hgnc_id": "HGNC:8946"
                    },
                    {
                        "symbol": "ABCA4",
                        "hgnc_id": "HGNC:34"
                    }
                ]
            }
        }

    def test_client_initialization(self):
        """Test HGNCClient initialization."""
        client = HGNCClient(
            timeout=30,
            max_retries=3,
            retry_delay=1.0,
            batch_size=100,
            max_workers=4
        )

        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
        assert client.batch_size == 100
        assert client.max_workers == 4
        assert client.BASE_URL == "https://rest.genenames.org"
        assert "kidney-genetics-db" in client.session.headers["User-Agent"]

    @patch('app.core.hgnc_client.requests.Session.request')
    def test_make_request_success(self, mock_request, client, mock_successful_response):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_successful_response
        mock_request.return_value = mock_response

        result = client._make_request("search/symbol", {"symbol": "PKD1"})

        assert result == mock_successful_response
        mock_request.assert_called_once()

    @patch('app.core.hgnc_client.requests.Session.request')
    def test_make_request_retry_on_failure(self, mock_request, client):
        """Test retry logic on API failure."""
        # First two calls fail, third succeeds
        mock_request.side_effect = [
            requests.RequestException("Network error"),
            requests.RequestException("Network error"),
            Mock(raise_for_status=Mock(), json=Mock(return_value={"success": True}))
        ]

        result = client._make_request("search/symbol", {"symbol": "PKD1"})

        assert result == {"success": True}
        assert mock_request.call_count == 3

    @patch('app.core.hgnc_client.requests.Session.request')
    def test_make_request_max_retries_exceeded(self, mock_request, client):
        """Test failure after max retries exceeded."""
        mock_request.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            client._make_request("search/symbol", {"symbol": "PKD1"})

        assert mock_request.call_count == client.max_retries + 1

    @patch('app.core.hgnc_client.HGNCClient._make_request')
    def test_symbol_to_hgnc_id_success(self, mock_request, client, mock_successful_response):
        """Test successful symbol to HGNC ID conversion."""
        mock_request.return_value = mock_successful_response

        result = client.symbol_to_hgnc_id("PKD1")

        assert result == "HGNC:8945"
        mock_request.assert_called_once_with("search/symbol", {"symbol": "PKD1"})

    @patch('app.core.hgnc_client.HGNCClient._make_request')
    def test_symbol_to_hgnc_id_not_found(self, mock_request, client, mock_empty_response):
        """Test symbol to HGNC ID when symbol not found."""
        mock_request.return_value = mock_empty_response

        result = client.symbol_to_hgnc_id("INVALID_GENE")

        assert result is None

    @patch('app.core.hgnc_client.HGNCClient._make_request')
    def test_symbol_to_hgnc_id_api_error(self, mock_request, client):
        """Test symbol to HGNC ID when API fails."""
        mock_request.side_effect = requests.RequestException("API Error")

        result = client.symbol_to_hgnc_id("PKD1")

        assert result is None

    @patch('app.core.hgnc_client.HGNCClient._make_request')
    def test_get_gene_info_success(self, mock_request, client, mock_successful_response):
        """Test successful gene info retrieval."""
        mock_request.return_value = mock_successful_response

        result = client.get_gene_info("PKD1")

        expected = mock_successful_response["response"]["docs"][0]
        assert result == expected
        mock_request.assert_called_once_with("search/symbol", {"symbol": "PKD1"})

    @patch('app.core.hgnc_client.HGNCClient._make_request')
    def test_get_gene_info_not_found(self, mock_request, client, mock_empty_response):
        """Test gene info retrieval when gene not found."""
        mock_request.return_value = mock_empty_response

        result = client.get_gene_info("INVALID_GENE")

        assert result is None

    @patch('app.core.hgnc_client.HGNCClient._make_request')
    def test_standardize_symbol_direct_match(self, mock_request, client, mock_successful_response):
        """Test symbol standardization with direct match."""
        mock_request.return_value = mock_successful_response

        result = client.standardize_symbol("PKD1")

        assert result == "PKD1"
        mock_request.assert_called_once_with("search/symbol/PKD1")

    @patch('app.core.hgnc_client.HGNCClient._make_request')
    def test_standardize_symbol_previous_symbol(self, mock_request, client, mock_empty_response, mock_successful_response):
        """Test symbol standardization using previous symbol lookup."""
        # Direct lookup fails, previous symbol lookup succeeds
        mock_request.side_effect = [mock_empty_response, mock_successful_response, mock_empty_response]

        result = client.standardize_symbol("OLD_SYMBOL")

        assert result == "PKD1"
        assert mock_request.call_count == 2

    @patch('app.core.hgnc_client.HGNCClient._make_request')
    def test_standardize_symbol_alias_symbol(self, mock_request, client, mock_empty_response, mock_successful_response):
        """Test symbol standardization using alias symbol lookup."""
        # Direct and previous lookups fail, alias lookup succeeds
        mock_request.side_effect = [mock_empty_response, mock_empty_response, mock_successful_response]

        result = client.standardize_symbol("ALIAS_SYMBOL")

        assert result == "PKD1"
        assert mock_request.call_count == 3

    @patch('app.core.hgnc_client.HGNCClient._make_request')
    def test_standardize_symbol_not_found(self, mock_request, client, mock_empty_response):
        """Test symbol standardization when symbol not found anywhere."""
        mock_request.return_value = mock_empty_response

        result = client.standardize_symbol("INVALID_SYMBOL")

        assert result == "INVALID_SYMBOL"  # Returns original symbol
        assert mock_request.call_count == 3  # Tries all three methods

    @patch('app.core.hgnc_client.HGNCClient._make_request')
    def test_standardize_symbols_batch_success(self, mock_request, client, mock_batch_response):
        """Test successful batch symbol standardization."""
        mock_request.return_value = mock_batch_response

        symbols = ("PKD1", "PKD2", "ABCA4")
        result = client.standardize_symbols_batch(symbols)

        expected = {
            "PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"},
            "PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"},
            "ABCA4": {"approved_symbol": "ABCA4", "hgnc_id": "HGNC:34"}
        }
        assert result == expected

        # Check the API call was made with correct OR syntax
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert "PKD1+OR+PKD2+OR+ABCA4" in args[0]

    @patch('app.core.hgnc_client.HGNCClient._make_request')
    @patch('app.core.hgnc_client.HGNCClient.standardize_symbol')
    @patch('app.core.hgnc_client.HGNCClient.get_gene_info')
    def test_standardize_symbols_batch_fallback_to_individual(self, mock_get_info, mock_standardize, mock_request, client):
        """Test batch standardization with fallback to individual lookups."""
        # Batch request fails completely
        mock_request.side_effect = requests.RequestException("Batch failed")

        # Individual lookups succeed
        mock_standardize.side_effect = ["PKD1", "PKD2"]
        mock_get_info.side_effect = [
            {"hgnc_id": "HGNC:8945"},
            {"hgnc_id": "HGNC:8946"}
        ]

        symbols = ("PKD1", "PKD2")
        result = client.standardize_symbols_batch(symbols)

        expected = {
            "PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"},
            "PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"}
        }
        assert result == expected

    def test_standardize_symbols_empty_input(self, client):
        """Test batch standardization with empty input."""
        result = client.standardize_symbols_batch(())
        assert result == {}

    @patch('app.core.hgnc_client.HGNCClient.standardize_symbols_batch')
    def test_standardize_symbols_single_batch(self, mock_batch, client):
        """Test standardize_symbols with single batch."""
        symbols = ["PKD1", "PKD2"]
        expected = {"PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"}}
        mock_batch.return_value = expected

        result = client.standardize_symbols(symbols)

        assert result == expected
        mock_batch.assert_called_once_with(tuple(symbols))

    @patch('app.core.hgnc_client.HGNCClient.standardize_symbols_batch')
    def test_standardize_symbols_multiple_batches(self, mock_batch, client):
        """Test standardize_symbols with multiple batches."""
        client.batch_size = 2  # Force multiple batches
        symbols = ["PKD1", "PKD2", "ABCA4"]

        # Mock returns for each batch
        mock_batch.side_effect = [
            {"PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"},
             "PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"}},
            {"ABCA4": {"approved_symbol": "ABCA4", "hgnc_id": "HGNC:34"}}
        ]

        result = client.standardize_symbols(symbols)

        expected = {
            "PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"},
            "PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"},
            "ABCA4": {"approved_symbol": "ABCA4", "hgnc_id": "HGNC:34"}
        }
        assert result == expected
        assert mock_batch.call_count == 2

    @patch('app.core.hgnc_client.HGNCClient.standardize_symbols_batch')
    def test_standardize_symbols_parallel_single_batch(self, mock_batch, client):
        """Test parallel standardization with single batch."""
        symbols = ["PKD1"]
        expected = {"PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"}}
        mock_batch.return_value = expected

        result = client.standardize_symbols_parallel(symbols)

        assert result == expected
        mock_batch.assert_called_once()

    @patch('app.core.hgnc_client.HGNCClient.standardize_symbols_batch')
    def test_standardize_symbols_parallel_multiple_batches(self, mock_batch, client):
        """Test parallel standardization with multiple batches."""
        client.batch_size = 1  # Force one symbol per batch
        symbols = ["PKD1", "PKD2"]

        # Mock successful batch processing
        mock_batch.side_effect = [
            {"PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"}},
            {"PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"}}
        ]

        result = client.standardize_symbols_parallel(symbols)

        expected = {
            "PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"},
            "PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"}
        }
        assert result == expected
        assert mock_batch.call_count == 2

    @patch('app.core.hgnc_client.HGNCClient.standardize_symbols_batch')
    @patch('app.core.hgnc_client.HGNCClient.get_gene_info')
    def test_standardize_symbols_parallel_batch_failure_fallback(self, mock_get_info, mock_batch, client):
        """Test parallel standardization with batch failure and individual fallback."""
        client.batch_size = 1
        symbols = ["PKD1", "PKD2"]

        # First batch succeeds, second fails
        mock_batch.side_effect = [
            {"PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"}},
            Exception("Batch failed")
        ]

        # Individual fallback for second symbol
        mock_get_info.return_value = {"hgnc_id": "HGNC:8946"}

        result = client.standardize_symbols_parallel(symbols)

        expected = {
            "PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"},
            "PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"}
        }
        assert result == expected

    def test_cache_functionality(self, client):
        """Test that caching works for repeated calls."""
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {
                "response": {
                    "docs": [{"symbol": "PKD1", "hgnc_id": "HGNC:8945"}]
                }
            }

            # First call
            result1 = client.symbol_to_hgnc_id("PKD1")
            # Second call (should use cache)
            result2 = client.symbol_to_hgnc_id("PKD1")

            assert result1 == result2 == "HGNC:8945"
            # Should only make one API call due to caching
            mock_request.assert_called_once()

    def test_get_cache_info(self, client):
        """Test cache info retrieval."""
        cache_info = client.get_cache_info()

        assert "symbol_to_hgnc_id" in cache_info
        assert "get_gene_info" in cache_info
        assert "standardize_symbol" in cache_info
        assert "standardize_symbols_batch" in cache_info

        # Check that each cache info contains expected fields
        for method_cache in cache_info.values():
            assert "hits" in method_cache
            assert "misses" in method_cache
            assert "currsize" in method_cache
            assert "maxsize" in method_cache

    def test_clear_cache(self, client):
        """Test cache clearing functionality."""
        # Make a call to populate cache
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {
                "response": {
                    "docs": [{"symbol": "PKD1", "hgnc_id": "HGNC:8945"}]
                }
            }
            client.symbol_to_hgnc_id("PKD1")

            # Verify cache has entries
            cache_info = client.get_cache_info()
            assert cache_info["symbol_to_hgnc_id"]["currsize"] > 0

            # Clear cache
            client.clear_cache()

            # Verify cache is empty
            cache_info = client.get_cache_info()
            assert cache_info["symbol_to_hgnc_id"]["currsize"] == 0

    def test_case_insensitive_processing(self, client):
        """Test that symbol processing handles case correctly."""
        with patch.object(client, '_make_request') as mock_request:
            mock_request.return_value = {
                "response": {
                    "docs": [{"symbol": "PKD1", "hgnc_id": "HGNC:8945"}]
                }
            }

            result = client.standardize_symbol("pkd1")  # lowercase input

            # Should convert to uppercase and find PKD1
            assert result == "PKD1"
            mock_request.assert_called_with("search/symbol/PKD1")

    @pytest.mark.parametrize("symbols,expected_query", [
        (("PKD1",), "PKD1"),
        (("PKD1", "PKD2"), "PKD1+OR+PKD2"),
        (("PKD1", "PKD2", "ABCA4"), "PKD1+OR+PKD2+OR+ABCA4"),
        (("pkd1", "PKD2"), "PKD1+OR+PKD2"),  # Mixed case
    ])
    def test_batch_query_construction(self, client, symbols, expected_query):
        """Test that batch queries are constructed correctly."""
        with patch.object(client, '_make_request') as mock_request:
            # Mock successful batch response to avoid fallback to individual lookups
            mock_response = {
                "response": {
                    "docs": [
                        {"symbol": symbol.upper(), "hgnc_id": f"HGNC:{i+1000}"}
                        for i, symbol in enumerate(symbols)
                    ]
                }
            }
            mock_request.return_value = mock_response

            client.standardize_symbols_batch(symbols)

            # Check the first call (batch request) contains the expected query
            first_call_args = mock_request.call_args_list[0]
            endpoint = first_call_args[0][0]
            assert expected_query in endpoint

    def test_empty_symbols_handling(self, client):
        """Test handling of empty or invalid symbol inputs."""
        assert client.standardize_symbols([]) == {}
        assert client.standardize_symbols_batch(()) == {}
        assert client.standardize_symbols_parallel([]) == {}
