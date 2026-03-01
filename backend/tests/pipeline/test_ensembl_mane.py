"""
Tests for Ensembl MANE bulk file integration.

Verifies that the MANE summary file is correctly parsed into an
Ensembl→RefSeq transcript mapping and that _resolve_refseq_id uses
MANE lookups before falling back to the Ensembl xrefs API.
"""

import gzip
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.pipeline.sources.annotations.ensembl import EnsemblAnnotationSource

# Sample MANE summary TSV content (matches real file format)
SAMPLE_HEADER = (
    "#NCBI_GeneID\tEnsembl_Gene\tHGNC_ID\tsymbol\tname\t"
    "RefSeq_nuc\tRefSeq_prot\tEnsembl_nuc\tEnsembl_prot\t"
    "MANE_status\tGRCh38_chr\tchr_start\tchr_end\tchr_strand\n"
)

SAMPLE_ROWS = """\
GeneID:5310\tENSG00000008710.20\tHGNC:9008\tPKD1\tpolycystin 1\tNM_001009944.3\tNP_001009944.1\tENST00000262304.10\tENSP00000262304.5\tMANE Select\tNC_000016.10\t2088708\t2135898\t+
GeneID:5311\tENSG00000118762.7\tHGNC:9009\tPKD2\tpolycystin 2\tNM_000297.4\tNP_000288.1\tENST00000237596.4\tENSP00000237596.3\tMANE Select\tNC_000004.12\t88007663\t88077654\t+
GeneID:7157\tENSG00000141510.20\tHGNC:11998\tTP53\ttumor protein p53\tNM_000546.6\tNP_000537.3\tENST00000269305.9\tENSP00000269305.4\tMANE Select\tNC_000017.11\t7661779\t7687538\t-
GeneID:7157\tENSG00000141510.20\tHGNC:11998\tTP53\ttumor protein p53\tNM_001276760.3\tNP_001263689.1\tENST00000610292.4\tENSP00000478219.1\tMANE Plus Clinical\tNC_000017.11\t7661779\t7687538\t-
"""


def _create_mane_file(tmp_path: Path, content: str | None = None) -> Path:
    """Create a temporary MANE summary TSV file."""
    if content is None:
        content = SAMPLE_HEADER + SAMPLE_ROWS
    mane_file = tmp_path / "MANE.GRCh38.summary.txt"
    mane_file.write_text(content)
    return mane_file


def _make_source() -> EnsemblAnnotationSource:
    """Create an EnsemblAnnotationSource without __init__ (no DB needed)."""
    return EnsemblAnnotationSource.__new__(EnsemblAnnotationSource)


@pytest.mark.unit
class TestMANEParsing:
    """Test MANE summary file parsing."""

    def test_parse_extracts_transcript_mapping(self, tmp_path: Path) -> None:
        """Parse MANE file maps unversioned ENST → RefSeq NM."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_bulk_file(mane_file)

        assert "ENST00000262304" in data
        assert data["ENST00000262304"]["refseq_nuc"] == "NM_001009944.3"

    def test_parse_strips_version_from_enst_key(self, tmp_path: Path) -> None:
        """Keys are unversioned ENST IDs (no .10 suffix)."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_bulk_file(mane_file)

        # Versioned key should NOT exist
        assert "ENST00000262304.10" not in data
        # Unversioned key should exist
        assert "ENST00000262304" in data

    def test_parse_includes_symbol(self, tmp_path: Path) -> None:
        """Parsed entries include gene symbol."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_bulk_file(mane_file)

        assert data["ENST00000262304"]["symbol"] == "PKD1"
        assert data["ENST00000237596"]["symbol"] == "PKD2"

    def test_parse_includes_mane_status(self, tmp_path: Path) -> None:
        """Parsed entries include MANE status."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_bulk_file(mane_file)

        assert data["ENST00000262304"]["mane_status"] == "MANE Select"
        assert data["ENST00000610292"]["mane_status"] == "MANE Plus Clinical"

    def test_parse_includes_versioned_enst(self, tmp_path: Path) -> None:
        """Parsed entries store the original versioned ENST ID."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_bulk_file(mane_file)

        assert data["ENST00000262304"]["ensembl_nuc_versioned"] == "ENST00000262304.10"

    def test_parse_multiple_transcripts_same_gene(self, tmp_path: Path) -> None:
        """TP53 has both MANE Select and MANE Plus Clinical transcripts."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_bulk_file(mane_file)

        # Both transcripts should be indexed separately
        assert "ENST00000269305" in data
        assert data["ENST00000269305"]["refseq_nuc"] == "NM_000546.6"
        assert "ENST00000610292" in data
        assert data["ENST00000610292"]["refseq_nuc"] == "NM_001276760.3"

    def test_parse_skips_header_lines(self, tmp_path: Path) -> None:
        """Lines starting with # are skipped."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_bulk_file(mane_file)

        # Should not contain header fields as keys
        assert "#NCBI_GeneID" not in data

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Empty file (header only) returns empty dict."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path, content=SAMPLE_HEADER)

        data = source.parse_bulk_file(mane_file)

        assert data == {}

    def test_parse_total_count(self, tmp_path: Path) -> None:
        """Sample data produces expected number of entries."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)

        data = source.parse_bulk_file(mane_file)

        # 4 rows → 4 unique ENST IDs
        assert len(data) == 4


@pytest.mark.unit
class TestMANELookup:
    """Test MANE-based RefSeq ID lookup."""

    def test_lookup_hit(self, tmp_path: Path) -> None:
        """lookup_gene returns MANE entry for known ENST."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)
        source._bulk_data = source.parse_bulk_file(mane_file)

        result = source.lookup_gene("ENST00000262304")

        assert result is not None
        assert result["refseq_nuc"] == "NM_001009944.3"

    def test_lookup_miss(self, tmp_path: Path) -> None:
        """lookup_gene returns None for unknown ENST."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)
        source._bulk_data = source.parse_bulk_file(mane_file)

        result = source.lookup_gene("ENST99999999999")

        assert result is None

    def test_lookup_not_loaded(self) -> None:
        """lookup_gene returns None when bulk data not loaded."""
        source = _make_source()
        source._bulk_data = None

        result = source.lookup_gene("ENST00000262304")

        assert result is None


@pytest.mark.unit
class TestResolveRefSeqId:
    """Test _resolve_refseq_id with MANE + API fallback."""

    @pytest.mark.asyncio
    async def test_resolve_uses_mane_when_available(self, tmp_path: Path) -> None:
        """MANE hit returns RefSeq without calling xrefs API."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)
        source._bulk_data = source.parse_bulk_file(mane_file)

        # Mock _fetch_refseq_id to ensure it's NOT called
        source._fetch_refseq_id = AsyncMock(return_value="NM_SHOULD_NOT_USE.1")

        result = await source._resolve_refseq_id("ENST00000262304")

        assert result == "NM_001009944.3"
        source._fetch_refseq_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_resolve_strips_version_for_lookup(self, tmp_path: Path) -> None:
        """Versioned ENST IDs have version stripped for MANE lookup."""
        source = _make_source()
        mane_file = _create_mane_file(tmp_path)
        source._bulk_data = source.parse_bulk_file(mane_file)

        # Pass versioned ID — should still match
        result = await source._resolve_refseq_id("ENST00000262304.10")

        assert result == "NM_001009944.3"

    @pytest.mark.asyncio
    async def test_resolve_falls_back_to_api(self) -> None:
        """When MANE miss, falls back to xrefs API."""
        source = _make_source()
        source._bulk_data = {}  # Empty MANE data

        source._fetch_refseq_id = AsyncMock(return_value="NM_999999.1")

        result = await source._resolve_refseq_id("ENST00000999999")

        assert result == "NM_999999.1"
        source._fetch_refseq_id.assert_called_once_with("ENST00000999999")

    @pytest.mark.asyncio
    async def test_resolve_returns_none_for_empty_id(self) -> None:
        """Empty transcript_id returns None without lookup."""
        source = _make_source()
        source._bulk_data = {}

        result = await source._resolve_refseq_id("")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_returns_none_when_both_miss(self) -> None:
        """None returned when both MANE and API miss."""
        source = _make_source()
        source._bulk_data = {}

        source._fetch_refseq_id = AsyncMock(return_value=None)

        result = await source._resolve_refseq_id("ENST00000999999")

        assert result is None


@pytest.mark.unit
class TestBulkFileAttributes:
    """Test that bulk file class attributes are properly set."""

    def test_bulk_file_url_set(self) -> None:
        """EnsemblAnnotationSource has MANE bulk_file_url."""
        source = _make_source()

        assert "MANE" in source.bulk_file_url
        assert source.bulk_file_url.endswith(".txt.gz")

    def test_bulk_cache_ttl(self) -> None:
        """Cache TTL is 7 days (168 hours)."""
        source = _make_source()

        assert source.bulk_cache_ttl_hours == 168

    def test_bulk_file_format(self) -> None:
        """File format is txt.gz."""
        source = _make_source()

        assert source.bulk_file_format == "txt.gz"


@pytest.mark.unit
class TestEnsemblParseGeneData:
    """Test _parse_gene_data produces expected annotation structure."""

    def test_parse_gene_data_basic(self) -> None:
        """Parsed annotation has expected fields."""
        source = _make_source()

        data = {
            "id": "ENSG00000008710",
            "display_name": "PKD1",
            "description": "polycystin 1",
            "biotype": "protein_coding",
            "seq_region_name": "16",
            "start": 2088708,
            "end": 2135898,
            "strand": 1,
            "assembly_name": "GRCh38",
            "Transcript": [
                {
                    "id": "ENST00000262304",
                    "display_name": "PKD1-201",
                    "biotype": "protein_coding",
                    "is_canonical": True,
                    "start": 2088708,
                    "end": 2135898,
                    "Exon": [
                        {
                            "id": "ENSE00001184675",
                            "start": 2088708,
                            "end": 2089100,
                            "phase": -1,
                            "end_phase": -1,
                        }
                    ],
                }
            ],
        }

        annotation = source._parse_gene_data("PKD1", data)

        assert annotation is not None
        assert annotation["gene_id"] == "ENSG00000008710"
        assert annotation["gene_symbol"] == "PKD1"
        assert annotation["chromosome"] == "16"
        assert annotation["strand"] == "+"
        assert annotation["canonical_transcript"]["transcript_id"] == "ENST00000262304"
        assert annotation["exon_count"] == 1

    def test_parse_gene_data_returns_none_for_empty(self) -> None:
        """Empty data returns None."""
        source = _make_source()

        assert source._parse_gene_data("PKD1", {}) is None

    def test_parse_gene_data_returns_none_for_no_transcript(self) -> None:
        """Data with no transcripts returns None."""
        source = _make_source()

        data = {
            "id": "ENSG00000008710",
            "display_name": "PKD1",
            "biotype": "protein_coding",
            "Transcript": [],
        }

        assert source._parse_gene_data("PKD1", data) is None


@pytest.mark.unit
class TestEnsembleEnsureBulkDataLoaded:
    """Test ensure_bulk_data_loaded integration with MANE file."""

    @pytest.mark.asyncio
    async def test_ensure_bulk_data_loaded_populates_data(self, tmp_path: Path) -> None:
        """After loading, _bulk_data contains MANE entries."""
        source = _make_source()
        source.bulk_cache_dir = tmp_path
        source._bulk_data = None

        # Pre-create the cache file as gzip (bulk_file_format is "txt.gz")
        mane_content = (SAMPLE_HEADER + SAMPLE_ROWS).encode()
        cache_path = source._bulk_cache_path()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(cache_path, "wb") as gz:
            gz.write(mane_content)

        await source.ensure_bulk_data_loaded()

        assert source._bulk_data is not None
        assert "ENST00000262304" in source._bulk_data

    @pytest.mark.asyncio
    async def test_ensure_bulk_data_loaded_skips_if_loaded(self) -> None:
        """Does not re-parse if _bulk_data already populated."""
        source = _make_source()
        source._bulk_data = {"ENST00000262304": {"refseq_nuc": "NM_001009944.3"}}

        # Should return immediately without downloading
        await source.ensure_bulk_data_loaded()

        assert source._bulk_data == {"ENST00000262304": {"refseq_nuc": "NM_001009944.3"}}
