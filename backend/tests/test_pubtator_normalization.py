"""
Tests for PubTator integration with gene normalization.
"""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.pipeline.sources.pubtator import PubTatorClient


class TestPubTatorNormalization:
    """Test PubTator integration with gene normalization system."""

    @pytest.fixture
    def client(self):
        """Create PubTator client for testing."""
        return PubTatorClient()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_pubtator_response(self):
        """Mock PubTator API response."""
        return {
            "PKD1": {"mentions": 150, "pmids": ["12345", "67890", "11111", "22222", "33333"]},
            "ABCA4": {"mentions": 75, "pmids": ["44444", "55555", "66666"]},
            "INVALID_GENE": {"mentions": 2, "pmids": ["77777"]},
        }

    @pytest.fixture
    def mock_normalization_results(self):
        """Mock gene normalization results."""
        return {
            "PKD1": {
                "status": "normalized",
                "approved_symbol": "PKD1",
                "hgnc_id": "HGNC:8945",
                "staging_id": None,
                "error": None,
            },
            "ABCA4": {
                "status": "normalized",
                "approved_symbol": "ABCA4",
                "hgnc_id": "HGNC:34",
                "staging_id": None,
                "error": None,
            },
            "INVALID_GENE": {
                "status": "requires_manual_review",
                "approved_symbol": None,
                "hgnc_id": None,
                "staging_id": 123,
                "error": None,
            },
        }

    @patch("app.pipeline.sources.pubtator.normalize_genes_batch")
    @patch("app.pipeline.sources.pubtator.gene_crud.create_or_update_gene")
    @patch("app.pipeline.sources.pubtator.gene_crud.create_gene_evidence")
    def test_process_genes_with_normalization(
        self,
        mock_create_evidence,
        mock_create_gene,
        mock_normalize_batch,
        client,
        mock_db,
        mock_pubtator_response,
        mock_normalization_results,
    ):
        """Test PubTator gene processing with normalization."""
        # Mock normalization returning mixed results
        mock_normalize_batch.return_value = mock_normalization_results

        # Mock gene creation
        mock_gene_pkd1 = Mock()
        mock_gene_pkd1.id = 1
        mock_gene_abca4 = Mock()
        mock_gene_abca4.id = 2

        def mock_create_gene_side_effect(db, approved_symbol, hgnc_id):
            if approved_symbol == "PKD1":
                return mock_gene_pkd1
            elif approved_symbol == "ABCA4":
                return mock_gene_abca4
            return None

        mock_create_gene.side_effect = mock_create_gene_side_effect

        # Process the genes
        with patch.object(client, "_fetch_pubtator_data") as mock_fetch:
            mock_fetch.return_value = mock_pubtator_response

            client.process_genes(mock_db, list(mock_pubtator_response.keys()))

        # Verify normalization was called with correct parameters
        mock_normalize_batch.assert_called_once()
        args, kwargs = mock_normalize_batch.call_args
        assert kwargs["gene_texts"] == list(mock_pubtator_response.keys())
        assert kwargs["source_name"] == "PubTator"
        assert len(kwargs["original_data_list"]) == 3

        # Verify only successfully normalized genes were created
        assert mock_create_gene.call_count == 2  # Only PKD1 and ABCA4

        # Verify evidence was created for normalized genes
        assert mock_create_evidence.call_count == 2

        # Check that staging genes were not processed further
        create_gene_calls = [call[1] for call in mock_create_gene.call_args_list]
        assert ("PKD1", "HGNC:8945") in [(call[0], call[1]) for call in create_gene_calls]
        assert ("ABCA4", "HGNC:34") in [(call[0], call[1]) for call in create_gene_calls]

    @patch("app.pipeline.sources.pubtator.normalize_genes_batch")
    def test_normalization_error_handling(self, mock_normalize_batch, client, mock_db):
        """Test handling of normalization errors."""
        # Mock normalization failure
        mock_normalize_batch.side_effect = Exception("Normalization failed")

        gene_list = ["PKD1", "ABCA4"]

        with patch.object(client, "_fetch_pubtator_data") as mock_fetch:
            mock_fetch.return_value = {
                gene: {"mentions": 10, "pmids": ["123"]} for gene in gene_list
            }

            # Should handle normalization errors gracefully
            with pytest.raises(Exception, match="Normalization failed"):
                client.process_genes(mock_db, gene_list)

    @patch("app.pipeline.sources.pubtator.normalize_genes_batch")
    @patch("app.pipeline.sources.pubtator.gene_crud.create_or_update_gene")
    def test_all_genes_require_staging(
        self, mock_create_gene, mock_normalize_batch, client, mock_db
    ):
        """Test scenario where all genes require manual review."""
        gene_list = ["INVALID1", "INVALID2", "INVALID3"]

        # All genes require staging
        mock_normalize_batch.return_value = {
            gene: {
                "status": "requires_manual_review",
                "approved_symbol": None,
                "hgnc_id": None,
                "staging_id": i + 100,
                "error": None,
            }
            for i, gene in enumerate(gene_list)
        }

        with patch.object(client, "_fetch_pubtator_data") as mock_fetch:
            mock_fetch.return_value = {
                gene: {"mentions": 5, "pmids": ["123"]} for gene in gene_list
            }

            result = client.process_genes(mock_db, gene_list)

        # No genes should be created since all require staging
        mock_create_gene.assert_not_called()

        # Should return information about staging
        assert "staging_count" in result or len(result) == 0

    @patch("app.pipeline.sources.pubtator.normalize_genes_batch")
    @patch("app.pipeline.sources.pubtator.gene_crud.create_or_update_gene")
    @patch("app.pipeline.sources.pubtator.gene_crud.create_gene_evidence")
    def test_mixed_normalization_results(
        self, mock_create_evidence, mock_create_gene, mock_normalize_batch, client, mock_db
    ):
        """Test handling of mixed normalization results."""
        gene_list = ["PKD1", "INVALID_GENE", "ABCA4"]

        # Mixed results: some normalized, some staged, some errors
        mock_normalize_batch.return_value = {
            "PKD1": {
                "status": "normalized",
                "approved_symbol": "PKD1",
                "hgnc_id": "HGNC:8945",
                "staging_id": None,
                "error": None,
            },
            "INVALID_GENE": {
                "status": "requires_manual_review",
                "approved_symbol": None,
                "hgnc_id": None,
                "staging_id": 123,
                "error": None,
            },
            "ABCA4": {
                "status": "error",
                "approved_symbol": None,
                "hgnc_id": None,
                "staging_id": None,
                "error": "API timeout",
            },
        }

        # Mock successful gene creation
        mock_gene = Mock()
        mock_gene.id = 1
        mock_create_gene.return_value = mock_gene

        with patch.object(client, "_fetch_pubtator_data") as mock_fetch:
            mock_fetch.return_value = {
                gene: {"mentions": 10, "pmids": ["123"]} for gene in gene_list
            }

            client.process_genes(mock_db, gene_list)

        # Only successfully normalized genes should be processed
        mock_create_gene.assert_called_once_with(mock_db, "PKD1", "HGNC:8945")
        mock_create_evidence.assert_called_once()

    def test_original_data_construction(self, client, mock_db):
        """Test that original data is correctly constructed for normalization."""
        gene_data = {
            "PKD1": {
                "mentions": 150,
                "pmids": ["12345", "67890", "11111", "22222", "33333", "44444", "55555"],
            }
        }

        with patch("app.pipeline.sources.pubtator.normalize_genes_batch") as mock_normalize:
            mock_normalize.return_value = {
                "PKD1": {
                    "status": "normalized",
                    "approved_symbol": "PKD1",
                    "hgnc_id": "HGNC:8945",
                    "staging_id": None,
                    "error": None,
                }
            }

            with patch.object(client, "_fetch_pubtator_data") as mock_fetch:
                with patch("app.pipeline.sources.pubtator.gene_crud.create_or_update_gene"):
                    with patch("app.pipeline.sources.pubtator.gene_crud.create_gene_evidence"):
                        mock_fetch.return_value = gene_data

                        client.process_genes(mock_db, ["PKD1"])

            # Check that original_data was constructed correctly
            args, kwargs = mock_normalize.call_args
            original_data = kwargs["original_data_list"][0]

            assert original_data["pmids"] == gene_data["PKD1"]["pmids"][:10]  # Limited to 10
            assert original_data["publication_count"] == 7
            assert original_data["total_mentions"] == 150

    @patch("app.pipeline.sources.pubtator.normalize_genes_batch")
    def test_normalization_with_empty_pubtator_data(self, mock_normalize_batch, client, mock_db):
        """Test normalization when PubTator returns empty data."""
        with patch.object(client, "_fetch_pubtator_data") as mock_fetch:
            mock_fetch.return_value = {}

            client.process_genes(mock_db, ["PKD1", "ABCA4"])

        # Should not call normalization with empty data
        mock_normalize_batch.assert_not_called()

    @patch("app.pipeline.sources.pubtator.normalize_genes_batch")
    @patch("app.pipeline.sources.pubtator.gene_crud.create_or_update_gene")
    def test_gene_creation_failure_handling(
        self, mock_create_gene, mock_normalize_batch, client, mock_db
    ):
        """Test handling of gene creation failures."""
        mock_normalize_batch.return_value = {
            "PKD1": {
                "status": "normalized",
                "approved_symbol": "PKD1",
                "hgnc_id": "HGNC:8945",
                "staging_id": None,
                "error": None,
            }
        }

        # Gene creation fails
        mock_create_gene.side_effect = Exception("Database error")

        with patch.object(client, "_fetch_pubtator_data") as mock_fetch:
            mock_fetch.return_value = {"PKD1": {"mentions": 10, "pmids": ["123"]}}

            # Should handle gene creation errors
            with pytest.raises(Exception, match="Database error"):
                client.process_genes(mock_db, ["PKD1"])

    def test_performance_with_large_gene_list(self, client, mock_db):
        """Test performance characteristics with large gene lists."""
        # Create a large list of genes
        large_gene_list = [f"GENE_{i}" for i in range(1000)]

        with patch("app.pipeline.sources.pubtator.normalize_genes_batch") as mock_normalize:
            # All genes successfully normalized
            mock_normalize.return_value = {
                gene: {
                    "status": "normalized",
                    "approved_symbol": gene,
                    "hgnc_id": f"HGNC:{i}",
                    "staging_id": None,
                    "error": None,
                }
                for i, gene in enumerate(large_gene_list)
            }

            with patch.object(client, "_fetch_pubtator_data") as mock_fetch:
                with patch("app.pipeline.sources.pubtator.gene_crud.create_or_update_gene"):
                    with patch("app.pipeline.sources.pubtator.gene_crud.create_gene_evidence"):
                        mock_fetch.return_value = {
                            gene: {"mentions": 1, "pmids": ["123"]} for gene in large_gene_list
                        }

                        client.process_genes(mock_db, large_gene_list)

        # Should make only one batch normalization call, not 1000 individual calls
        mock_normalize.assert_called_once()

        # Verify batch size
        args, kwargs = mock_normalize.call_args
        assert len(kwargs["gene_texts"]) == 1000
        assert len(kwargs["original_data_list"]) == 1000


class TestNormalizationIntegration:
    """Integration tests for normalization with PubTator pipeline."""

    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)

    def test_pipeline_run_with_normalization(self, mock_db):
        """Test complete pipeline run with normalization integration."""
        from app.pipeline.sources.pubtator import run_pubtator_pipeline

        # Mock the pipeline components
        with patch("app.pipeline.sources.pubtator.PubTatorClient") as mock_client_class:
            with patch(
                "app.pipeline.sources.pubtator.gene_crud.create_pipeline_run"
            ) as mock_create_run:
                with patch(
                    "app.pipeline.sources.pubtator.gene_crud.update_pipeline_run"
                ) as mock_update_run:
                    # Setup mocks
                    mock_client = Mock()
                    mock_client.fetch_kidney_genes.return_value = ["PKD1", "ABCA4", "COL4A5"]
                    mock_client.process_genes.return_value = {
                        "genes_processed": 2,
                        "genes_created": 2,
                        "genes_staged": 1,
                    }
                    mock_client_class.return_value = mock_client

                    mock_pipeline_run = Mock()
                    mock_pipeline_run.id = 1
                    mock_create_run.return_value = mock_pipeline_run

                    # Run pipeline
                    result = run_pubtator_pipeline(mock_db, max_pages=1)

                    # Verify normalization was integrated
                    mock_client.process_genes.assert_called_once()

                    # Verify pipeline tracking
                    mock_create_run.assert_called_once()
                    mock_update_run.assert_called_once()

                    assert result is not None
