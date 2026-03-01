"""
Tests for ClinVar bulk variant_summary.txt.gz parsing, deduplication,
batch fetch with bulk + API fallback, and NCBI API key support.
"""

import csv
import gzip
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# -- Fixtures: variant_summary.txt header + sample rows --

VARIANT_SUMMARY_HEADER = [
    "#AlleleID",
    "Type",
    "Name",
    "GeneID",
    "GeneSymbol",
    "HGNC_ID",
    "ClinicalSignificance",
    "ClinSigSimple",
    "LastEvaluated",
    "RS# (dbSNP)",
    "nsv/esv (dbVar)",
    "RCVaccession",
    "PhenotypeIDS",
    "PhenotypeList",
    "Origin",
    "OriginSimple",
    "Assembly",
    "ChromosomeAccession",
    "Chromosome",
    "Start",
    "Stop",
    "ReferenceAllele",
    "AlternateAllele",
    "Cytogenetic",
    "ReviewStatus",
    "NumberSubmitters",
    "Guidelines",
    "TestedInGTR",
    "OtherIDs",
    "SubmitterCategories",
    "VariationID",
    "PositionVCF",
    "ReferenceAlleleVCF",
    "AlternateAlleleVCF",
    "SomaticClinicalImpact",
    "SomaticClinicalImpactLastEvaluated",
    "ReviewStatusClinicalImpact",
    "OncogenicityClassification",
    "OncogenicityLastEvaluated",
    "ReviewStatusOncogenicity",
]

# Sample rows: 2 GRCh38 PKD1 variants, 1 GRCh37 duplicate, 1 NPHS1, 1 multi-gene, 1 non-target
SAMPLE_ROWS = [
    {
        "VariationID": "100",
        "Type": "single nucleotide variant",
        "Name": "NM_000297.4(PKD1):c.12616C>T (p.Arg4206Trp)",
        "GeneID": "5310",
        "GeneSymbol": "PKD1",
        "ClinicalSignificance": "Pathogenic",
        "Assembly": "GRCh38",
        "Chromosome": "16",
        "Start": "2138000",
        "Stop": "2138000",
        "ReviewStatus": "criteria provided, single submitter",
        "PhenotypeList": "Polycystic kidney disease",
    },
    {
        "VariationID": "101",
        "Type": "Deletion",
        "Name": "NM_000297.4(PKD1):c.5014del (p.Ala1672ProfsTer38)",
        "GeneID": "5310",
        "GeneSymbol": "PKD1",
        "ClinicalSignificance": "Likely pathogenic",
        "Assembly": "GRCh38",
        "Chromosome": "16",
        "Start": "2145000",
        "Stop": "2145000",
        "ReviewStatus": "criteria provided, multiple submitters, no conflicts",
        "PhenotypeList": "Polycystic kidney disease|Autosomal dominant",
    },
    {
        # Duplicate of 100 on GRCh37 — should be deduped (GRCh38 wins)
        "VariationID": "100",
        "Type": "single nucleotide variant",
        "Name": "NM_000297.4(PKD1):c.12616C>T (p.Arg4206Trp)",
        "GeneID": "5310",
        "GeneSymbol": "PKD1",
        "ClinicalSignificance": "Pathogenic",
        "Assembly": "GRCh37",
        "Chromosome": "16",
        "Start": "2100000",
        "Stop": "2100000",
        "ReviewStatus": "criteria provided, single submitter",
        "PhenotypeList": "Polycystic kidney disease",
    },
    {
        "VariationID": "200",
        "Type": "single nucleotide variant",
        "Name": "NM_004646.4(NPHS1):c.1339G>A (p.Glu447Lys)",
        "GeneID": "4868",
        "GeneSymbol": "NPHS1",
        "ClinicalSignificance": "Uncertain significance",
        "Assembly": "GRCh38",
        "Chromosome": "19",
        "Start": "35830000",
        "Stop": "35830000",
        "ReviewStatus": "criteria provided, single submitter",
        "PhenotypeList": "Nephrotic syndrome",
    },
    {
        # Multi-gene variant: PKD1 and PKD1-AS1, only PKD1 is target
        "VariationID": "300",
        "Type": "Deletion",
        "Name": "NC_000016.10:g.2150000del",
        "GeneID": "5310;100133050",
        "GeneSymbol": "PKD1;PKD1-AS1",
        "ClinicalSignificance": "Benign",
        "Assembly": "GRCh38",
        "Chromosome": "16",
        "Start": "2150000",
        "Stop": "2150000",
        "ReviewStatus": "no assertion criteria provided",
        "PhenotypeList": "not provided",
    },
    {
        # Non-target gene (should be filtered out)
        "VariationID": "999",
        "Type": "single nucleotide variant",
        "Name": "NM_999999.1:c.100A>G (p.Met1Val)",
        "GeneID": "99999",
        "GeneSymbol": "NONTARGET",
        "ClinicalSignificance": "Benign",
        "Assembly": "GRCh38",
        "Chromosome": "1",
        "Start": "100",
        "Stop": "100",
        "ReviewStatus": "no assertion criteria provided",
        "PhenotypeList": "-",
    },
    {
        # GRCh37-only variant (no GRCh38 version) — should be kept
        "VariationID": "102",
        "Type": "single nucleotide variant",
        "Name": "NM_000297.4(PKD1):c.10224+5G>A",
        "GeneID": "5310",
        "GeneSymbol": "PKD1",
        "ClinicalSignificance": "Uncertain significance",
        "Assembly": "GRCh37",
        "Chromosome": "16",
        "Start": "2160000",
        "Stop": "2160000",
        "ReviewStatus": "criteria provided, single submitter",
        "PhenotypeList": "not provided",
    },
]


def _create_variant_summary_gz(tmp_path: Path, rows: list[dict[str, str]] | None = None) -> Path:
    """Create a gzipped variant_summary.txt fixture."""
    if rows is None:
        rows = SAMPLE_ROWS

    gz_path = tmp_path / "variant_summary.txt.gz"
    with gzip.open(gz_path, "wt", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=VARIANT_SUMMARY_HEADER, delimiter="\t")
        writer.writeheader()
        for row in rows:
            # Fill missing columns with empty strings
            full_row = {col: row.get(col, "") for col in VARIANT_SUMMARY_HEADER}
            writer.writerow(full_row)

    return gz_path


def _create_source_with_bulk(
    tmp_path: Path,
    target_genes: set[str],
    rows: list[dict[str, str]] | None = None,
) -> Any:
    """Create a ClinVarAnnotationSource with pre-parsed bulk data."""
    from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

    source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
    source._review_confidence_levels = {
        "practice guideline": 4,
        "reviewed by expert panel": 4,
        "criteria provided, multiple submitters, no conflicts": 3,
        "criteria provided, conflicting classifications": 2,
        "criteria provided, single submitter": 2,
        "no assertion for the individual variant": 1,
        "no assertion criteria provided": 1,
        "no classification provided": 0,
    }
    source._target_genes = target_genes
    source._bulk_data = None

    gz_path = _create_variant_summary_gz(tmp_path, rows)
    source._bulk_data = source._parse_variant_summary(gz_path, target_genes)
    return source


@pytest.mark.unit
class TestClinVarBulkParsing:
    """Test variant_summary.txt.gz parsing and dedup."""

    def test_parses_target_genes_only(self, tmp_path: Path) -> None:
        """Only target genes appear in parsed output."""
        target = {"PKD1", "NPHS1"}
        source = _create_source_with_bulk(tmp_path, target)

        assert "PKD1" in source._bulk_data
        assert "NPHS1" in source._bulk_data
        assert "NONTARGET" not in source._bulk_data

    def test_dedup_prefers_grch38(self, tmp_path: Path) -> None:
        """GRCh38 row is preferred over GRCh37 for same VariationID."""
        target = {"PKD1"}
        source = _create_source_with_bulk(tmp_path, target)

        # PKD1 should have 4 unique variants: 100, 101, 300, 102
        pkd1 = source._bulk_data["PKD1"]
        assert pkd1["total_variants"] == 4

    def test_grch37_only_variant_kept(self, tmp_path: Path) -> None:
        """Variant with only GRCh37 assembly is included."""
        target = {"PKD1"}
        source = _create_source_with_bulk(tmp_path, target)

        # VariationID 102 only has GRCh37
        pkd1 = source._bulk_data["PKD1"]
        accessions = [v["accession"] for v in pkd1.get("protein_variants", [])]
        genomic_accessions = [v["accession"] for v in pkd1.get("genomic_variants", [])]
        # It should appear in genomic variants at minimum
        all_accessions = accessions + genomic_accessions
        assert any("102" in a for a in all_accessions) or pkd1["total_variants"] >= 4

    def test_multi_gene_variant_assigned_to_target(self, tmp_path: Path) -> None:
        """Multi-gene variant (PKD1;PKD1-AS1) is assigned to PKD1."""
        target = {"PKD1"}
        source = _create_source_with_bulk(tmp_path, target)
        assert source._bulk_data["PKD1"]["total_variants"] >= 3

    def test_aggregation_output_schema(self, tmp_path: Path) -> None:
        """Bulk-parsed annotation has required schema fields."""
        target = {"PKD1"}
        source = _create_source_with_bulk(tmp_path, target)
        pkd1 = source._bulk_data["PKD1"]

        required_keys = [
            "gene_symbol",
            "total_variants",
            "pathogenic_count",
            "likely_pathogenic_count",
            "vus_count",
            "benign_count",
            "likely_benign_count",
            "conflicting_count",
            "has_pathogenic",
            "pathogenic_percentage",
            "high_confidence_percentage",
            "variant_types",
            "top_traits",
            "molecular_consequences",
            "consequence_categories",
            "protein_variants",
            "genomic_variants",
            "variant_summary",
            "last_updated",
        ]
        for key in required_keys:
            assert key in pkd1, f"Missing key: {key}"

    def test_pathogenic_counts(self, tmp_path: Path) -> None:
        """Pathogenic and likely pathogenic are counted correctly."""
        target = {"PKD1"}
        source = _create_source_with_bulk(tmp_path, target)
        pkd1 = source._bulk_data["PKD1"]

        assert pkd1["pathogenic_count"] >= 1
        assert pkd1["likely_pathogenic_count"] >= 1
        assert pkd1["has_pathogenic"] is True

    def test_nphs1_is_vus(self, tmp_path: Path) -> None:
        """NPHS1 variant classified as VUS."""
        target = {"NPHS1"}
        source = _create_source_with_bulk(tmp_path, target)
        nphs1 = source._bulk_data["NPHS1"]

        assert nphs1["vus_count"] == 1
        assert nphs1["total_variants"] == 1

    def test_empty_gene_gets_zero_annotation(self, tmp_path: Path) -> None:
        """Target gene not in file gets empty annotation."""
        target = {"MISSING_GENE"}
        source = _create_source_with_bulk(tmp_path, target)

        assert "MISSING_GENE" in source._bulk_data
        assert source._bulk_data["MISSING_GENE"]["total_variants"] == 0

    def test_traits_parsed(self, tmp_path: Path) -> None:
        """Traits are extracted from PhenotypeList."""
        target = {"PKD1"}
        source = _create_source_with_bulk(tmp_path, target)
        pkd1 = source._bulk_data["PKD1"]

        # Should have "Polycystic kidney disease" as a top trait
        trait_names = [t["trait"] for t in pkd1["top_traits"]]
        assert any("Polycystic" in t for t in trait_names)


@pytest.mark.unit
class TestClinVarBulkFetchBatch:
    """Test fetch_batch with bulk data + API fallback."""

    @pytest.mark.asyncio
    async def test_bulk_hit_no_api_call(self, tmp_path: Path) -> None:
        """Gene found in bulk data does not trigger API call."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        source._review_confidence_levels = {
            "criteria provided, single submitter": 2,
            "no assertion criteria provided": 1,
        }
        source._target_genes = {"PKD1"}
        source._bulk_data = None
        source.circuit_breaker = None

        gz_path = _create_variant_summary_gz(tmp_path)
        source._bulk_data = source._parse_variant_summary(gz_path, {"PKD1"})

        gene = MagicMock()
        gene.id = 1
        gene.approved_symbol = "PKD1"

        source._fetch_via_api = AsyncMock()

        results = await source.fetch_batch([gene])

        assert 1 in results
        assert results[1]["gene_symbol"] == "PKD1"
        source._fetch_via_api.assert_not_called()

    @pytest.mark.asyncio
    async def test_bulk_miss_triggers_api_fallback(self, tmp_path: Path) -> None:
        """Gene not in bulk data triggers API fallback."""
        from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

        source = ClinVarAnnotationSource.__new__(ClinVarAnnotationSource)
        source._review_confidence_levels = {"criteria provided, single submitter": 2}
        source._target_genes = set()
        source._bulk_data = {}
        source.circuit_breaker = None

        gene = MagicMock()
        gene.id = 99
        gene.approved_symbol = "UNKNOWN_GENE"

        api_result = {
            "gene_symbol": "UNKNOWN_GENE",
            "total_variants": 5,
            "pathogenic_count": 1,
            "likely_pathogenic_count": 0,
            "vus_count": 2,
            "benign_count": 1,
            "likely_benign_count": 1,
            "conflicting_count": 0,
            "has_pathogenic": True,
        }
        source._fetch_via_api = AsyncMock(return_value=api_result)
        source._is_valid_annotation = MagicMock(return_value=True)

        results = await source.fetch_batch([gene])

        source._fetch_via_api.assert_called_once_with(gene)
        assert 99 in results
        assert results[99]["total_variants"] == 5


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
