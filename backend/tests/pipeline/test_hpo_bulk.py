"""
Tests for HPO bulk file parsing in HPOAnnotationSource.

Verifies that the genes_to_phenotype.txt bulk file is correctly parsed
and produces annotation dicts compatible with the API path.
"""

from pathlib import Path

import pytest

# Sample genes_to_phenotype.txt content
# Format: ncbi_gene_id\tgene_symbol\thpo_id\thpo_name\tfrequency\tdisease_id
SAMPLE_HEADER = (
    "#Format: ncbi_gene_id<tab>gene_symbol<tab>hpo_id<tab>hpo_name"
    "<tab>frequency<tab>disease_id\n"
)

SAMPLE_ROWS = """\
5310\tPKD1\tHP:0000107\tRenal cyst\tHP:0040283\tOMIM:173900
5310\tPKD1\tHP:0000112\tNephropathy\t-\tOMIM:173900
5310\tPKD1\tHP:0001407\tHepatic cyst\tHP:0040282\tOMIM:173900
5311\tPKD2\tHP:0000107\tRenal cyst\tHP:0040283\tOMIM:613095
5311\tPKD2\tHP:0001250\tSeizure\t-\tOMIM:613095
7157\tTP53\tHP:0002664\tNeoplasm\tHP:0040281\tOMIM:151623
"""

# File with no data rows
SAMPLE_EMPTY = SAMPLE_HEADER


def _create_bulk_file(tmp_path: Path, content: str | None = None) -> Path:
    """Create a temporary genes_to_phenotype.txt file."""
    if content is None:
        content = SAMPLE_HEADER + SAMPLE_ROWS
    bulk_file = tmp_path / "genes_to_phenotype.txt"
    bulk_file.write_text(content)
    return bulk_file


@pytest.mark.unit
class TestHPOBulkParsing:
    """Test genes_to_phenotype.txt parsing."""

    def test_parse_extracts_gene_phenotypes(self, tmp_path: Path) -> None:
        """Parse HPO bulk file groups phenotypes by gene symbol."""
        from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

        bulk_file = _create_bulk_file(tmp_path)

        source = HPOAnnotationSource.__new__(HPOAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert "PKD1" in data
        phenotypes = data["PKD1"]["phenotypes"]
        hpo_ids = {p["id"] for p in phenotypes}
        assert "HP:0000107" in hpo_ids
        assert "HP:0000112" in hpo_ids
        assert "HP:0001407" in hpo_ids

    def test_parse_extracts_ncbi_gene_id(self, tmp_path: Path) -> None:
        """Parsed data includes ncbi_gene_id."""
        from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

        bulk_file = _create_bulk_file(tmp_path)

        source = HPOAnnotationSource.__new__(HPOAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert data["PKD1"]["ncbi_gene_id"] == "5310"
        assert data["PKD2"]["ncbi_gene_id"] == "5311"

    def test_parse_extracts_diseases(self, tmp_path: Path) -> None:
        """Parsed data includes disease associations."""
        from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

        bulk_file = _create_bulk_file(tmp_path)

        source = HPOAnnotationSource.__new__(HPOAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        diseases = data["PKD1"]["diseases"]
        disease_ids = {d["id"] for d in diseases}
        assert "OMIM:173900" in disease_ids

    def test_parse_multiple_genes(self, tmp_path: Path) -> None:
        """All genes in bulk file are parsed."""
        from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

        bulk_file = _create_bulk_file(tmp_path)

        source = HPOAnnotationSource.__new__(HPOAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert len(data) == 3
        assert "PKD1" in data
        assert "PKD2" in data
        assert "TP53" in data

    def test_parse_deduplicates_phenotypes(self, tmp_path: Path) -> None:
        """Duplicate HPO terms for same gene are deduplicated."""
        from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

        content = SAMPLE_HEADER + (
            "5310\tPKD1\tHP:0000107\tRenal cyst\tHP:0040283\tOMIM:173900\n"
            "5310\tPKD1\tHP:0000107\tRenal cyst\t-\tOMIM:600666\n"
        )
        bulk_file = _create_bulk_file(tmp_path, content)

        source = HPOAnnotationSource.__new__(HPOAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        # Should have only one entry for HP:0000107
        phenotypes = data["PKD1"]["phenotypes"]
        assert len(phenotypes) == 1
        assert phenotypes[0]["id"] == "HP:0000107"

    def test_parse_phenotype_name_included(self, tmp_path: Path) -> None:
        """Phenotype names are extracted from bulk file."""
        from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

        bulk_file = _create_bulk_file(tmp_path)

        source = HPOAnnotationSource.__new__(HPOAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        phenotypes = data["PKD1"]["phenotypes"]
        names = {p["name"] for p in phenotypes}
        assert "Renal cyst" in names
        assert "Nephropathy" in names

    def test_parse_skips_comment_lines(self, tmp_path: Path) -> None:
        """Comment/header lines starting with # are skipped."""
        from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

        content = (
            "# This is a comment\n"
            "#Format: ncbi_gene_id...\n"
            "5310\tPKD1\tHP:0000107\tRenal cyst\tHP:0040283\tOMIM:173900\n"
        )
        bulk_file = _create_bulk_file(tmp_path, content)

        source = HPOAnnotationSource.__new__(HPOAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert "PKD1" in data

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Empty bulk file returns empty dict."""
        from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

        bulk_file = _create_bulk_file(tmp_path, SAMPLE_EMPTY)

        source = HPOAnnotationSource.__new__(HPOAnnotationSource)
        data = source.parse_bulk_file(bulk_file)

        assert data == {}


@pytest.mark.unit
class TestHPOBulkLookup:
    """Test bulk lookup returns correct data or None."""

    def test_lookup_returns_annotation_for_known_gene(self) -> None:
        """Genes in bulk data return their annotation dict."""
        from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

        source = HPOAnnotationSource.__new__(HPOAnnotationSource)
        source._bulk_data = {
            "PKD1": {
                "ncbi_gene_id": "5310",
                "phenotypes": [{"id": "HP:0000107", "name": "Renal cyst"}],
                "diseases": [{"id": "OMIM:173900", "db": "OMIM", "dbId": "173900"}],
            }
        }

        result = source.lookup_gene("PKD1")
        assert result is not None
        assert result["ncbi_gene_id"] == "5310"

    def test_lookup_returns_none_for_missing_gene(self) -> None:
        """Genes not in bulk data return None."""
        from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

        source = HPOAnnotationSource.__new__(HPOAnnotationSource)
        source._bulk_data = {"PKD1": {"ncbi_gene_id": "5310"}}

        result = source.lookup_gene("NONEXISTENT")
        assert result is None

    def test_lookup_returns_none_when_data_not_loaded(self) -> None:
        """Lookup returns None when bulk data hasn't been loaded."""
        from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

        source = HPOAnnotationSource.__new__(HPOAnnotationSource)
        source._bulk_data = None

        result = source.lookup_gene("PKD1")
        assert result is None
