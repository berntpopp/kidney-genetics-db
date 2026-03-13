"""Tests for materialized view definitions."""

import pytest


@pytest.mark.unit
class TestGeneDistributionAnalysis:
    """Verify gene_distribution_analysis references valid gene_scores columns."""

    def test_no_classification_column_reference(self):
        from app.db.materialized_views import MaterializedViewManager

        config = MaterializedViewManager.MATERIALIZED_VIEWS["gene_distribution_analysis"]
        definition = config.definition

        # Should reference 'evidence_tier' instead of 'classification'
        assert "evidence_tier" in definition
        assert "GROUP BY score_bin, evidence_tier" in definition
        assert "GROUP BY source_count, evidence_tier" in definition

    def test_no_bare_classification_in_definition(self):
        from app.db.materialized_views import MaterializedViewManager

        config = MaterializedViewManager.MATERIALIZED_VIEWS["gene_distribution_analysis"]
        definition = config.definition

        # 'classification' should not appear
        lines = definition.strip().split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("--"):
                continue
            assert (
                "classification" not in stripped.lower() or "evidence_tier" in stripped.lower()
            ), f"Found 'classification' in matview definition: {stripped}"
