"""
Tests for gene normalization functionality.
"""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.gene_normalization import (
    clean_gene_text,
    clear_normalization_cache,
    get_hgnc_client,
    get_normalization_stats,
    is_likely_gene_symbol,
    normalize_gene_for_database,
    normalize_genes_batch,
)
from app.models.gene import Gene

class TestGeneTextCleaning:
    """Test gene text cleaning and validation functions."""

    @pytest.mark.parametrize("input_text,expected", [
        ("PKD1", "PKD1"),
        ("  pkd1  ", "PKD1"),
        ("GENE:PKD1", "PKD1"),
        ("SYMBOL:PKD1", "PKD1"),
        ("PROTEIN:PKD1", "PKD1"),
        ("PKD1_HUMAN", "PKD1"),
        ("PKD1GENE", "PKD1"),
        ("PKD1PROTEIN", "PKD1"),
        ("PKD1;PKD2", "PKD1"),  # Take first part
        ("PKD1,PKD2", "PKD1"),
        ("PKD1|PKD2", "PKD1"),
        ("PKD1/PKD2", "PKD1"),
        ("PKD1 (alias)", "PKD1"),  # Remove parenthetical
        ("PKD1-AS1", "PKD1-AS1"),  # Keep hyphens
        ("PKD1@#$%", "PKD1"),  # Remove special chars except hyphens
        ("", ""),
        (None, ""),
    ])
    def test_clean_gene_text(self, input_text, expected):
        """Test gene text cleaning."""
        result = clean_gene_text(input_text) if input_text is not None else clean_gene_text("")
        assert result == expected

    @pytest.mark.parametrize("gene_text,expected", [
        ("PKD1", True),
        ("ABCA4", True),
        ("COL4A5", True),
        ("PKD1-AS1", True),  # Antisense transcript
        ("C5orf42", True),  # Chromosome-based name
        ("", False),  # Empty
        ("A", False),  # Too short
        ("UNKNOWN", False),  # Excluded term
        ("NONE", False),
        ("NULL", False),
        ("NA", False),
        ("GENE", False),
        ("PROTEIN", False),
        ("CHROMOSOME", False),
        ("COMPLEX", False),
        ("FAMILY", False),
        ("GROUP", False),
        ("CLUSTER", False),
        ("REGION", False),
        ("LOCUS", False),
        ("ELEMENT", False),
        ("SEQUENCE", False),
        ("FRAGMENT", False),
        ("PARTIAL", False),
        ("PUTATIVE", False),
        ("THIS_IS_A_VERY_LONG_GENE_NAME_THAT_IS_TOO_LONG", False),  # Too long
        ("12345", False),  # Only numbers
        ("ALBUMIN", True),  # Should pass basic checks (filtering happens later)
    ])
    def test_is_likely_gene_symbol(self, gene_text, expected):
        """Test gene symbol validation."""
        result = is_likely_gene_symbol(gene_text)
        assert result == expected

class TestGeneNormalization:
    """Test gene normalization functions."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_existing_gene(self):
        """Create mock existing gene."""
        gene = Mock()
        gene.approved_symbol = "PKD1"
        gene.hgnc_id = "HGNC:8945"
        return gene

    @pytest.fixture
    def mock_staging_record(self):
        """Create mock staging record."""
        record = Mock()
        record.id = 123
        return record

    @patch('app.core.gene_normalization.gene_crud.get_gene_by_symbol')
    @patch('app.core.gene_normalization.get_hgnc_client')
    def test_normalize_gene_for_database_existing_gene(self, mock_get_client, mock_get_gene, mock_db, mock_existing_gene):
        """Test normalization when gene already exists in database."""
        mock_get_gene.return_value = mock_existing_gene

        result = normalize_gene_for_database(
            db=mock_db,
            gene_text="PKD1",
            source_name="Test",
            original_data={"test": True}
        )

        expected = {
            "status": "normalized",
            "approved_symbol": "PKD1",
            "hgnc_id": "HGNC:8945",
            "staging_id": None,
            "error": None
        }
        assert result == expected
        mock_get_gene.assert_called_once_with(mock_db, "PKD1")
        mock_get_client.assert_not_called()  # Should not hit HGNC API

    @patch('app.core.gene_normalization.gene_crud.get_gene_by_symbol')
    @patch('app.core.gene_normalization.get_hgnc_client')
    def test_normalize_gene_for_database_hgnc_success(self, mock_get_client, mock_get_gene, mock_db):
        """Test successful normalization via HGNC API."""
        mock_get_gene.return_value = None  # Gene not in database

        mock_hgnc_client = Mock()
        mock_hgnc_client.standardize_symbols.return_value = {
            "PKD1": {
                "approved_symbol": "PKD1",
                "hgnc_id": "HGNC:8945"
            }
        }
        mock_get_client.return_value = mock_hgnc_client

        result = normalize_gene_for_database(
            db=mock_db,
            gene_text="PKD1",
            source_name="Test",
            original_data={"test": True}
        )

        expected = {
            "status": "normalized",
            "approved_symbol": "PKD1",
            "hgnc_id": "HGNC:8945",
            "staging_id": None,
            "error": None
        }
        assert result == expected
        mock_hgnc_client.standardize_symbols.assert_called_once_with(["PKD1"])

    @patch('app.core.gene_normalization.gene_crud.get_gene_by_symbol')
    @patch('app.core.gene_normalization.get_hgnc_client')
    @patch('app.core.gene_normalization.gene_staging.create_staging_record')
    def test_normalize_gene_for_database_hgnc_failure(self, mock_create_staging, mock_get_client, mock_get_gene, mock_db, mock_staging_record):
        """Test normalization when HGNC lookup fails."""
        mock_get_gene.return_value = None

        mock_hgnc_client = Mock()
        mock_hgnc_client.standardize_symbols.return_value = {
            "INVALID_GENE": {
                "approved_symbol": "INVALID_GENE",
                "hgnc_id": None  # No HGNC ID found
            }
        }
        mock_get_client.return_value = mock_hgnc_client
        mock_create_staging.return_value = mock_staging_record

        result = normalize_gene_for_database(
            db=mock_db,
            gene_text="INVALID_GENE",
            source_name="Test",
            original_data={"test": True}
        )

        expected = {
            "status": "requires_manual_review",
            "approved_symbol": None,
            "hgnc_id": None,
            "staging_id": 123,
            "error": None
        }
        assert result == expected
        mock_create_staging.assert_called_once()

    @patch('app.core.gene_normalization._create_staging_record')
    def test_normalize_gene_for_database_invalid_symbol(self, mock_create_staging, mock_db):
        """Test normalization with invalid gene symbol."""
        mock_create_staging.return_value = {
            "status": "requires_manual_review",
            "approved_symbol": None,
            "hgnc_id": None,
            "staging_id": 123,
            "error": None
        }

        result = normalize_gene_for_database(
            db=mock_db,
            gene_text="INVALID123",
            source_name="Test",
            original_data={"test": True}
        )

        assert result["status"] == "requires_manual_review"
        mock_create_staging.assert_called_once()

    @patch('app.core.gene_normalization.gene_crud.get_gene_by_symbol')
    def test_normalize_gene_for_database_exception_handling(self, mock_get_gene, mock_db):
        """Test exception handling in normalization."""
        mock_get_gene.side_effect = Exception("Database error")

        result = normalize_gene_for_database(
            db=mock_db,
            gene_text="PKD1",
            source_name="Test",
            original_data={"test": True}
        )

        expected = {
            "status": "error",
            "approved_symbol": None,
            "hgnc_id": None,
            "staging_id": None,
            "error": "Database error"
        }
        assert result == expected

    def test_normalize_gene_for_database_empty_input(self, mock_db):
        """Test normalization with empty input."""
        with patch('app.core.gene_normalization._create_staging_record') as mock_create_staging:
            mock_create_staging.return_value = {
                "status": "requires_manual_review",
                "approved_symbol": None,
                "hgnc_id": None,
                "staging_id": 123,
                "error": None
            }

            result = normalize_gene_for_database(
                db=mock_db,
                gene_text="",
                source_name="Test"
            )

            assert result["status"] == "requires_manual_review"

    @patch('app.core.gene_normalization.gene_crud.get_gene_by_symbol')
    @patch('app.core.gene_normalization.get_hgnc_client')
    def test_normalize_genes_batch_empty_input(self, mock_get_client, mock_get_gene, mock_db):
        """Test batch normalization with empty input."""
        result = normalize_genes_batch(
            db=mock_db,
            gene_texts=[],
            source_name="Test"
        )

        assert result == {}
        mock_get_gene.assert_not_called()
        mock_get_client.assert_not_called()

    @patch('app.core.gene_normalization.gene_crud.get_gene_by_symbol')
    @patch('app.core.gene_normalization.get_hgnc_client')
    def test_normalize_genes_batch_mixed_results(self, mock_get_client, mock_get_gene, mock_db, mock_existing_gene):
        """Test batch normalization with mixed results."""
        gene_texts = ["PKD1", "NEW_GENE", "INVALID_GENE"]

        # PKD1 exists in database, others need HGNC lookup
        def mock_get_gene_side_effect(db, symbol):
            if symbol == "PKD1":
                return mock_existing_gene
            return None

        mock_get_gene.side_effect = mock_get_gene_side_effect

        mock_hgnc_client = Mock()
        mock_hgnc_client.standardize_symbols_parallel.return_value = {
            "NEW_GENE": {
                "approved_symbol": "NEW_GENE",
                "hgnc_id": "HGNC:12345"
            },
            "INVALID_GENE": {
                "approved_symbol": "INVALID_GENE",
                "hgnc_id": None  # Failed normalization
            }
        }
        mock_get_client.return_value = mock_hgnc_client

        with patch('app.core.gene_normalization._create_staging_record') as mock_create_staging:
            mock_create_staging.return_value = {
                "status": "requires_manual_review",
                "approved_symbol": None,
                "hgnc_id": None,
                "staging_id": 123,
                "error": None
            }

            result = normalize_genes_batch(
                db=mock_db,
                gene_texts=gene_texts,
                source_name="Test"
            )

            # Check results
            assert result["PKD1"]["status"] == "normalized"
            assert result["PKD1"]["approved_symbol"] == "PKD1"
            assert result["PKD1"]["hgnc_id"] == "HGNC:8945"

            assert result["NEW_GENE"]["status"] == "normalized"
            assert result["NEW_GENE"]["approved_symbol"] == "NEW_GENE"
            assert result["NEW_GENE"]["hgnc_id"] == "HGNC:12345"

            assert result["INVALID_GENE"]["status"] == "requires_manual_review"

    @patch('app.core.gene_normalization.gene_crud.get_gene_by_symbol')
    @patch('app.core.gene_normalization.get_hgnc_client')
    def test_normalize_genes_batch_all_existing(self, mock_get_client, mock_get_gene, mock_db, mock_existing_gene):
        """Test batch normalization when all genes exist in database."""
        gene_texts = ["PKD1", "PKD2"]

        # All genes exist in database
        mock_get_gene.return_value = mock_existing_gene

        result = normalize_genes_batch(
            db=mock_db,
            gene_texts=gene_texts,
            source_name="Test"
        )

        # Should not call HGNC client since all genes exist
        mock_get_client.assert_called_once()  # Called but not used
        hgnc_client = mock_get_client.return_value
        hgnc_client.standardize_symbols_parallel.assert_not_called()

        # All results should be normalized
        assert all(result[gene]["status"] == "normalized" for gene in gene_texts)

    @patch('app.core.gene_normalization.gene_crud.get_gene_by_symbol')
    @patch('app.core.gene_normalization.get_hgnc_client')
    def test_normalize_genes_batch_with_original_data(self, mock_get_client, mock_get_gene, mock_db):
        """Test batch normalization with original data contexts."""
        gene_texts = ["PKD1", "PKD2"]
        original_data_list = [
            {"pmid": "12345", "mentions": 5},
            {"pmid": "67890", "mentions": 3}
        ]

        mock_get_gene.return_value = None  # No existing genes

        mock_hgnc_client = Mock()
        mock_hgnc_client.standardize_symbols_parallel.return_value = {
            "PKD1": {"approved_symbol": "PKD1", "hgnc_id": "HGNC:8945"},
            "PKD2": {"approved_symbol": "PKD2", "hgnc_id": "HGNC:8946"}
        }
        mock_get_client.return_value = mock_hgnc_client

        result = normalize_genes_batch(
            db=mock_db,
            gene_texts=gene_texts,
            source_name="Test",
            original_data_list=original_data_list
        )

        # Should process successfully
        assert len(result) == 2
        assert all(result[gene]["status"] == "normalized" for gene in gene_texts)

    @patch('app.core.gene_normalization.gene_crud.get_gene_count')
    @patch('app.core.gene_normalization.gene_crud.get_gene_count_with_hgnc')
    @patch('app.core.gene_normalization.gene_staging.get_staging_statistics')
    @patch('app.core.gene_normalization.get_hgnc_client')
    def test_get_normalization_stats(self, mock_get_client, mock_staging_stats, mock_count_hgnc, mock_count_total, mock_db):
        """Test normalization statistics retrieval."""
        mock_count_total.return_value = 1000
        mock_count_hgnc.return_value = 950
        mock_staging_stats.return_value = {
            "pending": 30,
            "approved": 15,
            "rejected": 5,
            "total": 50
        }

        mock_hgnc_client = Mock()
        mock_hgnc_client.get_cache_info.return_value = {
            "symbol_to_hgnc_id": {"hits": 100, "misses": 10}
        }
        mock_get_client.return_value = mock_hgnc_client

        result = get_normalization_stats(mock_db)

        expected = {
            "total_genes": 1000,
            "genes_with_hgnc_id": 950,
            "genes_without_hgnc_id": 50,
            "normalization_coverage": 95.0,
            "staging_records": {
                "pending": 30,
                "approved": 15,
                "rejected": 5,
                "total": 50
            },
            "hgnc_cache_info": {
                "symbol_to_hgnc_id": {"hits": 100, "misses": 10}
            }
        }
        assert result == expected

    @patch('app.core.gene_normalization.gene_crud.get_gene_count')
    def test_get_normalization_stats_exception(self, mock_count_total, mock_db):
        """Test normalization statistics with exception."""
        mock_count_total.side_effect = Exception("Database error")

        result = get_normalization_stats(mock_db)

        assert "error" in result
        assert result["error"] == "Database error"

    @patch('app.core.gene_normalization.get_hgnc_client')
    def test_clear_normalization_cache(self, mock_get_client):
        """Test clearing normalization cache."""
        mock_hgnc_client = Mock()
        mock_get_client.return_value = mock_hgnc_client

        clear_normalization_cache()

        mock_hgnc_client.clear_cache.assert_called_once()

    def test_get_hgnc_client_singleton(self):
        """Test that get_hgnc_client returns the same instance."""
        client1 = get_hgnc_client()
        client2 = get_hgnc_client()

        assert client1 is client2  # Should be the same instance

    @patch('app.core.gene_normalization.gene_staging.create_staging_record')
    def test_create_staging_record_success(self, mock_create_staging, mock_db, mock_staging_record):
        """Test successful staging record creation."""
        from app.core.gene_normalization import _create_staging_record

        mock_create_staging.return_value = mock_staging_record

        result = _create_staging_record(
            db=mock_db,
            gene_text="INVALID_GENE",
            source_name="Test",
            original_data={"test": True},
            reason="Test failure"
        )

        expected = {
            "status": "requires_manual_review",
            "approved_symbol": None,
            "hgnc_id": None,
            "staging_id": 123,
            "error": None
        }
        assert result == expected

    @patch('app.core.gene_normalization.gene_staging.create_staging_record')
    def test_create_staging_record_failure(self, mock_create_staging, mock_db):
        """Test staging record creation failure."""
        from app.core.gene_normalization import _create_staging_record

        mock_create_staging.side_effect = Exception("Staging error")

        result = _create_staging_record(
            db=mock_db,
            gene_text="INVALID_GENE",
            source_name="Test",
            original_data={"test": True},
            reason="Test failure"
        )

        expected = {
            "status": "error",
            "approved_symbol": None,
            "hgnc_id": None,
            "staging_id": None,
            "error": "Staging creation failed: Staging error"
        }
        assert result == expected

class TestIntegration:
    """Integration tests for gene normalization."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @patch('app.core.gene_normalization.gene_crud.get_gene_by_symbol')
    @patch('app.core.gene_normalization.get_hgnc_client')
    def test_end_to_end_normalization_workflow(self, mock_get_client, mock_get_gene, mock_db):
        """Test complete normalization workflow."""
        # Simulate mixed scenario: some genes exist, some need HGNC lookup, some fail
        gene_texts = ["PKD1", "NEW_GENE", "INVALID123"]

        # PKD1 exists in database
        existing_gene = Mock(spec=Gene)
        existing_gene.approved_symbol = "PKD1"
        existing_gene.hgnc_id = "HGNC:8945"

        def mock_get_gene_side_effect(db, symbol):
            if symbol == "PKD1":
                return existing_gene
            return None

        mock_get_gene.side_effect = mock_get_gene_side_effect

        # HGNC client returns mixed results
        mock_hgnc_client = Mock()
        mock_hgnc_client.standardize_symbols_parallel.return_value = {
            "NEW_GENE": {
                "approved_symbol": "NEW_GENE_CORRECTED",
                "hgnc_id": "HGNC:12345"
            }
        }
        mock_get_client.return_value = mock_hgnc_client

        # Mock staging for invalid genes
        with patch('app.core.gene_normalization._create_staging_record') as mock_create_staging:
            mock_create_staging.return_value = {
                "status": "requires_manual_review",
                "approved_symbol": None,
                "hgnc_id": None,
                "staging_id": 999,
                "error": None
            }

            # Process batch
            result = normalize_genes_batch(
                db=mock_db,
                gene_texts=gene_texts,
                source_name="TestSource"
            )

            # Verify results
            assert len(result) == 2  # Only valid gene symbols processed

            # PKD1 should be found in database
            assert result["PKD1"]["status"] == "normalized"
            assert result["PKD1"]["approved_symbol"] == "PKD1"
            assert result["PKD1"]["hgnc_id"] == "HGNC:8945"

            # NEW_GENE should be normalized via HGNC
            assert result["NEW_GENE"]["status"] == "normalized"
            assert result["NEW_GENE"]["approved_symbol"] == "NEW_GENE_CORRECTED"
            assert result["NEW_GENE"]["hgnc_id"] == "HGNC:12345"

    def test_performance_characteristics(self, mock_db):
        """Test that batch processing is more efficient than individual calls."""
        # This test verifies the batch processing optimization
        large_gene_list = [f"GENE_{i}" for i in range(100)]

        with patch('app.core.gene_normalization.gene_crud.get_gene_by_symbol') as mock_get_gene:
            with patch('app.core.gene_normalization.get_hgnc_client') as mock_get_client:
                mock_get_gene.return_value = None  # No existing genes

                mock_hgnc_client = Mock()
                mock_hgnc_client.standardize_symbols_parallel.return_value = {
                    gene: {"approved_symbol": gene, "hgnc_id": f"HGNC:{i}"}
                    for i, gene in enumerate(large_gene_list)
                }
                mock_get_client.return_value = mock_hgnc_client

                # Process batch
                result = normalize_genes_batch(
                    db=mock_db,
                    gene_texts=large_gene_list,
                    source_name="TestSource"
                )

                # Should make only one parallel call, not 100 individual calls
                mock_hgnc_client.standardize_symbols_parallel.assert_called_once()

                # All genes should be processed
                assert len(result) == 100
                assert all(result[gene]["status"] == "normalized" for gene in large_gene_list)
