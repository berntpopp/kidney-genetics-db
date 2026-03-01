"""
Tests for gnomAD bulk TSV parsing in GnomADAnnotationSource.

Verifies that the bulk constraint metrics TSV is correctly parsed and
produces annotation dicts with the same field names as the GraphQL API path.
"""

from pathlib import Path

import pytest

# Sample TSV matching real gnomAD v4.1 column names
SAMPLE_TSV_HEADER = (
    "gene\tgene_id\ttranscript\tcanonical\tmane_select\t"
    "lof_hc_lc.obs\tlof_hc_lc.exp\tlof_hc_lc.possible\tlof_hc_lc.oe\t"
    "lof_hc_lc.mu\tlof_hc_lc.pLI\tlof_hc_lc.pNull\tlof_hc_lc.pRec\t"
    "lof.obs\tlof.exp\tlof.possible\tlof.oe\tlof.mu\t"
    "lof.pLI\tlof.pNull\tlof.pRec\t"
    "lof.oe_ci.lower\tlof.oe_ci.upper\t"
    "lof.oe_ci.upper_rank\tlof.oe_ci.upper_bin_decile\t"
    "lof.z_raw\tlof.z_score\t"
    "mis.obs\tmis.exp\tmis.possible\tmis.oe\tmis.mu\t"
    "mis.oe_ci.lower\tmis.oe_ci.upper\tmis.z_raw\tmis.z_score\t"
    "mis_pphen.obs\tmis_pphen.exp\tmis_pphen.possible\tmis_pphen.oe\t"
    "syn.obs\tsyn.exp\tsyn.possible\tsyn.oe\tsyn.mu\t"
    "syn.oe_ci.lower\tsyn.oe_ci.upper\tsyn.z_raw\tsyn.z_score\t"
    "constraint_flags\tlevel\ttranscript_type\tchromosome\t"
    "cds_length\tnum_coding_exons"
)

# PKD1 row with canonical=true
SAMPLE_PKD1_ROW = (
    "PKD1\t5310\tNM_001009944.3\ttrue\ttrue\t"
    "10\t43.0\t193\t0.2326\t"
    "7.06e-07\t0.999\t0.0001\t0.0009\t"
    "10\t43.0\t193\t0.2326\t7.06e-07\t"
    "0.999\t0.0001\t0.0009\t"
    "0.1370\t0.1520\t"
    "100\t0\t"
    "5.50\t5.2300\t"
    "500\t600.0\t2870\t0.8333\t7.66e-06\t"
    "0.78\t0.89\t2.50\t3.4500\t"
    "220\t190.6\t890\t1.154\t"
    "316\t296.0\t994\t1.068\t3.02e-06\t"
    "0.97\t1.17\t-1.17\t-0.1200\t"
    "[]\tNA\tNA\tchr16\t"
    "12912\t46"
)

# PKD2 row with canonical=true
SAMPLE_PKD2_ROW = (
    "PKD2\t5311\tNM_000297.4\ttrue\ttrue\t"
    "5\t20.0\t100\t0.25\t"
    "3.5e-07\t0.500\t0.35\t0.15\t"
    "5\t20.0\t100\t0.2500\t3.5e-07\t"
    "0.500\t0.35\t0.15\t"
    "0.20\t0.4500\t"
    "200\t1\t"
    "1.50\t1.2300\t"
    "300\t400.0\t1500\t0.75\t5.0e-06\t"
    "0.65\t0.85\t1.20\t0.4500\t"
    "120\t100.0\t500\t1.2\t"
    "200\t180.0\t600\t1.111\t2.0e-06\t"
    "0.95\t1.20\t-0.50\t0.3200\t"
    "[]\tNA\tNA\tchr4\t"
    "2904\t15"
)

# Non-canonical row (should be skipped)
SAMPLE_NON_CANONICAL_ROW = (
    "PKD1\t5310\tNM_ALTERNATE.1\tfalse\tfalse\t"
    "0\t0\t0\t0\t"
    "0\t0\t0\t0\t"
    "0\t0\t0\t0\t0\t"
    "0\t0\t0\t"
    "0\t0\t"
    "0\t0\t"
    "0\t0\t"
    "0\t0\t0\t0\t0\t"
    "0\t0\t0\t0\t"
    "0\t0\t0\t0\t"
    "0\t0\t0\t0\t0\t"
    "0\t0\t0\t0\t"
    "[]\tNA\tNA\tchr16\t"
    "100\t5"
)


def _create_tsv(tmp_path: Path, *rows: str) -> Path:
    """Create a temporary TSV file with header and given data rows."""
    content = SAMPLE_TSV_HEADER + "\n" + "\n".join(rows) + "\n"
    tsv_file = tmp_path / "gnomad_constraint.tsv"
    tsv_file.write_text(content)
    return tsv_file


@pytest.mark.unit
class TestGnomADBulkParsing:
    """Test TSV parsing extracts correct fields."""

    def test_parse_constraint_tsv_extracts_core_fields(self, tmp_path: Path) -> None:
        """Parse gnomAD constraint TSV extracts pLI, LOEUF, z-scores."""
        from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource

        tsv_file = _create_tsv(tmp_path, SAMPLE_PKD1_ROW, SAMPLE_PKD2_ROW)

        source = GnomADAnnotationSource.__new__(GnomADAnnotationSource)
        data = source.parse_bulk_file(tsv_file)

        assert "PKD1" in data
        assert data["PKD1"]["pli"] == pytest.approx(0.999)
        assert data["PKD1"]["oe_lof_upper"] == pytest.approx(0.152)
        assert data["PKD1"]["lof_z"] == pytest.approx(5.23)
        assert data["PKD1"]["mis_z"] == pytest.approx(3.45)
        assert data["PKD1"]["syn_z"] == pytest.approx(-0.12)
        assert data["PKD1"]["oe_lof"] == pytest.approx(0.2326)

        assert "PKD2" in data
        assert data["PKD2"]["pli"] == pytest.approx(0.5)
        assert data["PKD2"]["oe_lof_upper"] == pytest.approx(0.45)

    def test_parse_skips_non_canonical_transcripts(self, tmp_path: Path) -> None:
        """Non-canonical transcripts are excluded from bulk data."""
        from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource

        tsv_file = _create_tsv(
            tmp_path, SAMPLE_PKD1_ROW, SAMPLE_NON_CANONICAL_ROW
        )

        source = GnomADAnnotationSource.__new__(GnomADAnnotationSource)
        data = source.parse_bulk_file(tsv_file)

        # Should have PKD1 from the canonical row only
        assert "PKD1" in data
        assert data["PKD1"]["pli"] == pytest.approx(0.999)

    def test_parse_includes_metadata_fields(self, tmp_path: Path) -> None:
        """Parsed data includes source_version and gene identifiers."""
        from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource

        tsv_file = _create_tsv(tmp_path, SAMPLE_PKD1_ROW)

        source = GnomADAnnotationSource.__new__(GnomADAnnotationSource)
        data = source.parse_bulk_file(tsv_file)

        assert data["PKD1"]["source_version"] == "gnomad_v4"
        assert data["PKD1"]["gene_symbol"] == "PKD1"
        assert data["PKD1"]["canonical_transcript"] == "NM_001009944.3"

    def test_parse_includes_oe_ratios_and_counts(self, tmp_path: Path) -> None:
        """Parsed data includes O/E ratios and raw counts."""
        from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource

        tsv_file = _create_tsv(tmp_path, SAMPLE_PKD1_ROW)

        source = GnomADAnnotationSource.__new__(GnomADAnnotationSource)
        data = source.parse_bulk_file(tsv_file)

        pkd1 = data["PKD1"]
        # O/E ratios
        assert "oe_lof_lower" in pkd1
        assert "oe_mis" in pkd1
        assert "oe_mis_lower" in pkd1
        assert "oe_mis_upper" in pkd1
        assert "oe_syn" in pkd1
        # Raw counts
        assert "obs_lof" in pkd1
        assert "exp_lof" in pkd1
        assert "obs_mis" in pkd1
        assert "exp_mis" in pkd1
        assert "obs_syn" in pkd1
        assert "exp_syn" in pkd1

    def test_parse_handles_na_values(self, tmp_path: Path) -> None:
        """NA values in TSV are excluded from parsed annotations."""
        from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource

        # Create a row with NA in rank/decile fields
        tsv_file = _create_tsv(tmp_path, SAMPLE_PKD1_ROW)

        source = GnomADAnnotationSource.__new__(GnomADAnnotationSource)
        data = source.parse_bulk_file(tsv_file)

        # None values should be stripped
        for value in data["PKD1"].values():
            assert value is not None


@pytest.mark.unit
class TestGnomADBulkLookup:
    """Test bulk lookup returns correct data or None."""

    def test_lookup_returns_annotation_for_known_gene(self) -> None:
        """Genes in bulk data return their annotation dict."""
        from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource

        source = GnomADAnnotationSource.__new__(GnomADAnnotationSource)
        source._bulk_data = {"PKD1": {"pli": 0.99, "source_version": "gnomad_v4"}}

        result = source.lookup_gene("PKD1")
        assert result is not None
        assert result["pli"] == 0.99

    def test_lookup_returns_none_for_missing_gene(self) -> None:
        """Genes not in bulk data return None."""
        from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource

        source = GnomADAnnotationSource.__new__(GnomADAnnotationSource)
        source._bulk_data = {"PKD1": {"pli": 0.99}}

        result = source.lookup_gene("NONEXISTENT")
        assert result is None

    def test_lookup_returns_none_when_data_not_loaded(self) -> None:
        """Lookup returns None when bulk data hasn't been loaded."""
        from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource

        source = GnomADAnnotationSource.__new__(GnomADAnnotationSource)
        source._bulk_data = None

        result = source.lookup_gene("PKD1")
        assert result is None
