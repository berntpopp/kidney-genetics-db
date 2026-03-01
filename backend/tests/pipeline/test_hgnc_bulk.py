"""
Tests for HGNC bulk JSON parsing in HGNCAnnotationSource.

Verifies that the bulk complete set JSON is correctly parsed and
produces annotation dicts with the same field names as the REST API path.
"""

import json
from pathlib import Path

import pytest

# Minimal HGNC complete set JSON fixture
SAMPLE_HGNC_JSON = {
    "responseHeader": {"QTime": 23, "status": 0},
    "response": {
        "numFound": 3,
        "docs": [
            {
                "hgnc_id": "HGNC:9008",
                "symbol": "PKD1",
                "name": "polycystin 1, transient receptor potential channel interacting",
                "status": "Approved",
                "entrez_id": "5310",
                "ensembl_gene_id": "ENSG00000008710",
                "omim_id": ["601313"],
                "orphanet": 12345,
                "cosmic": "PKD1",
                "refseq_accession": ["NM_001009944.3"],
                "mane_select": ["ENST00000262304.10", "NM_001009944.3"],
                "locus_type": "gene with protein product",
                "locus_group": "protein-coding gene",
                "location": "16p13.3",
                "location_sortable": "16p13.3",
                "alias_symbol": ["PBD"],
                "alias_name": [],
                "prev_symbol": [],
                "prev_name": [],
                "gene_family": ["Polycystins"],
                "gene_family_id": [1234],
                "pubmed_id": [8889548],
                "date_approved_reserved": "1994-06-30",
                "date_modified": "2024-01-15",
                "uuid": "abc-123",
                "_version_": 100,
            },
            {
                "hgnc_id": "HGNC:9009",
                "symbol": "PKD2",
                "name": "polycystin 2, transient receptor potential cation channel",
                "status": "Approved",
                "entrez_id": "5311",
                "ensembl_gene_id": "ENSG00000118762",
                "locus_type": "gene with protein product",
                "locus_group": "protein-coding gene",
                "location": "4q22.1",
            },
            {
                # Withdrawn gene — should still be parsed
                "hgnc_id": "HGNC:99999",
                "symbol": "WITHDRAWN1",
                "name": "withdrawn symbol",
                "status": "Entry Withdrawn",
            },
        ],
    },
}


def _create_json(tmp_path: Path) -> Path:
    """Write sample HGNC JSON to a temp file."""
    json_file = tmp_path / "hgnc_complete_set.json"
    json_file.write_text(json.dumps(SAMPLE_HGNC_JSON))
    return json_file


@pytest.mark.unit
class TestHGNCBulkParsing:
    """Test JSON parsing extracts correct fields."""

    def test_parse_extracts_core_identifiers(self, tmp_path: Path) -> None:
        """Parse HGNC JSON extracts hgnc_id, symbol, ensembl_gene_id."""
        from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource

        json_file = _create_json(tmp_path)

        source = HGNCAnnotationSource.__new__(HGNCAnnotationSource)
        data = source.parse_bulk_file(json_file)

        assert "PKD1" in data
        assert data["PKD1"]["hgnc_id"] == "HGNC:9008"
        assert data["PKD1"]["symbol"] == "PKD1"
        assert data["PKD1"]["ensembl_gene_id"] == "ENSG00000008710"
        assert data["PKD1"]["ncbi_gene_id"] == "5310"

    def test_parse_extracts_locus_and_family(self, tmp_path: Path) -> None:
        """Parse HGNC JSON extracts locus_type and gene_family."""
        from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource

        json_file = _create_json(tmp_path)

        source = HGNCAnnotationSource.__new__(HGNCAnnotationSource)
        data = source.parse_bulk_file(json_file)

        assert data["PKD1"]["locus_type"] == "gene with protein product"
        assert data["PKD1"]["gene_family"] == ["Polycystins"]

    def test_parse_handles_mane_select(self, tmp_path: Path) -> None:
        """Parse HGNC JSON correctly parses MANE Select transcripts."""
        from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource

        json_file = _create_json(tmp_path)

        source = HGNCAnnotationSource.__new__(HGNCAnnotationSource)
        data = source.parse_bulk_file(json_file)

        mane = data["PKD1"]["mane_select"]
        assert mane is not None
        assert mane["ensembl_transcript_id"] == "ENST00000262304.10"
        assert mane["refseq_transcript_id"] == "NM_001009944.3"

    def test_parse_multiple_genes(self, tmp_path: Path) -> None:
        """Parse HGNC JSON includes all genes with symbols."""
        from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource

        json_file = _create_json(tmp_path)

        source = HGNCAnnotationSource.__new__(HGNCAnnotationSource)
        data = source.parse_bulk_file(json_file)

        assert "PKD1" in data
        assert "PKD2" in data
        assert "WITHDRAWN1" in data

    def test_parse_strips_none_values(self, tmp_path: Path) -> None:
        """Parsed annotations don't contain None values."""
        from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource

        json_file = _create_json(tmp_path)

        source = HGNCAnnotationSource.__new__(HGNCAnnotationSource)
        data = source.parse_bulk_file(json_file)

        for value in data["PKD1"].values():
            assert value is not None


@pytest.mark.unit
class TestHGNCBulkLookup:
    """Test bulk lookup returns correct data or None."""

    def test_lookup_returns_annotation_for_known_gene(self) -> None:
        """Genes in bulk data return their annotation dict."""
        from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource

        source = HGNCAnnotationSource.__new__(HGNCAnnotationSource)
        source._bulk_data = {"PKD1": {"hgnc_id": "HGNC:9008", "symbol": "PKD1"}}

        result = source.lookup_gene("PKD1")
        assert result is not None
        assert result["hgnc_id"] == "HGNC:9008"

    def test_lookup_returns_none_for_missing_gene(self) -> None:
        """Genes not in bulk data return None."""
        from app.pipeline.sources.annotations.hgnc import HGNCAnnotationSource

        source = HGNCAnnotationSource.__new__(HGNCAnnotationSource)
        source._bulk_data = {"PKD1": {"hgnc_id": "HGNC:9008"}}

        result = source.lookup_gene("NONEXISTENT")
        assert result is None
