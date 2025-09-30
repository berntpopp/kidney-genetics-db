"""
Integration tests for annotation pipeline sources.
Tests the annotation sources with proper retry logic, caching, and error handling.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session


@pytest.mark.integration
class TestAnnotationPipelineBase:
    """Base tests for annotation pipeline functionality."""

    @pytest.mark.asyncio
    async def test_non_blocking_execution(self, db_session: Session):
        """Verify pipeline operations don't block the event loop."""
        from app.pipeline.annotation_pipeline import AnnotationPipeline

        pipeline = AnnotationPipeline(db_session)

        # Create a task that would block if not properly implemented
        async def monitor_responsiveness():
            """Check that event loop remains responsive."""
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(0.01)  # Should complete quickly
            elapsed = asyncio.get_event_loop().time() - start
            return elapsed < 0.02  # Should not be blocked

        # Start pipeline task
        pipeline_task = asyncio.create_task(pipeline.run_pipeline())

        # Check responsiveness multiple times
        responsive_checks = []
        for _ in range(5):
            is_responsive = await monitor_responsiveness()
            responsive_checks.append(is_responsive)
            await asyncio.sleep(0.05)

        # Cancel pipeline
        pipeline_task.cancel()
        try:
            await pipeline_task
        except asyncio.CancelledError:
            pass

        # All checks should show responsive event loop
        assert all(responsive_checks), "Event loop was blocked during pipeline execution"

    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker(self, db_session: Session):
        """Test that retry logic with circuit breaker works correctly."""
        from app.pipeline.annotation_pipeline import AnnotationPipeline

        pipeline = AnnotationPipeline(db_session)

        # Mock a source that fails then succeeds
        mock_source = MagicMock()
        mock_source.fetch_annotation = AsyncMock(
            side_effect=[
                Exception("Network error"),
                Exception("Network error"),
                {"data": "success", "source": "test"},
            ]
        )

        # Test retry logic
        result = await pipeline._fetch_with_retry(
            mock_source, {"symbol": "PKD1", "hgnc_id": "HGNC:8945"}
        )

        assert result == {"data": "success", "source": "test"}
        assert mock_source.fetch_annotation.call_count == 3

    @pytest.mark.asyncio
    async def test_cache_integration(self, db_session: Session, cache):
        """Test that annotation sources properly use caching."""
        from app.pipeline.sources.annotations.base import BaseAnnotationSource

        # Create a test annotation source
        class TestSource(BaseAnnotationSource):
            source_name = "test_source"
            cache_ttl_days = 1

            async def fetch_annotation(self, gene):
                return {"test": "data", "gene": gene.get("symbol")}

        source = TestSource()
        test_gene = {"symbol": "PKD1", "hgnc_id": "HGNC:8945"}

        # First call - should fetch and cache
        result1 = await source.get_cached_annotation(test_gene, cache)
        assert result1 == {"test": "data", "gene": "PKD1"}

        # Second call - should use cache
        with patch.object(source, "fetch_annotation") as mock_fetch:
            result2 = await source.get_cached_annotation(test_gene, cache)
            mock_fetch.assert_not_called()  # Should not fetch again

        assert result2 == result1


@pytest.mark.integration
class TestPanelAppSource:
    """Test PanelApp annotation source."""

    @pytest.fixture
    def mock_panelapp_response(self):
        """Mock PanelApp API response."""
        return {
            "result": {
                "Genes": [
                    {
                        "GeneSymbol": "PKD1",
                        "LevelOfConfidence": "DefinitiveDiagnosis",
                        "ModeOfInheritance": "MONOALLELIC",
                        "Phenotype": "Polycystic kidney disease",
                        "Panel": {"Name": "Cystic kidney disease"},
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_panelapp_data_transformation(self, mock_panelapp_response):
        """Test that PanelApp data is correctly transformed."""
        from app.pipeline.sources.unified.panelapp import PanelAppUnifiedSource

        source = PanelAppUnifiedSource()

        # Mock the HTTP call
        with patch.object(source, "_make_request", return_value=mock_panelapp_response):
            result = await source.fetch_data({"symbol": "PKD1"})

            assert result is not None
            assert "confidence" in result
            assert "mode_of_inheritance" in result
            assert "panel_name" in result

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_panelapp_rate_limiting(self, mock_get):
        """Test that PanelApp respects rate limits."""
        from app.pipeline.sources.unified.panelapp import PanelAppUnifiedSource

        source = PanelAppUnifiedSource()
        mock_get.return_value = AsyncMock(json=lambda: {"result": {"Genes": []}})

        # Make multiple rapid requests
        genes = [{"symbol": f"GENE{i}"} for i in range(10)]
        tasks = [source.fetch_data(gene) for gene in genes]

        import time

        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start

        # Should take some time due to rate limiting
        # Assuming 5 requests per second limit
        assert elapsed > 1.5  # At least 1.5 seconds for 10 requests

        # All should complete without errors
        assert all(not isinstance(r, Exception) for r in results)


@pytest.mark.integration
class TestClinVarSource:
    """Test ClinVar annotation source."""

    @pytest.fixture
    def mock_clinvar_response(self):
        """Mock ClinVar API response."""
        return {
            "result": {
                "uids": ["12345"],
                "12345": {
                    "gene_id": "8945",
                    "symbol": "PKD1",
                    "clinical_significance": ["Pathogenic", "Likely pathogenic"],
                    "variant_count": 150,
                },
            }
        }

    @pytest.mark.asyncio
    async def test_clinvar_variant_counting(self, mock_clinvar_response):
        """Test that ClinVar correctly counts variants by significance."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        source = ClinVarAnnotationSource()

        # Process mock response
        result = source._process_clinvar_data(mock_clinvar_response)

        assert result["pathogenic_count"] > 0
        assert "likely_pathogenic_count" in result
        assert "total_variants" in result

    @pytest.mark.asyncio
    async def test_clinvar_error_handling(self):
        """Test ClinVar source handles API errors gracefully."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        source = ClinVarAnnotationSource()

        # Mock API failure
        with patch.object(source, "_make_request", side_effect=Exception("API Error")):
            result = await source.fetch_annotation({"symbol": "PKD1"})

            # Should return empty result, not crash
            assert result == {} or result is None


@pytest.mark.integration
class TestHPOSource:
    """Test Human Phenotype Ontology source."""

    @pytest.mark.asyncio
    async def test_hpo_kidney_term_detection(self):
        """Test that HPO correctly identifies kidney-related terms."""
        from app.pipeline.sources.unified.hpo import HPOUnifiedSource

        source = HPOUnifiedSource()

        # Test kidney-related HPO terms
        kidney_terms = [
            "HP:0000077",  # Abnormality of the kidney
            "HP:0000107",  # Renal cyst
            "HP:0000113",  # Polycystic kidney dysplasia
        ]

        for term in kidney_terms:
            is_kidney = source._is_kidney_related(term)
            assert is_kidney, f"{term} should be identified as kidney-related"

    @pytest.mark.asyncio
    async def test_hpo_inheritance_parsing(self):
        """Test HPO inheritance pattern parsing."""
        from app.pipeline.sources.unified.hpo import HPOUnifiedSource

        source = HPOUnifiedSource()

        # Test various inheritance patterns
        patterns = {
            "Autosomal dominant": "AD",
            "Autosomal recessive": "AR",
            "X-linked": "XL",
            "Mitochondrial": "MT",
        }

        for full_name, abbrev in patterns.items():
            parsed = source._parse_inheritance(full_name)
            assert parsed == abbrev


@pytest.mark.integration
class TestSourceOrchestration:
    """Test coordination of multiple annotation sources."""

    @pytest.mark.asyncio
    async def test_parallel_source_fetching(self, db_session: Session):
        """Test that multiple sources can fetch in parallel."""
        from app.pipeline.annotation_pipeline import AnnotationPipeline

        pipeline = AnnotationPipeline(db_session)
        test_gene = {"symbol": "PKD1", "hgnc_id": "HGNC:8945"}

        # Mock multiple sources
        sources = []
        for i in range(5):
            mock_source = MagicMock()
            mock_source.name = f"source_{i}"
            mock_source.fetch_annotation = AsyncMock(
                return_value={"source": f"source_{i}", "data": i}
            )
            sources.append(mock_source)

        pipeline.sources = sources

        # Fetch from all sources
        results = await pipeline._fetch_all_annotations(test_gene)

        # All sources should return data
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["source"] == f"source_{i}"

    @pytest.mark.asyncio
    async def test_source_failure_isolation(self, db_session: Session):
        """Test that one source failure doesn't affect others."""
        from app.pipeline.annotation_pipeline import AnnotationPipeline

        pipeline = AnnotationPipeline(db_session)

        # Mix of successful and failing sources
        sources = []

        # Successful source
        success_source = MagicMock()
        success_source.fetch_annotation = AsyncMock(return_value={"status": "success"})
        sources.append(success_source)

        # Failing source
        fail_source = MagicMock()
        fail_source.fetch_annotation = AsyncMock(side_effect=Exception("Source failed"))
        sources.append(fail_source)

        # Another successful source
        success_source2 = MagicMock()
        success_source2.fetch_annotation = AsyncMock(return_value={"status": "success2"})
        sources.append(success_source2)

        pipeline.sources = sources

        # Fetch from all sources
        results = await pipeline._fetch_all_annotations({"symbol": "TEST"})

        # Should get results from successful sources only
        success_results = [r for r in results if r and "status" in r]
        assert len(success_results) == 2
        assert any(r["status"] == "success" for r in success_results)
        assert any(r["status"] == "success2" for r in success_results)
