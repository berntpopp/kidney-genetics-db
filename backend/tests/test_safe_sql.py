"""Tests for SQL identifier safety utilities."""

import pytest

from app.db.safe_sql import safe_identifier


@pytest.mark.unit
class TestSafeIdentifier:
    """Verify safe_identifier rejects invalid SQL identifiers."""

    def test_valid_identifier(self):
        assert safe_identifier("gene_scores") == "gene_scores"

    def test_valid_single_word(self):
        assert safe_identifier("genes") == "genes"

    def test_rejects_sql_injection(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("gene_scores; DROP TABLE users")

    def test_rejects_semicolon(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("test;")

    def test_rejects_dash(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("gene-scores")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("gene scores")

    def test_rejects_uppercase(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("GeneScores")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("a" * 64)

    def test_max_length_63(self):
        assert safe_identifier("a" * 63) == "a" * 63

    def test_rejects_leading_number(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("1gene")
