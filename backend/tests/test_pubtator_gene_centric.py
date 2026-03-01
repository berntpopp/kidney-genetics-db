"""
Tests for PubTator gene-centric optimization.

Verifies that gene-centric queries (one request per known gene)
produce correct evidence data and fall back to keyword search on failure.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource


@pytest.fixture
def mock_deps():
    """Create mock dependencies for PubTator source."""
    cache = MagicMock(spec=CacheService)
    http = AsyncMock(spec=CachedHttpClient)
    db = MagicMock(spec=Session)
    return cache, http, db


@pytest.fixture
def source(mock_deps):
    """Create PubTator source with mocked dependencies."""
    cache, http, db = mock_deps
    return PubTatorUnifiedSource(cache_service=cache, http_client=http, db_session=db)


class TestGeneCentricConfig:
    """Test gene-centric configuration."""

    def test_gene_centric_enabled_by_default(self, source):
        assert source.gene_centric_enabled is True

    def test_gene_centric_kidney_terms_configured(self, source):
        assert "kidney" in source.gene_centric_kidney_terms.lower()

    def test_search_api_url_configured(self, source):
        assert "pubtator3-api" in source.search_api_url

    def test_gene_centric_max_pages_default(self, source):
        assert source.gene_centric_max_pages == 1


class TestFetchGenePublications:
    """Test _fetch_gene_publications method."""

    @pytest.mark.asyncio
    async def test_fetch_returns_api_response(self, source, mock_deps):
        """Test successful gene query returns response dict."""
        _, http, _ = mock_deps
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "count": 42,
            "total_pages": 5,
            "results": [
                {
                    "pmid": "12345",
                    "title": "PKD1 in kidney disease",
                    "journal": "Nephrology",
                    "date": "2024-01-01",
                    "score": 250.5,
                    "text_hl": "@GENE_PKD1 @GENE_5310 @@@PKD1@@@ polycystin",
                }
            ],
        }
        http.get.return_value = mock_response

        with patch.object(source.rate_limiter, "wait", new=AsyncMock()):
            result = await source._fetch_gene_publications("PKD1")

        assert result is not None
        assert result["count"] == 42
        assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_fetch_uses_gene_syntax(self, source, mock_deps):
        """Test that query uses @GENE_ prefix syntax."""
        _, http, _ = mock_deps
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"count": 0, "total_pages": 0, "results": []}
        http.get.return_value = mock_response

        with patch.object(source.rate_limiter, "wait", new=AsyncMock()):
            await source._fetch_gene_publications("COL4A3")

        call_args = http.get.call_args
        params = call_args[1].get("params") or call_args.kwargs.get("params")
        assert "@GENE_COL4A3" in params["text"]
        assert "kidney" in params["text"].lower()

    @pytest.mark.asyncio
    async def test_fetch_uses_search_api_url(self, source, mock_deps):
        """Test that gene-centric queries use the PubTator3 search API URL."""
        _, http, _ = mock_deps
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"count": 0, "total_pages": 0, "results": []}
        http.get.return_value = mock_response

        with patch.object(source.rate_limiter, "wait", new=AsyncMock()):
            await source._fetch_gene_publications("PKD1")

        call_args = http.get.call_args
        url = call_args[0][0] if call_args[0] else call_args.kwargs.get("url", "")
        assert "pubtator3-api" in url

    @pytest.mark.asyncio
    async def test_fetch_returns_none_on_404(self, source, mock_deps):
        """Test non-retryable status returns None."""
        _, http, _ = mock_deps
        mock_response = MagicMock()
        mock_response.status_code = 404
        http.get.return_value = mock_response

        with patch.object(source.rate_limiter, "wait", new=AsyncMock()):
            result = await source._fetch_gene_publications("INVALID")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_respects_rate_limiter(self, source, mock_deps):
        """Test that rate limiter is called before each request."""
        _, http, _ = mock_deps
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"count": 0, "total_pages": 0, "results": []}
        http.get.return_value = mock_response

        with patch.object(source.rate_limiter, "wait", new=AsyncMock()) as mock_wait:
            await source._fetch_gene_publications("PKD1")
            mock_wait.assert_called_once()


class TestBuildGeneEvidence:
    """Test _build_gene_evidence method."""

    def test_basic_evidence_structure(self, source):
        """Test evidence data has required fields."""
        api_response = {
            "count": 10,
            "results": [
                {
                    "pmid": "111",
                    "title": "Paper 1",
                    "journal": "J1",
                    "date": "2024-01-01",
                    "score": 100.0,
                    "text_hl": "@GENE_PKD1 @GENE_5310 @@@PKD1@@@",
                },
                {
                    "pmid": "222",
                    "title": "Paper 2",
                    "journal": "J2",
                    "date": "2024-02-01",
                    "score": 90.0,
                },
            ],
        }

        evidence = source._build_gene_evidence("PKD1", api_response)

        assert evidence["publication_count"] == 10
        assert evidence["pmids"] == ["111", "222"]
        assert len(evidence["mentions"]) == 2
        assert evidence["mentions"][0]["score"] == 100.0  # Sorted by score desc
        assert "search_query" in evidence
        assert "@GENE_PKD1" in evidence["search_query"]

    def test_publication_count_from_api_count(self, source):
        """Test that publication_count uses API count, not len(results)."""
        api_response = {
            "count": 500,  # API says 500 total
            "results": [{"pmid": "1", "title": "T", "score": 1}],  # Only 1 on page 1
        }

        evidence = source._build_gene_evidence("GENE1", api_response)
        assert evidence["publication_count"] == 500

    def test_top_mentions_limited_to_five(self, source):
        """Test top_mentions capped at 5."""
        api_response = {
            "count": 10,
            "results": [
                {"pmid": str(i), "title": f"Paper {i}", "score": float(i)} for i in range(10)
            ],
        }

        evidence = source._build_gene_evidence("X", api_response)
        assert len(evidence["top_mentions"]) == 5

    def test_identifiers_extracted_from_highlight(self, source):
        """Test gene identifiers extracted from text_hl."""
        api_response = {
            "count": 1,
            "results": [
                {
                    "pmid": "1",
                    "title": "T",
                    "score": 1,
                    "text_hl": "@GENE_PKD1 @GENE_5310 @@@polycystin-1@@@",
                }
            ],
        }

        evidence = source._build_gene_evidence("PKD1", api_response)
        assert "5310" in evidence["identifiers"]

    def test_empty_results_handled(self, source):
        """Test graceful handling of empty results."""
        api_response = {"count": 0, "results": []}

        evidence = source._build_gene_evidence("EMPTY", api_response)
        assert evidence["publication_count"] == 0
        assert evidence["pmids"] == []
        assert evidence["mentions"] == []
        assert evidence["evidence_score"] == 0


class TestGeneCentricProcess:
    """Test _gene_centric_process method."""

    @pytest.mark.asyncio
    async def test_queries_all_genes_from_database(self, source, mock_deps):
        """Test that all gene symbols are queried from the database."""
        _, http, db = mock_deps

        # Mock DB to return gene symbols
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("PKD1",), ("COL4A3",), ("NPHS1",)]
        db.execute.return_value = mock_result

        # Mock API responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"count": 0, "total_pages": 0, "results": []}
        http.get.return_value = mock_response

        with patch.object(source.rate_limiter, "wait", new=AsyncMock()):
            stats = await source._gene_centric_process(db, None, "smart")

        assert stats["processed_genes"] == 3
        assert stats["approach"] == "gene_centric"

    @pytest.mark.asyncio
    async def test_skips_genes_below_threshold(self, source, mock_deps):
        """Test genes with few publications are skipped when filtering enabled."""
        _, http, db = mock_deps
        source.filtering_enabled = True
        source.min_publications = 3

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("RARE_GENE",)]
        db.execute.return_value = mock_result

        # Gene has only 1 publication
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "count": 1,
            "total_pages": 1,
            "results": [{"pmid": "1", "title": "T", "score": 1}],
        }
        http.get.return_value = mock_response

        with patch.object(source.rate_limiter, "wait", new=AsyncMock()):
            stats = await source._gene_centric_process(db, None, "smart")

        assert stats["genes_skipped_below_threshold"] == 1
        assert stats["genes_with_publications"] == 0

    @pytest.mark.asyncio
    async def test_empty_database_returns_empty_stats(self, source, mock_deps):
        """Test graceful handling when no genes in database."""
        _, _, db = mock_deps

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        db.execute.return_value = mock_result

        stats = await source._gene_centric_process(db, None, "smart")

        assert stats["processed_genes"] == 0
        assert stats["approach"] == "gene_centric"

    @pytest.mark.asyncio
    async def test_continues_on_single_gene_error(self, source, mock_deps):
        """Test that errors on individual genes don't stop processing."""
        _, _, db = mock_deps

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("GENE1",), ("GENE2",)]
        db.execute.return_value = mock_result

        # Mock _fetch_gene_publications directly (bypasses retry decorator)
        call_count = 0
        original_fetch = source._fetch_gene_publications

        async def mock_fetch(symbol):
            nonlocal call_count
            call_count += 1
            if symbol == "GENE1":
                raise ConnectionError("Network error")
            return {"count": 0, "results": []}

        with patch.object(source, "_fetch_gene_publications", side_effect=mock_fetch):
            stats = await source._gene_centric_process(db, None, "smart")

        assert stats["errors"] >= 1
        assert stats["processed_genes"] >= 1


class TestUpdateDataFallback:
    """Test update_data fallback from gene-centric to keyword search."""

    @pytest.mark.asyncio
    async def test_uses_gene_centric_by_default(self, source, mock_deps):
        """Test update_data tries gene-centric first."""
        _, _, db = mock_deps

        # Mock the DB query for post-processing stats
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (10, 50)
        db.execute.return_value = mock_result

        mock_tracker = Mock()
        mock_tracker.start = Mock()
        mock_tracker.update = Mock()
        mock_tracker.complete = Mock()

        with patch.object(source, "_gene_centric_process", new_callable=AsyncMock) as mock_gc:
            mock_gc.return_value = {
                "processed_genes": 5,
                "processed_articles": 50,
                "genes_created": 2,
                "evidence_created": 10,
            }

            result = await source.update_data(db, mock_tracker)
            mock_gc.assert_called_once()
            assert result["data_fetched"] is True

    @pytest.mark.asyncio
    async def test_falls_back_to_keyword_search(self, source, mock_deps):
        """Test fallback to keyword search when gene-centric fails."""
        _, _, db = mock_deps

        mock_result = MagicMock()
        mock_result.fetchone.return_value = (10, 50)
        db.execute.return_value = mock_result

        mock_tracker = Mock()
        mock_tracker.start = Mock()
        mock_tracker.update = Mock()
        mock_tracker.complete = Mock()

        with (
            patch.object(source, "_gene_centric_process", new_callable=AsyncMock) as mock_gc,
            patch.object(source, "_stream_process_pubtator", new_callable=AsyncMock) as mock_stream,
        ):
            mock_gc.side_effect = Exception("Gene-centric failed")
            mock_stream.return_value = {
                "processed_genes": 3,
                "processed_articles": 30,
                "genes_created": 1,
                "evidence_created": 5,
            }

            result = await source.update_data(db, mock_tracker)

            mock_gc.assert_called_once()
            mock_stream.assert_called_once()
            assert result["data_fetched"] is True

    @pytest.mark.asyncio
    async def test_skips_gene_centric_when_disabled(self, source, mock_deps):
        """Test that keyword search is used when gene-centric is disabled."""
        _, _, db = mock_deps
        source.gene_centric_enabled = False

        mock_result = MagicMock()
        mock_result.fetchone.return_value = (10, 50)
        db.execute.return_value = mock_result

        mock_tracker = Mock()
        mock_tracker.start = Mock()
        mock_tracker.update = Mock()
        mock_tracker.complete = Mock()

        with (
            patch.object(source, "_gene_centric_process", new_callable=AsyncMock) as mock_gc,
            patch.object(source, "_stream_process_pubtator", new_callable=AsyncMock) as mock_stream,
        ):
            mock_stream.return_value = {
                "processed_genes": 3,
                "processed_articles": 30,
                "genes_created": 1,
                "evidence_created": 5,
            }

            await source.update_data(db, mock_tracker)

            mock_gc.assert_not_called()
            mock_stream.assert_called_once()
