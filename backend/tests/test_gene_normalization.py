"""
Tests for gene normalization utility functions.

These tests cover the pure utility functions in gene_normalizer module:
- clean_gene_text: Gene text cleaning and preprocessing
- is_likely_gene_symbol: Gene symbol validation heuristics
"""

import pytest

from app.core.gene_normalizer import (
    clean_gene_text,
    is_likely_gene_symbol,
)


@pytest.mark.unit
class TestGeneTextCleaning:
    """Test gene text cleaning and validation functions."""

    @pytest.mark.parametrize(
        "input_text,expected",
        [
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
        ],
    )
    def test_clean_gene_text(self, input_text, expected):
        """Test gene text cleaning with various input formats."""
        result = clean_gene_text(input_text)
        assert result == expected

    def test_clean_gene_text_none_handling(self):
        """Test that empty string is returned for None-like input."""
        # The function expects a string, so we pass empty string
        result = clean_gene_text("")
        assert result == ""


@pytest.mark.unit
class TestGeneSymbolValidation:
    """Test gene symbol validation heuristics."""

    @pytest.mark.parametrize(
        "gene_text,expected",
        [
            # Valid gene symbols
            ("PKD1", True),
            ("ABCA4", True),
            ("COL4A5", True),
            ("PKD1-AS1", True),  # Antisense transcript
            ("C5orf42", True),  # Chromosome-based name
            ("ALBUMIN", True),  # Should pass basic checks
            # Invalid: empty or too short
            ("", False),
            ("A", False),
            # Invalid: excluded common terms
            ("UNKNOWN", False),
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
            # Invalid: too long
            ("THIS_IS_A_VERY_LONG_GENE_NAME_THAT_IS_TOO_LONG", False),
            # Invalid: only numbers
            ("12345", False),
        ],
    )
    def test_is_likely_gene_symbol(self, gene_text, expected):
        """Test gene symbol validation with various inputs."""
        result = is_likely_gene_symbol(gene_text)
        assert result == expected

    def test_is_likely_gene_symbol_expects_clean_input(self):
        """Test that validation expects cleaned (uppercased) input.

        Note: is_likely_gene_symbol is designed to work with output from
        clean_gene_text, which returns uppercase strings. The exclusion
        check uses uppercase terms.
        """
        # When properly cleaned (uppercase), excluded terms are rejected
        assert is_likely_gene_symbol("NONE") is False
        assert is_likely_gene_symbol("UNKNOWN") is False

        # Lowercase input is NOT automatically excluded - use clean_gene_text first
        # This is correct behavior since the function expects cleaned input
        cleaned = clean_gene_text("none")
        assert is_likely_gene_symbol(cleaned) is False  # "NONE" is excluded
