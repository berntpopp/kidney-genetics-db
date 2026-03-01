"""
Unit tests for ClinVar HGVS parsing utilities.

Tests all pure functions in clinvar_utils.py with edge cases.
"""

import pytest

from app.pipeline.sources.annotations.clinvar_utils import (
    GeneAccumulator,
    format_accession,
    infer_effect_category,
    infer_molecular_consequences,
    map_classification,
    map_review_confidence,
    parse_protein_change,
    parse_protein_position,
    parse_variant_row,
)

# Standard confidence levels for tests
CONFIDENCE_LEVELS = {
    "practice guideline": 4,
    "reviewed by expert panel": 4,
    "criteria provided, multiple submitters, no conflicts": 3,
    "criteria provided, conflicting classifications": 2,
    "criteria provided, single submitter": 2,
    "no assertion for the individual variant": 1,
    "no assertion criteria provided": 1,
    "no classification provided": 0,
}


@pytest.mark.unit
class TestParseProteinChange:
    """Tests for parse_protein_change()."""

    def test_standard_missense(self) -> None:
        name = "NM_000297.4(PKD1):c.12616C>T (p.Arg4206Trp)"
        assert parse_protein_change(name) == "p.Arg4206Trp"

    def test_nonsense(self) -> None:
        name = "NM_000297.4(PKD1):c.11017C>T (p.Arg3673Ter)"
        assert parse_protein_change(name) == "p.Arg3673Ter"

    def test_frameshift(self) -> None:
        name = "NM_000297.4(PKD1):c.5014del (p.Ala1672ProfsTer38)"
        assert parse_protein_change(name) == "p.Ala1672ProfsTer38"

    def test_synonymous(self) -> None:
        name = "NM_000297.4(PKD1):c.12417C>T (p.Ser4139=)"
        assert parse_protein_change(name) == "p.Ser4139="

    def test_stop_star(self) -> None:
        name = "NM_000297.4(PKD1):c.12616C>T (p.Gly1234*)"
        assert parse_protein_change(name) == "p.Gly1234*"

    def test_extension(self) -> None:
        name = "NM_001234.5:c.100T>C (p.Ter100GlnextTer50)"
        assert parse_protein_change(name) == "p.Ter100GlnextTer50"

    def test_no_protein_change(self) -> None:
        name = "NM_000297.4(PKD1):c.10224+5G>A"
        assert parse_protein_change(name) == ""

    def test_empty_string(self) -> None:
        assert parse_protein_change("") == ""

    def test_none_like(self) -> None:
        assert parse_protein_change("") == ""

    def test_inframe_deletion(self) -> None:
        name = "NM_000297.4(PKD1):c.5014_5016del (p.Ala1672del)"
        assert parse_protein_change(name) == "p.Ala1672del"


@pytest.mark.unit
class TestParseProteinPosition:
    """Tests for parse_protein_position()."""

    def test_standard_position(self) -> None:
        assert parse_protein_position("p.Arg4206Trp") == 4206

    def test_stop_position(self) -> None:
        assert parse_protein_position("p.Gly1234*") == 1234

    def test_frameshift_position(self) -> None:
        assert parse_protein_position("p.Ala1672ProfsTer38") == 1672

    def test_ter_position(self) -> None:
        assert parse_protein_position("p.Arg3673Ter") == 3673

    def test_synonymous_position(self) -> None:
        assert parse_protein_position("p.Ser4139=") == 4139

    def test_empty(self) -> None:
        assert parse_protein_position("") is None

    def test_no_position(self) -> None:
        assert parse_protein_position("p.?") is None

    def test_single_digit(self) -> None:
        assert parse_protein_position("p.Met1Val") == 1


@pytest.mark.unit
class TestInferEffectCategory:
    """Tests for infer_effect_category()."""

    def test_missense(self) -> None:
        name = "NM_000297.4(PKD1):c.12616C>T (p.Arg4206Trp)"
        assert infer_effect_category(name) == "missense"

    def test_nonsense_ter(self) -> None:
        name = "NM_000297.4(PKD1):c.11017C>T (p.Arg3673Ter)"
        assert infer_effect_category(name) == "truncating"

    def test_nonsense_star(self) -> None:
        name = "NM_000297.4(PKD1):c.3G>A (p.Trp1*)"
        assert infer_effect_category(name) == "truncating"

    def test_frameshift(self) -> None:
        name = "NM_000297.4(PKD1):c.5014del (p.Ala1672ProfsTer38)"
        assert infer_effect_category(name) == "truncating"

    def test_synonymous(self) -> None:
        name = "NM_000297.4(PKD1):c.12417C>T (p.Ser4139=)"
        assert infer_effect_category(name) == "synonymous"

    def test_extension_not_truncating(self) -> None:
        name = "NM_001234.5:c.100T>C (p.Ter100GlnextTer50)"
        assert infer_effect_category(name) != "truncating"

    def test_canonical_splice_donor(self) -> None:
        name = "NM_000297.4(PKD1):c.10224+1G>A"
        assert infer_effect_category(name) == "splice_region"

    def test_canonical_splice_acceptor(self) -> None:
        name = "NM_000297.4(PKD1):c.10225-2A>G"
        assert infer_effect_category(name) == "splice_region"

    def test_intronic(self) -> None:
        name = "NM_000297.4(PKD1):c.10224+5G>A"
        assert infer_effect_category(name) == "intronic"

    def test_inframe_deletion(self) -> None:
        name = "NM_000297.4(PKD1):c.5014_5016del (p.Ala1672del)"
        assert infer_effect_category(name) == "inframe"

    def test_inframe_dup(self) -> None:
        name = "NM_000297.4(PKD1):c.100_102dup (p.Ala34dup)"
        assert infer_effect_category(name) == "inframe"

    def test_empty(self) -> None:
        assert infer_effect_category("") == "other"

    def test_genomic_deletion_no_protein(self) -> None:
        name = "NC_000016.10:g.2100000del"
        assert infer_effect_category(name) == "inframe"

    def test_splice_plus_2(self) -> None:
        name = "NM_000297.4(PKD1):c.10224+2T>C"
        assert infer_effect_category(name) == "splice_region"

    def test_deep_intronic(self) -> None:
        name = "NM_000297.4(PKD1):c.10224+50G>A"
        assert infer_effect_category(name) == "intronic"


@pytest.mark.unit
class TestInferMolecularConsequences:
    """Tests for infer_molecular_consequences()."""

    def test_truncating_frameshift(self) -> None:
        name = "NM_000297.4(PKD1):c.5014del (p.Ala1672ProfsTer38)"
        result = infer_molecular_consequences(name, "truncating")
        assert result == ["frameshift variant"]

    def test_truncating_nonsense(self) -> None:
        name = "NM_000297.4(PKD1):c.11017C>T (p.Arg3673Ter)"
        result = infer_molecular_consequences(name, "truncating")
        assert result == ["nonsense"]

    def test_missense(self) -> None:
        result = infer_molecular_consequences("...", "missense")
        assert result == ["missense variant"]

    def test_synonymous(self) -> None:
        result = infer_molecular_consequences("...", "synonymous")
        assert result == ["synonymous variant"]

    def test_splice_donor(self) -> None:
        name = "NM_000297.4(PKD1):c.10224+1G>A"
        result = infer_molecular_consequences(name, "splice_region")
        assert result == ["splice donor variant"]

    def test_splice_acceptor(self) -> None:
        name = "NM_000297.4(PKD1):c.10225-2A>G"
        result = infer_molecular_consequences(name, "splice_region")
        assert result == ["splice acceptor variant"]

    def test_intronic(self) -> None:
        result = infer_molecular_consequences("...", "intronic")
        assert result == ["intron variant"]

    def test_inframe(self) -> None:
        result = infer_molecular_consequences("...", "inframe")
        assert result == ["inframe_indel"]

    def test_other(self) -> None:
        result = infer_molecular_consequences("...", "other")
        assert result == ["other"]


@pytest.mark.unit
class TestMapClassification:
    """Tests for map_classification()."""

    def test_pathogenic(self) -> None:
        assert map_classification("Pathogenic") == "pathogenic"

    def test_likely_pathogenic(self) -> None:
        assert map_classification("Likely pathogenic") == "likely_pathogenic"

    def test_pathogenic_likely_pathogenic(self) -> None:
        assert map_classification("Pathogenic/Likely pathogenic") == "pathogenic"

    def test_benign(self) -> None:
        assert map_classification("Benign") == "benign"

    def test_likely_benign(self) -> None:
        assert map_classification("Likely benign") == "likely_benign"

    def test_uncertain_significance(self) -> None:
        assert map_classification("Uncertain significance") == "vus"

    def test_uncertain_with_other(self) -> None:
        assert map_classification("Uncertain significance; other") == "vus"

    def test_conflicting(self) -> None:
        assert map_classification("Conflicting classifications of pathogenicity") == "conflicting"

    def test_not_provided(self) -> None:
        assert map_classification("not provided") == "not_provided"

    def test_empty(self) -> None:
        assert map_classification("") == "not_provided"

    def test_dash(self) -> None:
        assert map_classification("-") == "not_provided"

    def test_drug_response(self) -> None:
        assert map_classification("drug response") == "other"

    def test_benign_likely_benign(self) -> None:
        assert map_classification("Benign/Likely benign") == "likely_benign"


@pytest.mark.unit
class TestMapReviewConfidence:
    """Tests for map_review_confidence()."""

    def test_practice_guideline(self) -> None:
        assert map_review_confidence("practice guideline", CONFIDENCE_LEVELS) == 4

    def test_expert_panel(self) -> None:
        assert map_review_confidence("reviewed by expert panel", CONFIDENCE_LEVELS) == 4

    def test_multiple_submitters(self) -> None:
        result = map_review_confidence(
            "criteria provided, multiple submitters, no conflicts", CONFIDENCE_LEVELS
        )
        assert result == 3

    def test_single_submitter(self) -> None:
        assert (
            map_review_confidence("criteria provided, single submitter", CONFIDENCE_LEVELS) == 2
        )

    def test_no_assertion(self) -> None:
        assert (
            map_review_confidence("no assertion criteria provided", CONFIDENCE_LEVELS) == 1
        )

    def test_empty(self) -> None:
        assert map_review_confidence("", CONFIDENCE_LEVELS) == 0

    def test_dash(self) -> None:
        assert map_review_confidence("-", CONFIDENCE_LEVELS) == 0

    def test_unknown_status(self) -> None:
        assert map_review_confidence("some unknown status", CONFIDENCE_LEVELS) == 0


@pytest.mark.unit
class TestFormatAccession:
    """Tests for format_accession()."""

    def test_standard(self) -> None:
        assert format_accession("12345") == "VCV000012345"

    def test_large_number(self) -> None:
        assert format_accession("999999999") == "VCV999999999"

    def test_single_digit(self) -> None:
        assert format_accession("1") == "VCV000000001"

    def test_zero(self) -> None:
        assert format_accession("0") == "VCV000000000"

    def test_non_numeric(self) -> None:
        result = format_accession("abc")
        assert result == "VCVabc"


@pytest.mark.unit
class TestParseVariantRow:
    """Tests for parse_variant_row()."""

    def test_complete_row(self) -> None:
        row = {
            "Name": "NM_000297.4(PKD1):c.12616C>T (p.Arg4206Trp)",
            "ClinicalSignificance": "Pathogenic",
            "ReviewStatus": "criteria provided, single submitter",
            "VariationID": "12345",
            "Type": "single nucleotide variant",
            "Chromosome": "16",
            "Start": "2138000",
            "Stop": "2138000",
            "GeneSymbol": "PKD1",
            "PhenotypeList": "Polycystic kidney disease|Autosomal dominant",
        }
        result = parse_variant_row(row, CONFIDENCE_LEVELS)

        assert result["variant_id"] == "12345"
        assert result["accession"] == "VCV000012345"
        assert result["classification"] == "Pathogenic"
        assert result["review_status"] == "criteria provided, single submitter"
        assert result["protein_change"] == "p.Arg4206Trp"
        assert result["variant_type"] == "single nucleotide variant"
        assert result["chromosome"] == "16"
        assert result["genomic_start"] == 2138000
        assert result["genomic_end"] == 2138000
        assert result["molecular_consequences"] == ["missense variant"]
        assert len(result["traits"]) == 2
        assert result["traits"][0]["name"] == "Polycystic kidney disease"

    def test_minimal_row(self) -> None:
        row: dict[str, str] = {}
        result = parse_variant_row(row, CONFIDENCE_LEVELS)

        assert result["classification"] == "Not classified"
        assert result["review_status"] == "No data"
        assert result["protein_change"] == ""
        assert result["traits"] == []

    def test_not_provided_phenotype_excluded(self) -> None:
        row = {
            "PhenotypeList": "not provided",
            "Name": "",
            "ClinicalSignificance": "",
            "ReviewStatus": "",
            "VariationID": "1",
        }
        result = parse_variant_row(row, CONFIDENCE_LEVELS)
        assert result["traits"] == []

    def test_dash_phenotype_excluded(self) -> None:
        row = {
            "PhenotypeList": "-",
            "Name": "",
            "ClinicalSignificance": "",
            "ReviewStatus": "",
            "VariationID": "1",
        }
        result = parse_variant_row(row, CONFIDENCE_LEVELS)
        assert result["traits"] == []

    def test_genomic_coordinates_na(self) -> None:
        row = {
            "Start": "-",
            "Stop": "na",
            "Name": "",
            "ClinicalSignificance": "",
            "ReviewStatus": "",
            "VariationID": "1",
        }
        result = parse_variant_row(row, CONFIDENCE_LEVELS)
        assert result["genomic_start"] is None
        assert result["genomic_end"] is None


@pytest.mark.unit
class TestGeneAccumulator:
    """Tests for GeneAccumulator streaming aggregation."""

    def _make_variant(
        self,
        classification: str = "Pathogenic",
        review_status: str = "criteria provided, single submitter",
        protein_change: str = "p.Arg100Trp",
        genomic_start: int | None = 12345,
        variant_type: str = "single nucleotide variant",
        mol_consequences: list[str] | None = None,
        traits: list[dict[str, str | None]] | None = None,
    ) -> dict[str, object]:
        return {
            "variant_id": "1",
            "accession": "VCV000000001",
            "title": "test",
            "variant_type": variant_type,
            "classification": classification,
            "review_status": review_status,
            "traits": traits or [],
            "molecular_consequences": mol_consequences or ["missense variant"],
            "chromosome": "1",
            "genomic_start": genomic_start,
            "genomic_end": genomic_start,
            "protein_change": protein_change,
            "cdna_change": "c.100C>T",
        }

    def test_empty_accumulator(self) -> None:
        acc = GeneAccumulator(CONFIDENCE_LEVELS)
        stats = acc.finalize()
        assert stats["total_count"] == 0
        assert stats["has_pathogenic"] is False
        assert stats["protein_variants"] == []
        assert stats["genomic_variants"] == []

    def test_single_pathogenic(self) -> None:
        acc = GeneAccumulator(CONFIDENCE_LEVELS)
        acc.add_variant(self._make_variant("Pathogenic"))
        stats = acc.finalize()
        assert stats["total_count"] == 1
        assert stats["pathogenic_count"] == 1
        assert stats["has_pathogenic"] is True
        assert stats["pathogenic_percentage"] == 100.0

    def test_classification_counts(self) -> None:
        acc = GeneAccumulator(CONFIDENCE_LEVELS)
        acc.add_variant(self._make_variant("Pathogenic"))
        acc.add_variant(self._make_variant("Likely pathogenic"))
        acc.add_variant(self._make_variant("Uncertain significance"))
        acc.add_variant(self._make_variant("Benign"))
        acc.add_variant(self._make_variant("Likely benign"))
        acc.add_variant(self._make_variant("Conflicting classifications"))
        stats = acc.finalize()
        assert stats["pathogenic_count"] == 1
        assert stats["likely_pathogenic_count"] == 1
        assert stats["vus_count"] == 1
        assert stats["benign_count"] == 1
        assert stats["likely_benign_count"] == 1
        assert stats["conflicting_count"] == 1
        assert stats["total_count"] == 6

    def test_high_confidence_counting(self) -> None:
        acc = GeneAccumulator(CONFIDENCE_LEVELS)
        acc.add_variant(
            self._make_variant(
                review_status="criteria provided, multiple submitters, no conflicts"
            )
        )
        acc.add_variant(
            self._make_variant(review_status="criteria provided, single submitter")
        )
        stats = acc.finalize()
        assert stats["high_confidence_count"] == 1

    def test_protein_variant_capping(self) -> None:
        acc = GeneAccumulator(CONFIDENCE_LEVELS, max_detail=3)
        for i in range(10):
            acc.add_variant(self._make_variant(protein_change=f"p.Arg{i + 1}Trp"))
        stats = acc.finalize()
        assert len(stats["protein_variants"]) == 3
        assert stats["total_count"] == 10

    def test_genomic_variant_capping(self) -> None:
        acc = GeneAccumulator(CONFIDENCE_LEVELS, max_detail=2)
        for i in range(5):
            acc.add_variant(self._make_variant(genomic_start=1000 + i))
        stats = acc.finalize()
        assert len(stats["genomic_variants"]) == 2
        assert stats["total_count"] == 5

    def test_variant_type_counts(self) -> None:
        acc = GeneAccumulator(CONFIDENCE_LEVELS)
        acc.add_variant(self._make_variant(variant_type="single nucleotide variant"))
        acc.add_variant(self._make_variant(variant_type="Deletion"))
        acc.add_variant(self._make_variant(variant_type="single nucleotide variant"))
        stats = acc.finalize()
        assert stats["variant_type_counts"]["single nucleotide variant"] == 2
        assert stats["variant_type_counts"]["Deletion"] == 1

    def test_traits_aggregation(self) -> None:
        acc = GeneAccumulator(CONFIDENCE_LEVELS)
        acc.add_variant(
            self._make_variant(traits=[{"name": "PKD"}, {"name": "ADPKD"}])
        )
        acc.add_variant(self._make_variant(traits=[{"name": "PKD"}]))
        stats = acc.finalize()
        assert stats["top_traits"][0]["trait"] == "PKD"
        assert stats["top_traits"][0]["count"] == 2

    def test_consequence_categories(self) -> None:
        acc = GeneAccumulator(CONFIDENCE_LEVELS)
        acc.add_variant(self._make_variant(mol_consequences=["missense variant"]))
        acc.add_variant(self._make_variant(mol_consequences=["nonsense"]))
        acc.add_variant(self._make_variant(mol_consequences=["synonymous variant"]))
        stats = acc.finalize()
        assert stats["consequence_categories"]["missense"] == 1
        assert stats["consequence_categories"]["truncating"] == 1
        assert stats["consequence_categories"]["synonymous"] == 1

    def test_finalize_output_schema(self) -> None:
        acc = GeneAccumulator(CONFIDENCE_LEVELS)
        acc.add_variant(self._make_variant())
        stats = acc.finalize()
        required_keys = [
            "total_count",
            "pathogenic_count",
            "likely_pathogenic_count",
            "vus_count",
            "benign_count",
            "likely_benign_count",
            "conflicting_count",
            "not_provided_count",
            "high_confidence_count",
            "variant_type_counts",
            "molecular_consequences",
            "protein_variants",
            "genomic_variants",
            "consequence_categories",
            "top_molecular_consequences",
            "top_traits",
            "high_confidence_percentage",
            "pathogenic_percentage",
            "has_pathogenic",
        ]
        for key in required_keys:
            assert key in stats, f"Missing key: {key}"
