"""
Tests for GTEx bulk GCT parsing in GTExAnnotationSource.

Verifies that the bulk median gene expression GCT file is correctly parsed
and produces annotation dicts with the same field names as the API path.
"""

from pathlib import Path

import pytest

# GCT v1.2 format: 2 header lines, then tab-separated gene × tissue matrix
# Line 1: #1.2
# Line 2: num_genes<tab>num_tissues
# Line 3: Name<tab>Description<tab>tissue1<tab>tissue2<tab>...
# Line 4+: gencode_id<tab>gene_symbol<tab>tpm1<tab>tpm2<tab>...

SAMPLE_GCT_CONTENT = """\
#1.2
3\t4
Name\tDescription\tWhole_Blood\tBrain_Cortex\tKidney_Cortex\tLiver
ENSG00000008710.20\tPKD1\t5.123\t0.456\t12.340\t0.001
ENSG00000118762.15\tPKD2\t8.900\t1.230\t9.876\t0.500
ENSG00000141510.18\tTP53\t3.210\t0.890\t4.560\t7.800
"""

# GCT with NA/missing values
SAMPLE_GCT_WITH_NA = """\
#1.2
1\t3
Name\tDescription\tWhole_Blood\tBrain_Cortex\tKidney_Cortex
ENSG00000008710.20\tPKD1\t5.123\tNA\t12.340
"""


def _create_gct(tmp_path: Path, content: str = SAMPLE_GCT_CONTENT) -> Path:
    """Create a temporary GCT file."""
    gct_file = tmp_path / "gene_median_tpm.gct"
    gct_file.write_text(content)
    return gct_file


@pytest.mark.unit
class TestGTExBulkParsing:
    """Test GCT parsing extracts correct fields."""

    def test_parse_gct_extracts_tissue_expression(self, tmp_path: Path) -> None:
        """Parse GTEx GCT file extracts tissue-specific TPM values."""
        from app.pipeline.sources.annotations.gtex import GTExAnnotationSource

        gct_file = _create_gct(tmp_path)

        source = GTExAnnotationSource.__new__(GTExAnnotationSource)
        data = source.parse_bulk_file(gct_file)

        assert "PKD1" in data
        tissues = data["PKD1"]["tissues"]
        assert tissues["Whole_Blood"]["median_tpm"] == pytest.approx(5.123)
        assert tissues["Brain_Cortex"]["median_tpm"] == pytest.approx(0.456)
        assert tissues["Kidney_Cortex"]["median_tpm"] == pytest.approx(12.34)
        assert tissues["Liver"]["median_tpm"] == pytest.approx(0.001)

    def test_parse_gct_extracts_all_genes(self, tmp_path: Path) -> None:
        """All genes in GCT are parsed."""
        from app.pipeline.sources.annotations.gtex import GTExAnnotationSource

        gct_file = _create_gct(tmp_path)

        source = GTExAnnotationSource.__new__(GTExAnnotationSource)
        data = source.parse_bulk_file(gct_file)

        assert len(data) == 3
        assert "PKD1" in data
        assert "PKD2" in data
        assert "TP53" in data

    def test_parse_gct_includes_metadata(self, tmp_path: Path) -> None:
        """Parsed data includes dataset version, gencode_id, gene_symbol."""
        from app.pipeline.sources.annotations.gtex import GTExAnnotationSource

        gct_file = _create_gct(tmp_path)

        source = GTExAnnotationSource.__new__(GTExAnnotationSource)
        data = source.parse_bulk_file(gct_file)

        pkd1 = data["PKD1"]
        assert pkd1["dataset_version"] == "gtex_v8"
        assert pkd1["gencode_id"] == "ENSG00000008710.20"
        assert pkd1["gene_symbol"] == "PKD1"

    def test_parse_gct_tissue_unit_is_tpm(self, tmp_path: Path) -> None:
        """All tissue entries have unit='TPM'."""
        from app.pipeline.sources.annotations.gtex import GTExAnnotationSource

        gct_file = _create_gct(tmp_path)

        source = GTExAnnotationSource.__new__(GTExAnnotationSource)
        data = source.parse_bulk_file(gct_file)

        for tissue_data in data["PKD1"]["tissues"].values():
            assert tissue_data["unit"] == "TPM"

    def test_parse_gct_handles_na_values(self, tmp_path: Path) -> None:
        """NA values in GCT are excluded from tissue data."""
        from app.pipeline.sources.annotations.gtex import GTExAnnotationSource

        gct_file = _create_gct(tmp_path, SAMPLE_GCT_WITH_NA)

        source = GTExAnnotationSource.__new__(GTExAnnotationSource)
        data = source.parse_bulk_file(gct_file)

        tissues = data["PKD1"]["tissues"]
        assert "Brain_Cortex" not in tissues
        assert "Whole_Blood" in tissues
        assert "Kidney_Cortex" in tissues

    def test_parse_gct_empty_file(self, tmp_path: Path) -> None:
        """Empty GCT file returns empty dict."""
        from app.pipeline.sources.annotations.gtex import GTExAnnotationSource

        gct_content = "#1.2\n0\t0\nName\tDescription\n"
        gct_file = _create_gct(tmp_path, gct_content)

        source = GTExAnnotationSource.__new__(GTExAnnotationSource)
        data = source.parse_bulk_file(gct_file)

        assert data == {}


@pytest.mark.unit
class TestGTExBulkLookup:
    """Test bulk lookup returns correct data or None."""

    def test_lookup_returns_annotation_for_known_gene(self) -> None:
        """Genes in bulk data return their annotation dict."""
        from app.pipeline.sources.annotations.gtex import GTExAnnotationSource

        source = GTExAnnotationSource.__new__(GTExAnnotationSource)
        source._bulk_data = {
            "PKD1": {
                "tissues": {"Whole_Blood": {"median_tpm": 5.0, "unit": "TPM"}},
                "dataset_version": "gtex_v8",
                "gencode_id": "ENSG00000008710.20",
                "gene_symbol": "PKD1",
            }
        }

        result = source.lookup_gene("PKD1")
        assert result is not None
        assert result["gene_symbol"] == "PKD1"
        assert "tissues" in result

    def test_lookup_returns_none_for_missing_gene(self) -> None:
        """Genes not in bulk data return None."""
        from app.pipeline.sources.annotations.gtex import GTExAnnotationSource

        source = GTExAnnotationSource.__new__(GTExAnnotationSource)
        source._bulk_data = {"PKD1": {"tissues": {}}}

        result = source.lookup_gene("NONEXISTENT")
        assert result is None

    def test_lookup_returns_none_when_data_not_loaded(self) -> None:
        """Lookup returns None when bulk data hasn't been loaded."""
        from app.pipeline.sources.annotations.gtex import GTExAnnotationSource

        source = GTExAnnotationSource.__new__(GTExAnnotationSource)
        source._bulk_data = None

        result = source.lookup_gene("PKD1")
        assert result is None
