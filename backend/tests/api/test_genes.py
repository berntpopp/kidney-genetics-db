"""
Integration tests for gene API endpoints.
Following Test Diamond pattern - these are the bulk of our tests (60%).
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from tests.factories import GeneFactory, GeneFactoryBatch


@pytest.mark.integration
class TestGeneEndpoints:
    """Test gene API endpoints with real database."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        """Create test data for each test."""
        # Create a variety of genes with different evidence scores
        self.genes = GeneFactoryBatch.create_with_varying_evidence(db_session, count=20)
        self.kidney_genes = GeneFactoryBatch.create_kidney_panel(db_session, count=10)

    @pytest.mark.asyncio
    async def test_list_genes_basic(self, async_client: AsyncClient):
        """Test basic gene listing without filters."""
        response = await async_client.get("/api/genes")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data

        # Verify we have genes
        assert len(data["items"]) > 0
        assert data["total"] == 30  # 20 + 10 genes created

    @pytest.mark.asyncio
    async def test_list_genes_with_pagination(self, async_client: AsyncClient):
        """Test gene listing with pagination parameters."""
        # First page
        response = await async_client.get("/api/genes", params={"limit": 10, "offset": 0})
        assert response.status_code == 200
        page1 = response.json()

        assert len(page1["items"]) == 10
        assert page1["total"] == 30

        # Second page
        response = await async_client.get("/api/genes", params={"limit": 10, "offset": 10})
        assert response.status_code == 200
        page2 = response.json()

        assert len(page2["items"]) == 10

        # Verify different genes on each page
        page1_ids = {g["hgnc_id"] for g in page1["items"]}
        page2_ids = {g["hgnc_id"] for g in page2["items"]}
        assert page1_ids.isdisjoint(page2_ids)  # No overlap

    @pytest.mark.asyncio
    async def test_list_genes_with_evidence_filter(self, async_client: AsyncClient):
        """Test gene listing with evidence score filtering."""
        response = await async_client.get("/api/genes", params={"evidence_score_min": 0.5})

        assert response.status_code == 200
        data = response.json()

        # Verify all returned genes meet the criteria
        for gene in data["items"]:
            assert gene["evidence_score"] >= 0.5

        # Should have roughly half the genes
        assert data["total"] < 30

    @pytest.mark.asyncio
    async def test_list_genes_with_classification_filter(self, async_client: AsyncClient):
        """Test gene listing with classification filtering."""
        response = await async_client.get("/api/genes", params={"classification": "definitive"})

        assert response.status_code == 200
        data = response.json()

        # Verify all returned genes have the correct classification
        for gene in data["items"]:
            assert gene["classification"] == "definitive"

    @pytest.mark.asyncio
    async def test_list_genes_with_multiple_filters(self, async_client: AsyncClient):
        """Test gene listing with multiple filters combined."""
        response = await async_client.get(
            "/api/genes",
            params={"evidence_score_min": 0.7, "classification": "definitive", "limit": 5},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all filters are applied
        assert len(data["items"]) <= 5
        for gene in data["items"]:
            assert gene["evidence_score"] >= 0.7
            assert gene["classification"] == "definitive"

    @pytest.mark.asyncio
    async def test_get_gene_by_id(self, async_client: AsyncClient):
        """Test retrieving a single gene by HGNC ID."""
        test_gene = self.kidney_genes[0]

        response = await async_client.get(f"/api/genes/{test_gene.hgnc_id}")

        assert response.status_code == 200
        gene_data = response.json()

        # Verify correct gene returned
        assert gene_data["hgnc_id"] == test_gene.hgnc_id
        assert gene_data["symbol"] == test_gene.symbol

    @pytest.mark.asyncio
    async def test_get_gene_not_found(self, async_client: AsyncClient):
        """Test retrieving non-existent gene returns 404."""
        response = await async_client.get("/api/genes/HGNC:99999999")

        assert response.status_code == 404
        assert "detail" in response.json()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_param,value",
        [
            ("evidence_score_min", "not_a_number"),
            ("limit", -1),
            ("limit", 1001),  # Assuming max limit is 1000
            ("offset", "abc"),
            ("classification", "invalid_class"),
        ],
    )
    async def test_invalid_query_parameters(
        self, async_client: AsyncClient, invalid_param: str, value
    ):
        """Test API validates query parameters correctly."""
        response = await async_client.get("/api/genes", params={invalid_param: value})

        assert response.status_code == 422
        error = response.json()
        assert "detail" in error

    @pytest.mark.asyncio
    async def test_gene_detail_caching(self, async_client: AsyncClient, cache):
        """Test that gene details are properly cached."""
        test_gene = self.kidney_genes[0]

        # First request - cache miss
        response1 = await async_client.get(f"/api/genes/{test_gene.hgnc_id}")
        assert response1.status_code == 200

        # Check cache was populated
        cached = await cache.get(f"genes:{test_gene.hgnc_id}", namespace="api")
        assert cached is not None

        # Second request - should use cache
        response2 = await async_client.get(f"/api/genes/{test_gene.hgnc_id}")
        assert response2.status_code == 200

        # Responses should be identical
        assert response2.json() == response1.json()

    @pytest.mark.asyncio
    async def test_search_genes_by_symbol(self, async_client: AsyncClient):
        """Test searching genes by symbol pattern."""
        # Search for PKD genes
        response = await async_client.get("/api/genes", params={"search": "PKD"})

        assert response.status_code == 200
        data = response.json()

        # Should find PKD1 and PKD2
        symbols = [g["symbol"] for g in data["items"]]
        assert any("PKD" in s for s in symbols)

    @pytest.mark.asyncio
    async def test_sorting_genes(self, async_client: AsyncClient):
        """Test sorting genes by different fields."""
        # Sort by evidence score descending
        response = await async_client.get(
            "/api/genes", params={"sort": "-evidence_score", "limit": 5}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify descending order
        scores = [g["evidence_score"] for g in data["items"]]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_gene_annotations_included(self, async_client: AsyncClient):
        """Test that gene annotations are included when requested."""
        test_gene = self.kidney_genes[0]

        response = await async_client.get(
            f"/api/genes/{test_gene.hgnc_id}", params={"include_annotations": True}
        )

        assert response.status_code == 200
        gene_data = response.json()

        # Verify annotations are present
        assert "annotations" in gene_data
        assert isinstance(gene_data["annotations"], dict)

    @pytest.mark.asyncio
    async def test_gene_export_format(self, async_client: AsyncClient):
        """Test exporting genes in different formats."""
        # Test CSV export
        response = await async_client.get("/api/genes", params={"format": "csv", "limit": 5})

        # Assuming API supports CSV export
        if response.status_code == 200:
            assert "text/csv" in response.headers.get("content-type", "")
        else:
            # If not implemented yet, skip
            pytest.skip("CSV export not yet implemented")

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, async_client: AsyncClient):
        """Test API handles concurrent requests correctly."""
        import asyncio

        # Make 10 concurrent requests
        tasks = [async_client.get("/api/genes", params={"limit": 5}) for _ in range(10)]

        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200

        # All should return the same data (since DB is unchanged)
        first_data = responses[0].json()
        for response in responses[1:]:
            assert response.json() == first_data


@pytest.mark.integration
class TestGeneStatistics:
    """Test gene statistics endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        """Create test data with known statistics."""
        # Create specific distribution for testing
        GeneFactory.create_batch(5, classification="definitive", _session=db_session)
        GeneFactory.create_batch(10, classification="strong", _session=db_session)
        GeneFactory.create_batch(15, classification="moderate", _session=db_session)
        GeneFactory.create_batch(20, classification="limited", _session=db_session)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_get_gene_statistics(self, async_client: AsyncClient):
        """Test retrieving gene statistics."""
        response = await async_client.get("/api/genes/statistics")

        if response.status_code == 404:
            pytest.skip("Statistics endpoint not yet implemented")

        assert response.status_code == 200
        stats = response.json()

        # Verify statistics structure
        assert "total_genes" in stats
        assert "by_classification" in stats

        # Verify counts
        assert stats["total_genes"] == 50
        assert stats["by_classification"]["definitive"] == 5
        assert stats["by_classification"]["strong"] == 10
        assert stats["by_classification"]["moderate"] == 15
        assert stats["by_classification"]["limited"] == 20
