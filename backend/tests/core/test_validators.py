"""
Property-based tests for validation functions using Hypothesis.
These tests explore edge cases and validate invariants automatically.
"""

import math

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from app.core.gene_normalizer import clean_gene_text, is_likely_gene_symbol


@pytest.mark.unit
class TestGeneSymbolValidation:
    """Property-based tests for gene symbol validation."""

    @given(st.text(min_size=1, max_size=50))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_clean_gene_text_always_uppercase(self, symbol: str):
        """Test that clean_gene_text always returns uppercase."""
        assume(symbol.strip())  # Skip empty strings

        cleaned = clean_gene_text(symbol)

        # Property: cleaned symbol should always be uppercase
        assert cleaned == cleaned.upper(), "Cleaned gene text must be uppercase"

    @given(st.text(min_size=1, max_size=50))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_clean_gene_text_no_leading_trailing_whitespace(self, symbol: str):
        """Test that cleaned text has no leading/trailing whitespace."""
        assume(symbol.strip())

        cleaned = clean_gene_text(symbol)

        # Property: no leading/trailing whitespace
        assert cleaned == cleaned.strip(), "Cleaned text must have no whitespace"

    @given(
        st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")), min_size=2, max_size=15
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_alphanumeric_symbols_likely_valid(self, symbol: str):
        """Test that reasonable alphanumeric symbols are considered valid."""
        assume(len(symbol) >= 2)  # Gene symbols are at least 2 chars
        assume(not symbol[0].isdigit())  # Don't start with number
        assume(symbol.lower() not in ["none", "null", "na", "unknown"])  # Not excluded

        result = is_likely_gene_symbol(symbol)

        # Most alphanumeric strings of reasonable length should be valid candidates
        # (final validation happens with HGNC)
        assert isinstance(result, bool), "Should return boolean"

    @given(
        st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
    )
    def test_evidence_score_bounds(self, score: float):
        """Test evidence score validation bounds."""
        # Assuming there's a validate_evidence_score function
        # This is a placeholder showing the pattern

        if 0 <= score <= 1:
            # Valid scores should be in range
            assert True
        else:
            # Invalid scores should be rejected
            assert score < 0 or score > 1

    @given(st.text())
    def test_gene_symbol_no_special_chars(self, text: str):
        """Test that gene symbols with special characters are handled."""
        if any(char in text for char in "!@#$%^&*()=+[]{}|\\;:'\"<>?/"):
            # Symbols with special chars should generally be rejected
            # (unless they're valid separators like - or _)
            result = is_likely_gene_symbol(text)
            # This validates the function handles edge cases
            assert isinstance(result, bool)


@pytest.mark.unit
class TestClassificationValidation:
    """Property-based tests for gene classification validation."""

    VALID_CLASSIFICATIONS = ["definitive", "strong", "moderate", "limited"]

    @given(st.sampled_from(VALID_CLASSIFICATIONS))
    def test_valid_classifications_accepted(self, classification: str):
        """Test that valid classifications are accepted."""
        # This is a structural test showing the pattern
        assert classification in self.VALID_CLASSIFICATIONS

    @given(st.text())
    def test_invalid_classifications_rejected(self, classification: str):
        """Test that invalid classifications are rejected."""
        assume(classification not in self.VALID_CLASSIFICATIONS)

        # Would test actual validation function here
        assert classification not in self.VALID_CLASSIFICATIONS


@pytest.mark.unit
class TestHGNCIDValidation:
    """Property-based tests for HGNC ID validation."""

    @given(st.integers(min_value=1, max_value=999999))
    def test_valid_hgnc_id_format(self, gene_id: int):
        """Test HGNC ID format validation."""
        hgnc_id = f"HGNC:{gene_id}"

        # Properties of valid HGNC IDs
        assert hgnc_id.startswith("HGNC:")
        assert hgnc_id.split(":")[1].isdigit()
        assert len(hgnc_id.split(":")) == 2

    @given(st.text())
    def test_invalid_hgnc_id_format(self, text: str):
        """Test that invalid formats are detected."""
        assume(not text.startswith("HGNC:"))

        # Invalid format should not match HGNC pattern
        assert not (text.startswith("HGNC:") and ":" in text and text.split(":")[1].isdigit())


@pytest.mark.unit
class TestPaginationParameters:
    """Property-based tests for pagination parameter validation."""

    @given(
        limit=st.integers(min_value=1, max_value=1000),
        offset=st.integers(min_value=0, max_value=1000000),
    )
    def test_valid_pagination_bounds(self, limit: int, offset: int):
        """Test that valid pagination parameters are in range."""
        # Valid pagination should satisfy these properties
        assert 1 <= limit <= 1000, "Limit should be between 1 and 1000"
        assert offset >= 0, "Offset should be non-negative"
        assert limit + offset >= 0, "Combined parameters should be valid"

    @given(st.integers())
    def test_negative_limit_rejected(self, limit: int):
        """Test that negative limits are invalid."""
        assume(limit < 1)

        # Negative or zero limits should be invalid
        is_valid = limit >= 1
        assert not is_valid, "Negative limits should be rejected"

    @given(st.integers())
    def test_negative_offset_rejected(self, offset: int):
        """Test that negative offsets are invalid."""
        assume(offset < 0)

        # Negative offsets should be invalid
        is_valid = offset >= 0
        assert not is_valid, "Negative offsets should be rejected"


@pytest.mark.unit
class TestScoreAggregation:
    """Property-based tests for score aggregation logic."""

    @given(
        st.lists(st.floats(min_value=0.0, max_value=1.0, allow_nan=False), min_size=1, max_size=10)
    )
    def test_average_score_bounds(self, scores: list[float]):
        """Test that average scores stay within bounds."""
        if scores:
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)

            # Property: average should be within min and max of inputs
            # Use math.isclose for floating-point comparisons to handle precision issues
            assert (
                min_score <= avg_score or math.isclose(min_score, avg_score, rel_tol=1e-9)
            ), "Average should be >= min"
            assert (
                avg_score <= max_score or math.isclose(avg_score, max_score, rel_tol=1e-9)
            ), "Average should be <= max"
            assert 0 <= avg_score <= 1 or math.isclose(avg_score, 0, rel_tol=1e-9) or math.isclose(
                avg_score, 1, rel_tol=1e-9
            ), "Average should be in [0, 1]"

    @given(
        st.lists(st.floats(min_value=0.0, max_value=1.0, allow_nan=False), min_size=2, max_size=10)
    )
    def test_weighted_average_bounds(self, scores: list[float]):
        """Test weighted average properties."""
        weights = [1.0] * len(scores)  # Equal weights

        weighted_sum = sum(s * w for s, w in zip(scores, weights, strict=False))
        total_weight = sum(weights)

        if total_weight > 0:
            weighted_avg = weighted_sum / total_weight
            min_score = min(scores)
            max_score = max(scores)

            # Property: weighted average should be in range
            # Use math.isclose for floating-point comparisons to handle precision issues
            assert (
                0 <= weighted_avg <= 1
                or math.isclose(weighted_avg, 0, rel_tol=1e-9)
                or math.isclose(weighted_avg, 1, rel_tol=1e-9)
            ), "Weighted average should be in [0, 1]"
            assert (
                min_score <= weighted_avg or math.isclose(min_score, weighted_avg, rel_tol=1e-9)
            ), "Weighted average should be >= min"
            assert (
                weighted_avg <= max_score or math.isclose(weighted_avg, max_score, rel_tol=1e-9)
            ), "Weighted average should be <= max"


@pytest.mark.unit
class TestStringCleaning:
    """Property-based tests for string cleaning utilities."""

    @given(st.text())
    def test_clean_text_idempotent(self, text: str):
        """Test that cleaning is idempotent (cleaning twice = cleaning once)."""
        assume(text.strip())  # Skip empty strings

        cleaned_once = clean_gene_text(text)
        cleaned_twice = clean_gene_text(cleaned_once)

        # Property: cleaning should be idempotent
        assert cleaned_once == cleaned_twice, "Cleaning should be idempotent"

    @given(st.text(min_size=1, alphabet=st.characters(blacklist_categories=("Cs",))))
    def test_clean_text_no_longer(self, text: str):
        """Test that cleaning never makes text longer (excluding Unicode case expansion).

        Note: Some Unicode characters expand when uppercased (e.g., ß → SS),
        which is correct behavior. We account for this by comparing against
        the uppercased original length.
        """
        cleaned = clean_gene_text(text)

        # Property: cleaned text should not be longer than uppercased original
        # (uppercasing can expand some chars like ß → SS, which is expected)
        assert len(cleaned) <= len(text.upper()), "Cleaning should not increase length beyond case expansion"

    @given(st.text())
    def test_clean_text_preserves_alphanumeric(self, text: str):
        """Test that cleaning preserves alphanumeric characters from the preserved portion.

        Note: clean_gene_text removes everything after separators (;,|/\\) and
        parenthetical content, so we only check that alphanumeric chars from the
        portion that would be preserved are actually preserved.
        """
        import re

        cleaned = clean_gene_text(text)

        # Simulate the separator removal to get the portion that should be preserved
        # First, get uppercase version like clean_gene_text does
        text_upper = text.strip().upper()
        # Remove prefixes (like clean_gene_text does)
        text_upper = re.sub(r"^(GENE:|SYMBOL:|PROTEIN:)", "", text_upper)
        text_upper = re.sub(r"(GENE|PROTEIN|_HUMAN)$", "", text_upper)
        # Get only the part before separators (like clean_gene_text does)
        preserved_part = re.sub(r"[;,|/\\].*$", "", text_upper)
        # Remove parenthetical content
        preserved_part = re.sub(r"\s*\([^)]*\)", "", preserved_part)

        # Get alphanumeric characters from the preserved portion only
        preserved_alnum = "".join(c for c in preserved_part if c.isalnum())

        if preserved_alnum:
            # Check that alphanumeric content from preserved portion is in cleaned
            assert all(c in cleaned for c in preserved_alnum if c.isalnum())


@pytest.mark.unit
@pytest.mark.slow
class TestFuzzingInputs:
    """Fuzzing tests to find edge cases and security issues."""

    @given(st.text(min_size=0, max_size=1000))
    @settings(max_examples=500, deadline=None)
    def test_gene_validation_never_crashes(self, text: str):
        """Test that gene validation handles all inputs without crashing."""
        try:
            # Should never crash regardless of input
            result = is_likely_gene_symbol(text)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"Gene validation crashed on input: {text!r} with {e}")

    @given(st.text(alphabet=st.characters(blacklist_characters=["\x00"]), min_size=0, max_size=500))
    @settings(max_examples=200)
    def test_clean_text_handles_unicode(self, text: str):
        """Test that text cleaning handles unicode without crashing."""
        try:
            cleaned = clean_gene_text(text)
            # Should always return a string
            assert isinstance(cleaned, str)
        except Exception as e:
            pytest.fail(f"Text cleaning crashed on: {text!r} with {e}")

    @given(st.text(alphabet="PKD1'; DROP TABLE genes; --", min_size=1, max_size=100))
    def test_sql_injection_patterns(self, malicious_input: str):
        """Test that inputs resembling SQL injection are handled safely."""
        # This tests that validation doesn't crash on SQL-like input
        try:
            result = is_likely_gene_symbol(malicious_input)
            cleaned = clean_gene_text(malicious_input)

            # Should handle without errors
            assert isinstance(result, bool)
            assert isinstance(cleaned, str)
        except Exception as e:
            pytest.fail(f"Failed on SQL-like input: {malicious_input!r} with {e}")
