"""
Tests for ClinVar bulk file parsing, pre-filtering, and NCBI API key support.

Verifies that gene_specific_summary.txt is parsed correctly and that the
bulk pre-filter skips genes with zero ClinVar variants.
"""

from pathlib import Path

import pytest

# Sample gene_specific_summary.txt content
SAMPLE_HEADER = (
    "#Symbol\tGeneID\tTotal_submissions\tTotal_alleles"
    "\tSubmissions_reporting_this_gene"
    "\tAlleles_reported_Pathogenic_Likely_pathogenic"
    "\tGene_MIM_number\tNumber_uncertain\tNumber_with_conflicts\n"
)

SAMPLE_ROWS = """\
PKD1\t5310\t3456\t2100\t3400\t185\t601313\t950\t42
PKD2\t5311\t890\t500\t880\t45\t173910\t210\t15
NPHS1\t4868\t200\t120\t195\t30\t602716\t55\t3
EMPTY_GENE\t99999\t0\t0\t0\t0\t-\t0\t0
"""


def _create_bulk_file(tmp_path: Path, content: str | None = None) -> Path:
    """Create a temporary gene_specific_summary.txt file."""
    if content is None:
        content = SAMPLE_HEADER + SAMPLE_ROWS
    bulk_file = tmp_path / "gene_specific_summary.txt"
    bulk_file.write_text(content)
    return bulk_file


@pytest.mark.unit
class TestClinVarBulkParsing:
    """Test gene_specific_summary.txt parsing."""

    def test_parse_extracts_all_genes(self, tmp_path: Path) -> None:
        """All gene rows are parsed."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        bulk_file = _create_bulk_file(tmp_path)
        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert len(data) == 4
        assert "PKD1" in data
        assert "PKD2" in data
        assert "NPHS1" in data
        assert "EMPTY_GENE" in data

    def test_parse_extracts_allele_counts(self, tmp_path: Path) -> None:
        """Total alleles are extracted correctly."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        bulk_file = _create_bulk_file(tmp_path)
        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert data["PKD1"]["total_alleles"] == 2100
        assert data["PKD2"]["total_alleles"] == 500
        assert data["EMPTY_GENE"]["total_alleles"] == 0

    def test_parse_extracts_pathogenic_counts(self, tmp_path: Path) -> None:
        """Pathogenic/likely pathogenic counts are extracted."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        bulk_file = _create_bulk_file(tmp_path)
        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert data["PKD1"]["pathogenic_likely_pathogenic"] == 185
        assert data["PKD2"]["pathogenic_likely_pathogenic"] == 45

    def test_parse_extracts_uncertain_and_conflicts(self, tmp_path: Path) -> None:
        """VUS and conflict counts are extracted."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        bulk_file = _create_bulk_file(tmp_path)
        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert data["PKD1"]["number_uncertain"] == 950
        assert data["PKD1"]["number_with_conflicts"] == 42

    def test_parse_extracts_gene_id_and_mim(self, tmp_path: Path) -> None:
        """NCBI gene ID and MIM number are extracted."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        bulk_file = _create_bulk_file(tmp_path)
        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert data["PKD1"]["gene_id"] == "5310"
        assert data["PKD1"]["gene_mim_number"] == "601313"

    def test_parse_skips_comment_lines(self, tmp_path: Path) -> None:
        """Lines starting with # are skipped."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        bulk_file = _create_bulk_file(tmp_path)
        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        # "#Symbol..." header line should not appear as a gene
        assert "#Symbol" not in data

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """File with only header returns empty dict."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        bulk_file = _create_bulk_file(tmp_path, SAMPLE_HEADER)
        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert data == {}

    def test_parse_handles_dash_values(self, tmp_path: Path) -> None:
        """Dash values in numeric columns are parsed as 0."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        content = SAMPLE_HEADER + "TESTGENE\t1\t-\t-\t-\t-\t-\t-\t-\n"
        bulk_file = _create_bulk_file(tmp_path, content)
        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert data["TESTGENE"]["total_alleles"] == 0
        assert data["TESTGENE"]["pathogenic_likely_pathogenic"] == 0


@pytest.mark.unit
class TestClinVarBulkPreFilter:
    """Test bulk pre-filter logic."""

    def test_gene_has_variants_returns_true_for_gene_with_alleles(self) -> None:
        """Gene with alleles returns True."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        source._bulk_data = {"PKD1": {"total_alleles": 2100}}

        assert source._gene_has_variants("PKD1") is True

    def test_gene_has_variants_returns_false_for_zero_alleles(self) -> None:
        """Gene with zero alleles returns False."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        source._bulk_data = {"EMPTY_GENE": {"total_alleles": 0}}

        assert source._gene_has_variants("EMPTY_GENE") is False

    def test_gene_has_variants_returns_false_for_missing_gene(self) -> None:
        """Gene not in bulk data returns False."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        source._bulk_data = {"PKD1": {"total_alleles": 2100}}

        assert source._gene_has_variants("NONEXISTENT") is False

    def test_gene_has_variants_returns_none_when_not_loaded(self) -> None:
        """Returns None when bulk data has not been loaded."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        source._bulk_data = None

        assert source._gene_has_variants("PKD1") is None


@pytest.mark.unit
class TestClinVarNCBIApiKey:
    """Test NCBI API key injection."""

    def test_ncbi_params_without_key(self) -> None:
        """Without API key, params contain only extra values."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        source.ncbi_api_key = None

        params = source._ncbi_params({"db": "clinvar"})
        assert "api_key" not in params
        assert params["db"] == "clinvar"

    def test_ncbi_params_with_key(self) -> None:
        """With API key, api_key is injected into params."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        source.ncbi_api_key = "test_key_123"

        params = source._ncbi_params({"db": "clinvar"})
        assert params["api_key"] == "test_key_123"
        assert params["db"] == "clinvar"

    def test_ncbi_params_empty_extra(self) -> None:
        """With no extra params, only api_key is returned (if set)."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        source.ncbi_api_key = "mykey"

        params = source._ncbi_params()
        assert params == {"api_key": "mykey"}
