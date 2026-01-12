"""
Tests for HGNC client functionality.

Tests the async HGNCClientCached class which uses the unified cache service
for persistent, shared caching across application instances.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.hgnc_client import HGNCClientCached


class TestHGNCClientCached:
    """Test cases for HGNCClientCached class."""

    @pytest.fixture(autouse=True)
    def reset_global_cache(self):
        """Reset the global cache service singleton before each test."""
        import app.core.cache_service as cache_module

        # Reset the global singleton
        original_cache = cache_module.cache_service
        cache_module.cache_service = None
        yield
        # Restore after test (optional, but clean)
        cache_module.cache_service = original_cache

    @pytest.fixture
    def mock_cache_service(self):
        """Create a mock cache service."""
        cache_service = MagicMock()
        cache_service.get = AsyncMock(return_value=None)
        cache_service.set = AsyncMock()
        cache_service.get_or_set = AsyncMock()
        cache_service.clear_namespace = AsyncMock(return_value=0)
        cache_service.get_stats = AsyncMock(return_value={})
        cache_service.db_session = None
        return cache_service

    @pytest.fixture
    def mock_http_client(self):
        """Create a mock HTTP client."""
        http_client = MagicMock()
        http_client.get = AsyncMock()
        return http_client

    @pytest.fixture
    def client(self, mock_cache_service, mock_http_client):
        """Create HGNCClientCached instance for testing."""
        # Patch get_cache_service to return our mock
        with patch(
            "app.core.hgnc_client.get_cache_service", return_value=mock_cache_service
        ):
            return HGNCClientCached(
                cache_service=mock_cache_service,
                http_client=mock_http_client,
                timeout=10,
                max_retries=2,
                batch_size=50,
                max_workers=2,
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
                        "status": "Approved",
                    }
                ]
            }
        }

    @pytest.fixture
    def mock_empty_response(self):
        """Mock empty HGNC API response."""
        return {"response": {"docs": []}}

    @pytest.fixture
    def mock_batch_response(self):
        """Mock batch HGNC API response."""
        return {
            "response": {
                "docs": [
                    {"symbol": "PKD1", "hgnc_id": "HGNC:8945"},
                    {"symbol": "PKD2", "hgnc_id": "HGNC:8946"},
                    {"symbol": "ABCA4", "hgnc_id": "HGNC:34"},
                ]
            }
        }

    def test_client_initialization(self, mock_cache_service, mock_http_client):
        """Test HGNCClientCached initialization."""
        client = HGNCClientCached(
            cache_service=mock_cache_service,
            http_client=mock_http_client,
            timeout=30,
            max_retries=3,
            batch_size=100,
            max_workers=4,
        )

        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.batch_size == 100
        assert client.max_workers == 4
        assert client.BASE_URL == "https://rest.genenames.org"
        assert client.NAMESPACE == "hgnc"

    @pytest.mark.asyncio
    async def test_make_request_success(
        self, client, mock_http_client, mock_successful_response
    ):
        """Test successful API request."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_successful_response
        mock_http_client.get.return_value = mock_response

        result = await client._make_request("search/symbol", {"symbol": "PKD1"})

        assert result == mock_successful_response
        mock_http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_failure(self, client, mock_http_client):
        """Test API request failure."""
        mock_http_client.get.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            await client._make_request("search/symbol", {"symbol": "PKD1"})

    @pytest.mark.asyncio
    async def test_symbol_to_hgnc_id_success(
        self, client, mock_successful_response
    ):
        """Test successful symbol to HGNC ID conversion."""

        async def bypass_cache(key, fetch_func, namespace, ttl, db_session):
            """Bypass cache and call fetch function directly."""
            return await fetch_func()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request, patch(
            "app.core.hgnc_client.cached", side_effect=bypass_cache
        ):
            mock_request.return_value = mock_successful_response

            result = await client.symbol_to_hgnc_id("PKD1")

            assert result == "HGNC:8945"

    @pytest.mark.asyncio
    async def test_symbol_to_hgnc_id_not_found(self, client, mock_empty_response):
        """Test symbol to HGNC ID when symbol not found."""

        async def bypass_cache(key, fetch_func, namespace, ttl, db_session):
            """Bypass cache and call fetch function directly."""
            return await fetch_func()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request, patch(
            "app.core.hgnc_client.cached", side_effect=bypass_cache
        ):
            mock_request.return_value = mock_empty_response

            result = await client.symbol_to_hgnc_id("INVALID_GENE")

            assert result is None

    @pytest.mark.asyncio
    async def test_symbol_to_hgnc_id_api_error(self, client):
        """Test symbol to HGNC ID when API fails."""

        async def bypass_cache(key, fetch_func, namespace, ttl, db_session):
            """Bypass cache and call fetch function directly."""
            return await fetch_func()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request, patch(
            "app.core.hgnc_client.cached", side_effect=bypass_cache
        ):
            mock_request.side_effect = Exception("API Error")

            result = await client.symbol_to_hgnc_id("PKD1")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_gene_info_success(self, client, mock_successful_response):
        """Test successful gene info retrieval."""

        async def bypass_cache(key, fetch_func, namespace, ttl, db_session):
            """Bypass cache and call fetch function directly."""
            return await fetch_func()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request, patch(
            "app.core.hgnc_client.cached", side_effect=bypass_cache
        ):
            mock_request.return_value = mock_successful_response

            result = await client.get_gene_info("PKD1")

            expected = mock_successful_response["response"]["docs"][0]
            assert result == expected

    @pytest.mark.asyncio
    async def test_get_gene_info_not_found(self, client, mock_empty_response):
        """Test gene info retrieval when gene not found."""

        async def bypass_cache(key, fetch_func, namespace, ttl, db_session):
            """Bypass cache and call fetch function directly."""
            return await fetch_func()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request, patch(
            "app.core.hgnc_client.cached", side_effect=bypass_cache
        ):
            mock_request.return_value = mock_empty_response

            result = await client.get_gene_info("INVALID_GENE")

            assert result is None

    @pytest.mark.asyncio
    async def test_standardize_symbol_direct_match(self, client, mock_successful_response):
        """Test symbol standardization with direct match."""

        async def bypass_cache(key, fetch_func, namespace, ttl, db_session):
            """Bypass cache and call fetch function directly."""
            return await fetch_func()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request, patch(
            "app.core.hgnc_client.cached", side_effect=bypass_cache
        ):
            mock_request.return_value = mock_successful_response

            result = await client.standardize_symbol("PKD1")

            assert result == "PKD1"
            # Check that the first call was to search/symbol/PKD1
            first_call_args = mock_request.call_args_list[0]
            assert "search/symbol/PKD1" in first_call_args[0][0]

    @pytest.mark.asyncio
    async def test_standardize_symbol_previous_symbol(
        self, client, mock_empty_response, mock_successful_response
    ):
        """Test symbol standardization using previous symbol lookup."""

        async def bypass_cache(key, fetch_func, namespace, ttl, db_session):
            """Bypass cache and call fetch function directly."""
            return await fetch_func()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request, patch(
            "app.core.hgnc_client.cached", side_effect=bypass_cache
        ):
            # Direct lookup fails, previous symbol lookup succeeds
            mock_request.side_effect = [
                mock_empty_response,
                mock_successful_response,
            ]

            result = await client.standardize_symbol("OLD_SYMBOL")

            assert result == "PKD1"
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_standardize_symbol_alias_symbol(
        self, client, mock_empty_response, mock_successful_response
    ):
        """Test symbol standardization using alias symbol lookup."""

        async def bypass_cache(key, fetch_func, namespace, ttl, db_session):
            """Bypass cache and call fetch function directly."""
            return await fetch_func()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request, patch(
            "app.core.hgnc_client.cached", side_effect=bypass_cache
        ):
            # Direct and previous lookups fail, alias lookup succeeds
            mock_request.side_effect = [
                mock_empty_response,
                mock_empty_response,
                mock_successful_response,
            ]

            result = await client.standardize_symbol("ALIAS_SYMBOL")

            assert result == "PKD1"
            assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_standardize_symbol_not_found(self, client, mock_empty_response):
        """Test symbol standardization when symbol not found anywhere."""

        async def bypass_cache(key, fetch_func, namespace, ttl, db_session):
            """Bypass cache and call fetch function directly."""
            return await fetch_func()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request, patch(
            "app.core.hgnc_client.cached", side_effect=bypass_cache
        ):
            mock_request.return_value = mock_empty_response

            result = await client.standardize_symbol("INVALID_SYMBOL")

            assert result == "INVALID_SYMBOL"  # Returns original symbol
            assert mock_request.call_count == 3  # Tries all three methods

    @pytest.mark.asyncio
    async def test_standardize_symbols_batch_success(
        self, client, mock_batch_response, mock_cache_service
    ):
        """Test successful batch symbol standardization."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_batch_response

            symbols = ["PKD1", "PKD2", "ABCA4"]
            result = await client.standardize_symbols_batch(symbols)

            expected = {
                "PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"},
                "PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"},
                "ABCA4": {"approved_symbol": "ABCA4", "hgnc_id": "HGNC:34"},
            }
            assert result == expected

            # Check the API call was made with correct OR syntax
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert "PKD1+OR+PKD2+OR+ABCA4" in args[0]

    @pytest.mark.asyncio
    async def test_standardize_symbols_batch_fallback_to_individual(
        self, client, mock_cache_service
    ):
        """Test batch standardization with fallback to individual lookups."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            # Batch request fails completely
            mock_request.side_effect = Exception("Batch failed")

        with patch.object(
            client, "standardize_symbol", new_callable=AsyncMock
        ) as mock_standardize, patch.object(
            client, "get_gene_info", new_callable=AsyncMock
        ) as mock_get_info:
            # Individual lookups succeed
            mock_standardize.side_effect = ["PKD1", "PKD2"]
            mock_get_info.side_effect = [
                {"hgnc_id": "HGNC:8945"},
                {"hgnc_id": "HGNC:8946"},
            ]

            symbols = ["PKD1", "PKD2"]
            result = await client._process_batch(symbols)

            expected = {
                "PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"},
                "PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"},
            }
            assert result == expected

    @pytest.mark.asyncio
    async def test_standardize_symbols_empty_input(self, client):
        """Test batch standardization with empty input."""
        result = await client.standardize_symbols_batch([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_standardize_symbols_parallel_single_batch(
        self, client, mock_cache_service
    ):
        """Test parallel standardization with single batch."""
        with patch.object(
            client, "standardize_symbols_batch", new_callable=AsyncMock
        ) as mock_batch:
            symbols = ["PKD1"]
            expected = {"PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"}}
            mock_batch.return_value = expected

            result = await client.standardize_symbols_parallel(symbols)

            assert result == expected
            mock_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_standardize_symbols_parallel_multiple_batches(
        self, client, mock_cache_service
    ):
        """Test parallel standardization with multiple batches."""
        client.batch_size = 1  # Force one symbol per batch

        with patch.object(
            client, "standardize_symbols_batch", new_callable=AsyncMock
        ) as mock_batch:
            symbols = ["PKD1", "PKD2"]

            # Mock successful batch processing
            mock_batch.side_effect = [
                {"PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"}},
                {"PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"}},
            ]

            result = await client.standardize_symbols_parallel(symbols)

            expected = {
                "PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"},
                "PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"},
            }
            assert result == expected
            assert mock_batch.call_count == 2

    @pytest.mark.asyncio
    async def test_standardize_symbols_parallel_batch_failure_fallback(
        self, client, mock_cache_service
    ):
        """Test parallel standardization with batch failure and individual fallback."""
        client.batch_size = 1
        symbols = ["PKD1", "PKD2"]

        with patch.object(
            client, "standardize_symbols_batch", new_callable=AsyncMock
        ) as mock_batch, patch.object(
            client, "get_gene_info", new_callable=AsyncMock
        ) as mock_get_info:
            # First batch succeeds, second fails
            mock_batch.side_effect = [
                {"PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"}},
                Exception("Batch failed"),
            ]

            # Individual fallback for second symbol
            mock_get_info.return_value = {"hgnc_id": "HGNC:8946"}

            result = await client.standardize_symbols_parallel(symbols)

            expected = {
                "PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"},
                "PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"},
            }
            assert result == expected

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, client, mock_cache_service):
        """Test cache stats retrieval."""
        expected_stats = {"hits": 10, "misses": 5}
        mock_cache_service.get_stats.return_value = expected_stats

        result = await client.get_cache_stats()

        assert result == expected_stats
        mock_cache_service.get_stats.assert_called_once_with("hgnc")

    @pytest.mark.asyncio
    async def test_clear_cache(self, client, mock_cache_service):
        """Test cache clearing functionality."""
        mock_cache_service.clear_namespace.return_value = 10

        result = await client.clear_cache()

        assert result == 10
        mock_cache_service.clear_namespace.assert_called_once_with("hgnc")

    @pytest.mark.asyncio
    async def test_case_insensitive_processing(self, client):
        """Test that symbol processing handles case correctly."""

        async def bypass_cache(key, fetch_func, namespace, ttl, db_session):
            """Bypass cache and call fetch function directly."""
            return await fetch_func()

        with patch.object(
            client, "_make_request", new_callable=AsyncMock
        ) as mock_request, patch(
            "app.core.hgnc_client.cached", side_effect=bypass_cache
        ):
            mock_request.return_value = {
                "response": {"docs": [{"symbol": "PKD1", "hgnc_id": "HGNC:8945"}]}
            }

            result = await client.standardize_symbol("pkd1")  # lowercase input

            # Should convert to uppercase and find PKD1
            assert result == "PKD1"
            # Check that the endpoint contains uppercase symbol
            first_call_args = mock_request.call_args_list[0]
            assert "PKD1" in first_call_args[0][0]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "symbols,expected_query",
        [
            (["PKD1"], "PKD1"),
            (["PKD1", "PKD2"], "PKD1+OR+PKD2"),
            (["PKD1", "PKD2", "ABCA4"], "PKD1+OR+PKD2+OR+ABCA4"),
            (["pkd1", "PKD2"], "PKD1+OR+PKD2"),  # Mixed case
        ],
    )
    async def test_batch_query_construction(self, client, symbols, expected_query):
        """Test that batch queries are constructed correctly."""
        with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
            # Mock successful batch response to avoid fallback to individual lookups
            mock_response = {
                "response": {
                    "docs": [
                        {"symbol": symbol.upper(), "hgnc_id": f"HGNC:{i + 1000}"}
                        for i, symbol in enumerate(symbols)
                    ]
                }
            }
            mock_request.return_value = mock_response

            await client._process_batch(symbols)

            # Check the first call (batch request) contains the expected query
            first_call_args = mock_request.call_args_list[0]
            endpoint = first_call_args[0][0]
            assert expected_query in endpoint

    @pytest.mark.asyncio
    async def test_empty_symbols_handling(self, client):
        """Test handling of empty or invalid symbol inputs."""
        assert await client.standardize_symbols_batch([]) == {}
        assert await client.standardize_symbols_parallel([]) == {}

    @pytest.mark.asyncio
    async def test_warm_cache(self, client, mock_cache_service):
        """Test cache warming functionality."""
        with patch.object(
            client, "standardize_symbols_batch", new_callable=AsyncMock
        ) as mock_batch, patch.object(
            client, "get_gene_info", new_callable=AsyncMock
        ) as mock_get_info:
            mock_batch.return_value = {}
            mock_get_info.return_value = None

            common_symbols = ["PKD1", "PKD2"]
            result = await client.warm_cache(common_symbols)

            assert result == 2
            mock_batch.assert_called_once_with(common_symbols)
