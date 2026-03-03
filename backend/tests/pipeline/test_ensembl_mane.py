"""
Tests for Ensembl GTF bulk file integration and MANE cross-referencing.

Verifies that:
- GTF lines are correctly parsed (gene, transcript, exon features)
- Canonical transcript selection follows priority rules
- MANE summary file produces correct Ensembl→RefSeq mapping
- Cross-referencing attaches RefSeq IDs to canonical transcripts
- Output schema matches the expected annotation format
- fetch_batch returns correct annotations via dict lookup
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.pipeline.sources.annotations.ensembl import (
    EnsemblAnnotationSource,
    _parse_gtf_attributes,
)

# ---------------------------------------------------------------------------
# Sample GTF content (minimal, matches real Ensembl GTF format)
# ---------------------------------------------------------------------------

SAMPLE_GTF = """\
#!genome-build GRCh38.p14
#!genome-version GRCh38
16\tensembl_havana\tgene\t2088708\t2135898\t.\t+\t.\tgene_id "ENSG00000008710"; gene_version "20"; gene_name "PKD1"; gene_source "ensembl_havana"; gene_biotype "protein_coding";
16\tensembl_havana\ttranscript\t2088708\t2135898\t.\t+\t.\tgene_id "ENSG00000008710"; gene_version "20"; transcript_id "ENST00000262304"; transcript_version "10"; gene_name "PKD1"; gene_source "ensembl_havana"; gene_biotype "protein_coding"; transcript_name "PKD1-201"; transcript_source "ensembl_havana"; transcript_biotype "protein_coding"; tag "MANE_Select"; tag "Ensembl_canonical";
16\tensembl_havana\texon\t2088708\t2089100\t.\t+\t.\tgene_id "ENSG00000008710"; transcript_id "ENST00000262304"; exon_number "1"; exon_id "ENSE00001184675";
16\tensembl_havana\texon\t2090000\t2090500\t.\t+\t.\tgene_id "ENSG00000008710"; transcript_id "ENST00000262304"; exon_number "2"; exon_id "ENSE00001184676";
16\tensembl_havana\ttranscript\t2088800\t2135000\t.\t+\t.\tgene_id "ENSG00000008710"; gene_version "20"; transcript_id "ENST00000999999"; transcript_version "1"; gene_name "PKD1"; gene_source "ensembl_havana"; gene_biotype "protein_coding"; transcript_name "PKD1-202"; transcript_source "ensembl_havana"; transcript_biotype "protein_coding";
16\tensembl_havana\texon\t2088800\t2089050\t.\t+\t.\tgene_id "ENSG00000008710"; transcript_id "ENST00000999999"; exon_number "1"; exon_id "ENSE00009999991";
4\tensembl_havana\tgene\t88007663\t88077654\t.\t+\t.\tgene_id "ENSG00000118762"; gene_version "7"; gene_name "PKD2"; gene_source "ensembl_havana"; gene_biotype "protein_coding";
4\tensembl_havana\ttranscript\t88007663\t88077654\t.\t+\t.\tgene_id "ENSG00000118762"; gene_version "7"; transcript_id "ENST00000237596"; transcript_version "4"; gene_name "PKD2"; gene_source "ensembl_havana"; gene_biotype "protein_coding"; transcript_name "PKD2-201"; transcript_source "ensembl_havana"; transcript_biotype "protein_coding"; tag "Ensembl_canonical";
4\tensembl_havana\texon\t88007663\t88008000\t.\t+\t.\tgene_id "ENSG00000118762"; transcript_id "ENST00000237596"; exon_number "1"; exon_id "ENSE00002378001";
17\tensembl_havana\tgene\t7661779\t7687538\t.\t-\t.\tgene_id "ENSG00000141510"; gene_version "20"; gene_name "TP53"; gene_source "ensembl_havana"; gene_biotype "protein_coding";
17\tensembl_havana\ttranscript\t7661779\t7687538\t.\t-\t.\tgene_id "ENSG00000141510"; gene_version "20"; transcript_id "ENST00000269305"; transcript_version "9"; gene_name "TP53"; gene_source "ensembl_havana"; gene_biotype "protein_coding"; transcript_name "TP53-201"; transcript_source "ensembl_havana"; transcript_biotype "protein_coding"; tag "MANE_Select";
17\tensembl_havana\texon\t7687377\t7687538\t.\t-\t.\tgene_id "ENSG00000141510"; transcript_id "ENST00000269305"; exon_number "1"; exon_id "ENSE00003723991";
17\tensembl_havana\texon\t7676594\t7676622\t.\t-\t.\tgene_id "ENSG00000141510"; transcript_id "ENST00000269305"; exon_number "2"; exon_id "ENSE00003725258";
"""

# ---------------------------------------------------------------------------
# Sample MANE summary TSV content
# ---------------------------------------------------------------------------

SAMPLE_MANE_HEADER = (
    "#NCBI_GeneID\tEnsembl_Gene\tHGNC_ID\tsymbol\tname\t"
    "RefSeq_nuc\tRefSeq_prot\tEnsembl_nuc\tEnsembl_prot\t"
    "MANE_status\tGRCh38_chr\tchr_start\tchr_end\tchr_strand\n"
)

SAMPLE_MANE_ROWS = """\
GeneID:5310\tENSG00000008710.20\tHGNC:9008\tPKD1\tpolycystin 1\tNM_001009944.3\tNP_001009944.1\tENST00000262304.10\tENSP00000262304.5\tMANE Select\tNC_000016.10\t2088708\t2135898\t+
GeneID:5311\tENSG00000118762.7\tHGNC:9009\tPKD2\tpolycystin 2\tNM_000297.4\tNP_000288.1\tENST00000237596.4\tENSP00000237596.3\tMANE Select\tNC_000004.12\t88007663\t88077654\t+
GeneID:7157\tENSG00000141510.20\tHGNC:11998\tTP53\ttumor protein p53\tNM_000546.6\tNP_000537.3\tENST00000269305.9\tENSP00000269305.4\tMANE Select\tNC_000017.11\t7661779\t7687538\t-
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_gtf_file(tmp_path: Path, content: str | None = None) -> Path:
    """Create a temporary GTF file."""
    if content is None:
        content = SAMPLE_GTF
    gtf_file = tmp_path / "ensembl.gtf"
    gtf_file.write_text(content)
    return gtf_file


def _create_mane_file(tmp_path: Path, content: str | None = None) -> Path:
    """Create a temporary MANE summary TSV file."""
    if content is None:
        content = SAMPLE_MANE_HEADER + SAMPLE_MANE_ROWS
    mane_file = tmp_path / "MANE.GRCh38.summary.txt"
    mane_file.write_text(content)
    return mane_file


def _make_source() -> EnsemblAnnotationSource:
    """Create an EnsemblAnnotationSource without __init__ (no DB needed)."""
    src = EnsemblAnnotationSource.__new__(EnsemblAnnotationSource)
    src._bulk_data = None
    src._mane_data = None
    return src


def _make_gene(gene_id: int = 1, symbol: str = "PKD1") -> MagicMock:
    """Create a mock Gene object."""
    gene = MagicMock(spec=["id", "approved_symbol"])
    gene.id = gene_id
    gene.approved_symbol = symbol
    return gene


# ===========================================================================
# Tests: GTF attribute parsing
# ===========================================================================


@pytest.mark.unit
class TestGTFAttributeParsing:
    """Test the GTF attribute line parser."""

    def test_basic_attributes(self) -> None:
        """Parse simple key-value attributes."""
        attr_str = 'gene_id "ENSG00000008710"; gene_name "PKD1";'
        attrs, tags = _parse_gtf_attributes(attr_str)

        assert attrs["gene_id"] == "ENSG00000008710"
        assert attrs["gene_name"] == "PKD1"
        assert len(tags) == 0

    def test_tags_collected_into_set(self) -> None:
        """Multiple tag keys are collected into a set."""
        attr_str = 'transcript_id "ENST00000262304"; tag "MANE_Select"; tag "Ensembl_canonical";'
        attrs, tags = _parse_gtf_attributes(attr_str)

        assert attrs["transcript_id"] == "ENST00000262304"
        assert "MANE_Select" in tags
        assert "Ensembl_canonical" in tags

    def test_empty_string(self) -> None:
        """Empty attribute string returns empty results."""
        attrs, tags = _parse_gtf_attributes("")
        assert attrs == {}
        assert tags == set()

    def test_single_attribute(self) -> None:
        """Single attribute without trailing semicolon."""
        attrs, tags = _parse_gtf_attributes('gene_id "ENSG00000008710"')
        assert attrs["gene_id"] == "ENSG00000008710"


# ===========================================================================
# Tests: GTF file parsing
# ===========================================================================


@pytest.mark.unit
class TestGTFParsing:
    """Test GTF file parsing into gene annotation dict."""

    def test_parse_extracts_genes(self, tmp_path: Path) -> None:
        """Parse GTF extracts all genes."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)

        assert "PKD1" in data
        assert "PKD2" in data
        assert "TP53" in data

    def test_parse_gene_coordinates(self, tmp_path: Path) -> None:
        """Gene coordinates are correctly parsed."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)
        pkd1 = data["PKD1"]

        assert pkd1["chromosome"] == "16"
        assert pkd1["start"] == 2088708
        assert pkd1["end"] == 2135898
        assert pkd1["strand"] == "+"
        assert pkd1["gene_id"] == "ENSG00000008710"
        assert pkd1["biotype"] == "protein_coding"

    def test_parse_negative_strand(self, tmp_path: Path) -> None:
        """Negative strand genes have '-' strand."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)

        assert data["TP53"]["strand"] == "-"

    def test_parse_gene_length(self, tmp_path: Path) -> None:
        """Gene length is end - start + 1."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)

        assert data["PKD1"]["gene_length"] == 2135898 - 2088708 + 1

    def test_parse_assembly(self, tmp_path: Path) -> None:
        """Assembly is always GRCh38."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)

        assert data["PKD1"]["assembly"] == "GRCh38"

    def test_parse_canonical_transcript_mane_select(self, tmp_path: Path) -> None:
        """MANE_Select transcript is chosen as canonical."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)
        pkd1 = data["PKD1"]

        # PKD1 has MANE_Select on ENST00000262304
        assert pkd1["canonical_transcript"]["transcript_id"] == "ENST00000262304"

    def test_parse_exons(self, tmp_path: Path) -> None:
        """Exons are correctly parsed and numbered."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)
        exons = data["PKD1"]["canonical_transcript"]["exons"]

        assert len(exons) == 2
        assert exons[0]["exon_number"] == 1
        assert exons[0]["start"] == 2088708
        assert exons[0]["end"] == 2089100
        assert exons[0]["length"] == 2089100 - 2088708 + 1
        assert exons[1]["exon_number"] == 2

    def test_parse_exon_count(self, tmp_path: Path) -> None:
        """exon_count matches number of exons."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)

        assert data["PKD1"]["exon_count"] == 2
        assert data["PKD1"]["canonical_transcript"]["exon_count"] == 2

    def test_parse_transcript_count(self, tmp_path: Path) -> None:
        """transcript_count includes all transcripts for the gene."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)

        # PKD1 has 2 transcripts in sample
        assert data["PKD1"]["transcript_count"] == 2
        # PKD2 has 1
        assert data["PKD2"]["transcript_count"] == 1

    def test_parse_output_schema(self, tmp_path: Path) -> None:
        """Output annotation has all required fields."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)
        pkd1 = data["PKD1"]

        # Top-level fields
        required_fields = [
            "gene_id",
            "gene_symbol",
            "display_name",
            "description",
            "biotype",
            "chromosome",
            "start",
            "end",
            "strand",
            "gene_length",
            "assembly",
            "canonical_transcript",
            "transcript_count",
            "exon_count",
            "last_updated",
        ]
        for field in required_fields:
            assert field in pkd1, f"Missing field: {field}"

        # Canonical transcript fields
        ct = pkd1["canonical_transcript"]
        ct_fields = [
            "transcript_id",
            "display_name",
            "biotype",
            "is_canonical",
            "start",
            "end",
            "exon_count",
            "exons",
            "refseq_transcript_id",
        ]
        for field in ct_fields:
            assert field in ct, f"Missing canonical_transcript field: {field}"

    def test_parse_skips_comment_lines(self, tmp_path: Path) -> None:
        """Lines starting with # are skipped."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)

        # Should not crash, and should produce valid results
        assert len(data) > 0

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Empty GTF file returns empty dict."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path, content="# header only\n")

        data = source.parse_bulk_file(gtf_file)

        assert data == {}

    def test_parse_description_is_none(self, tmp_path: Path) -> None:
        """Description is None (not in GTF)."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)

        data = source.parse_bulk_file(gtf_file)

        assert data["PKD1"]["description"] is None


# ===========================================================================
# Tests: Canonical transcript selection
# ===========================================================================


@pytest.mark.unit
class TestCanonicalTranscriptSelection:
    """Test _select_canonical_transcript priority logic."""

    def test_mane_select_preferred(self) -> None:
        """MANE_Select transcript wins over Ensembl_canonical."""
        transcripts = {
            "TX1": {
                "is_mane_select": False,
                "is_canonical": True,
                "biotype": "protein_coding",
                "length": 5000,
            },
            "TX2": {
                "is_mane_select": True,
                "is_canonical": False,
                "biotype": "protein_coding",
                "length": 3000,
            },
        }

        result = EnsemblAnnotationSource._select_canonical_transcript(["TX1", "TX2"], transcripts)

        assert result == "TX2"

    def test_ensembl_canonical_second(self) -> None:
        """Ensembl_canonical wins when no MANE_Select."""
        transcripts = {
            "TX1": {
                "is_mane_select": False,
                "is_canonical": True,
                "biotype": "protein_coding",
                "length": 3000,
            },
            "TX2": {
                "is_mane_select": False,
                "is_canonical": False,
                "biotype": "protein_coding",
                "length": 5000,
            },
        }

        result = EnsemblAnnotationSource._select_canonical_transcript(["TX1", "TX2"], transcripts)

        assert result == "TX1"

    def test_longest_protein_coding_third(self) -> None:
        """Longest protein-coding wins when no tagged transcript."""
        transcripts = {
            "TX1": {
                "is_mane_select": False,
                "is_canonical": False,
                "biotype": "protein_coding",
                "length": 3000,
            },
            "TX2": {
                "is_mane_select": False,
                "is_canonical": False,
                "biotype": "protein_coding",
                "length": 5000,
            },
            "TX3": {
                "is_mane_select": False,
                "is_canonical": False,
                "biotype": "lncRNA",
                "length": 9000,
            },
        }

        result = EnsemblAnnotationSource._select_canonical_transcript(
            ["TX1", "TX2", "TX3"], transcripts
        )

        assert result == "TX2"

    def test_fallback_to_first(self) -> None:
        """Falls back to first transcript when nothing else matches."""
        transcripts = {
            "TX1": {
                "is_mane_select": False,
                "is_canonical": False,
                "biotype": "lncRNA",
                "length": 3000,
            },
            "TX2": {
                "is_mane_select": False,
                "is_canonical": False,
                "biotype": "lncRNA",
                "length": 5000,
            },
        }

        result = EnsemblAnnotationSource._select_canonical_transcript(["TX1", "TX2"], transcripts)

        assert result == "TX1"

    def test_empty_list(self) -> None:
        """Empty transcript list returns None."""
        result = EnsemblAnnotationSource._select_canonical_transcript([], {})

        assert result is None


# ===========================================================================
# Tests: MANE parsing
# ===========================================================================


@pytest.mark.unit
class TestMANEParsing:
    """Test MANE summary file parsing."""

    def test_parse_extracts_transcript_mapping(self, tmp_path: Path) -> None:
        """Parse MANE file maps unversioned ENST → RefSeq NM."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_mane_file(mane_file)

        assert "ENST00000262304" in data
        assert data["ENST00000262304"]["refseq_nuc"] == "NM_001009944.3"

    def test_parse_strips_version_from_enst_key(self, tmp_path: Path) -> None:
        """Keys are unversioned ENST IDs (no .10 suffix)."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_mane_file(mane_file)

        assert "ENST00000262304.10" not in data
        assert "ENST00000262304" in data

    def test_parse_includes_symbol(self, tmp_path: Path) -> None:
        """Parsed entries include gene symbol."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_mane_file(mane_file)

        assert data["ENST00000262304"]["symbol"] == "PKD1"
        assert data["ENST00000237596"]["symbol"] == "PKD2"

    def test_parse_includes_mane_status(self, tmp_path: Path) -> None:
        """Parsed entries include MANE status."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_mane_file(mane_file)

        assert data["ENST00000262304"]["mane_status"] == "MANE Select"

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Empty file (header only) returns empty dict."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path, content=SAMPLE_MANE_HEADER)

        data = source.parse_mane_file(mane_file)

        assert data == {}

    def test_parse_total_count(self, tmp_path: Path) -> None:
        """Sample data produces expected number of entries."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_mane_file(mane_file)

        assert len(data) == 3


# ===========================================================================
# Tests: Cross-referencing GTF with MANE
# ===========================================================================


@pytest.mark.unit
class TestCrossReference:
    """Test cross-referencing GTF data with MANE for RefSeq IDs."""

    def test_refseq_attached_to_canonical(self, tmp_path: Path) -> None:
        """After cross-referencing, canonical transcript has refseq_transcript_id."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)
        mane_file = _create_mane_file(tmp_path)

        source._bulk_data = source.parse_bulk_file(gtf_file)
        source._mane_data = source.parse_mane_file(mane_file)

        # Manually cross-reference (same logic as ensure_bulk_data_loaded)
        for _symbol, annotation in source._bulk_data.items():
            canonical = annotation.get("canonical_transcript")
            if not canonical:
                continue
            transcript_id = canonical.get("transcript_id", "")
            enst_unversioned = transcript_id.split(".")[0]
            mane_entry = source._mane_data.get(enst_unversioned)
            if mane_entry:
                canonical["refseq_transcript_id"] = mane_entry["refseq_nuc"]

        pkd1 = source._bulk_data["PKD1"]
        assert pkd1["canonical_transcript"]["refseq_transcript_id"] == "NM_001009944.3"

    def test_refseq_none_when_not_in_mane(self, tmp_path: Path) -> None:
        """Genes not in MANE keep refseq_transcript_id as None."""
        source = _make_source()
        # GTF with a gene not in MANE
        gtf_content = (
            "1\tensembl\tgene\t100\t200\t.\t+\t.\t"
            'gene_id "ENSG99999"; gene_name "FAKEGENE"; gene_biotype "protein_coding";\n'
            "1\tensembl\ttranscript\t100\t200\t.\t+\t.\t"
            'gene_id "ENSG99999"; transcript_id "ENST88888"; gene_name "FAKEGENE"; '
            'transcript_name "FAKE-201"; transcript_biotype "protein_coding"; tag "Ensembl_canonical";\n'
            "1\tensembl\texon\t100\t200\t.\t+\t.\t"
            'gene_id "ENSG99999"; transcript_id "ENST88888"; exon_number "1"; exon_id "ENSE88888";\n'
        )
        gtf_file = _create_gtf_file(tmp_path, content=gtf_content)
        mane_file = _create_mane_file(tmp_path)  # Does not contain FAKEGENE

        source._bulk_data = source.parse_bulk_file(gtf_file)
        source._mane_data = source.parse_mane_file(mane_file)

        # Cross-reference
        for _symbol, annotation in source._bulk_data.items():
            canonical = annotation.get("canonical_transcript")
            if not canonical:
                continue
            transcript_id = canonical.get("transcript_id", "")
            enst_unversioned = transcript_id.split(".")[0]
            mane_entry = source._mane_data.get(enst_unversioned)
            if mane_entry:
                canonical["refseq_transcript_id"] = mane_entry["refseq_nuc"]

        assert source._bulk_data["FAKEGENE"]["canonical_transcript"]["refseq_transcript_id"] is None


# ===========================================================================
# Tests: fetch_batch and fetch_annotation
# ===========================================================================


@pytest.mark.unit
class TestFetchBatch:
    """Test fetch_batch returns annotations via dict lookup."""

    @pytest.mark.asyncio
    async def test_fetch_batch_returns_results(self, tmp_path: Path) -> None:
        """fetch_batch returns annotations for known genes."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)
        source._bulk_data = source.parse_bulk_file(gtf_file)
        source._mane_data = {}  # No MANE data needed for this test
        source.ensure_bulk_data_loaded = AsyncMock()

        genes = [_make_gene(1, "PKD1"), _make_gene(2, "PKD2")]
        results = await source.fetch_batch(genes)

        assert 1 in results
        assert 2 in results
        assert results[1]["gene_symbol"] == "PKD1"
        assert results[2]["gene_symbol"] == "PKD2"

    @pytest.mark.asyncio
    async def test_fetch_batch_skips_unknown_genes(self, tmp_path: Path) -> None:
        """fetch_batch skips genes not in GTF."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)
        source._bulk_data = source.parse_bulk_file(gtf_file)
        source._mane_data = {}
        source.ensure_bulk_data_loaded = AsyncMock()

        genes = [_make_gene(1, "PKD1"), _make_gene(99, "NONEXISTENT")]
        results = await source.fetch_batch(genes)

        assert 1 in results
        assert 99 not in results

    @pytest.mark.asyncio
    async def test_fetch_batch_empty_list(self) -> None:
        """fetch_batch with empty list returns empty dict."""
        source = _make_source()
        results = await source.fetch_batch([])

        assert results == {}

    @pytest.mark.asyncio
    async def test_fetch_annotation_returns_gene(self, tmp_path: Path) -> None:
        """fetch_annotation returns annotation for a known gene."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)
        source._bulk_data = source.parse_bulk_file(gtf_file)
        source._mane_data = {}
        source.ensure_bulk_data_loaded = AsyncMock()

        gene = _make_gene(1, "PKD1")
        result = await source.fetch_annotation(gene)

        assert result is not None
        assert result["gene_symbol"] == "PKD1"
        assert result["gene_id"] == "ENSG00000008710"

    @pytest.mark.asyncio
    async def test_fetch_annotation_returns_none_for_unknown(self, tmp_path: Path) -> None:
        """fetch_annotation returns None for unknown gene."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)
        source._bulk_data = source.parse_bulk_file(gtf_file)
        source._mane_data = {}
        source.ensure_bulk_data_loaded = AsyncMock()

        gene = _make_gene(99, "NONEXISTENT")
        result = await source.fetch_annotation(gene)

        assert result is None


# ===========================================================================
# Tests: Bulk file attributes
# ===========================================================================


@pytest.mark.unit
class TestBulkFileAttributes:
    """Test that bulk file class attributes are properly set."""

    def test_bulk_file_url_is_gtf(self) -> None:
        """EnsemblAnnotationSource has GTF bulk_file_url."""
        source = _make_source()

        assert "gtf" in source.bulk_file_url.lower()
        assert source.bulk_file_url.endswith(".gtf.gz")

    def test_mane_file_url_set(self) -> None:
        """EnsemblAnnotationSource has MANE mane_file_url."""
        source = _make_source()

        assert "MANE" in source.mane_file_url

    def test_bulk_cache_ttl(self) -> None:
        """Cache TTL is 7 days (168 hours)."""
        source = _make_source()

        assert source.bulk_cache_ttl_hours == 168

    def test_bulk_file_format(self) -> None:
        """File format is gtf.gz."""
        source = _make_source()

        assert source.bulk_file_format == "gtf.gz"

    def test_min_size_bytes(self) -> None:
        """Minimum file size guard is set."""
        source = _make_source()

        assert source.bulk_file_min_size_bytes >= 80_000_000


# ===========================================================================
# Tests: Validation
# ===========================================================================


@pytest.mark.unit
class TestValidation:
    """Test _is_valid_annotation."""

    def test_valid_annotation(self, tmp_path: Path) -> None:
        """Valid annotation with exons passes validation."""
        source = _make_source()
        gtf_file = _create_gtf_file(tmp_path)
        data = source.parse_bulk_file(gtf_file)

        assert source._is_valid_annotation(data["PKD1"]) is True

    def test_invalid_without_gene_id(self) -> None:
        """Annotation without gene_id fails validation."""
        source = _make_source()
        annotation: dict[str, Any] = {"gene_symbol": "PKD1"}

        assert source._is_valid_annotation(annotation) is False

    def test_invalid_without_exons(self) -> None:
        """Annotation with zero exons fails validation."""
        source = _make_source()
        annotation: dict[str, Any] = {
            "gene_id": "ENSG00000008710",
            "gene_symbol": "PKD1",
            "canonical_transcript": {"exon_count": 0},
        }

        assert source._is_valid_annotation(annotation) is False


# ===========================================================================
# Tests: ensure_bulk_data_loaded integration
# ===========================================================================


@pytest.mark.unit
class TestEnsureBulkDataLoaded:
    """Test ensure_bulk_data_loaded with pre-created files."""

    @pytest.mark.asyncio
    async def test_skips_if_loaded(self) -> None:
        """Does not re-parse if data already populated."""
        source = _make_source()
        source._bulk_data = {"PKD1": {"gene_id": "ENSG00000008710"}}
        source._mane_data = {"ENST00000262304": {"refseq_nuc": "NM_001009944.3"}}

        await source.ensure_bulk_data_loaded()

        # Data unchanged
        assert "PKD1" in source._bulk_data
        assert "ENST00000262304" in source._mane_data
