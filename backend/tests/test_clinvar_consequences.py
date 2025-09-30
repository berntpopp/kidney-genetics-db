"""Test ClinVar molecular consequences extraction and categorization."""

from unittest.mock import Mock

from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource


class TestClinVarConsequences:
    """Test molecular consequence handling."""

    def test_parse_variant_with_consequences(self):
        """Test extraction of molecular_consequence_list."""
        clinvar = ClinVarAnnotationSource(Mock())

        variant_data = {
            "uid": "12345",
            "obj_type": "single nucleotide variant",
            "molecular_consequence_list": ["frameshift variant", "nonsense"],
        }

        result = clinvar._parse_variant(variant_data)

        assert result["molecular_consequences"] == ["frameshift variant", "nonsense"]
        assert result["variant_type"] == "single nucleotide variant"

    def test_parse_variant_without_consequences(self):
        """Test graceful handling when molecular_consequence_list is missing."""
        clinvar = ClinVarAnnotationSource(Mock())

        variant_data = {"uid": "12345", "obj_type": "single nucleotide variant"}

        result = clinvar._parse_variant(variant_data)

        assert result["molecular_consequences"] == []

    def test_aggregate_variants_categorization(self):
        """Test correct categorization of consequences."""
        clinvar = ClinVarAnnotationSource(Mock())

        variants = [
            {
                "molecular_consequences": ["frameshift variant"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "Deletion",
                "traits": [],
            },
            {
                "molecular_consequences": ["nonsense"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
            {
                "molecular_consequences": ["missense variant"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
            {
                "molecular_consequences": ["synonymous variant"],
                "classification": "benign",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
            {
                "molecular_consequences": ["splice donor variant"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
        ]

        stats = clinvar._aggregate_variants(variants)

        # Check counts
        assert (
            stats["consequence_categories"]["truncating"] == 3
        )  # frameshift, nonsense, splice donor
        assert stats["consequence_categories"]["missense"] == 1
        assert stats["consequence_categories"]["synonymous"] == 1

        # Check percentages
        assert stats["truncating_percentage"] == 60.0  # 3/5
        assert stats["missense_percentage"] == 20.0  # 1/5
        assert stats["synonymous_percentage"] == 20.0  # 1/5

        # Check top consequences
        assert len(stats["top_molecular_consequences"]) <= 10

    def test_aggregate_variants_empty_consequences(self):
        """Test aggregation when no consequences are provided."""
        clinvar = ClinVarAnnotationSource(Mock())

        variants = [
            {
                "molecular_consequences": [],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
            {
                "classification": "benign",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },  # Missing field entirely
        ]

        stats = clinvar._aggregate_variants(variants)

        # All categories should be 0
        assert all(count == 0 for count in stats["consequence_categories"].values())
        assert stats["truncating_percentage"] == 0

    def test_multiple_consequences_per_variant(self):
        """Test handling of variants with multiple consequences."""
        clinvar = ClinVarAnnotationSource(Mock())

        variants = [
            {
                "molecular_consequences": ["frameshift variant", "nonsense"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "Deletion",
                "traits": [],
            },
            {
                "molecular_consequences": ["missense variant", "splice region variant"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
        ]

        stats = clinvar._aggregate_variants(variants)

        # Both frameshift and nonsense should be counted as truncating
        assert stats["consequence_categories"]["truncating"] == 2  # frameshift + nonsense
        assert stats["consequence_categories"]["missense"] == 1
        assert stats["consequence_categories"]["splice_region"] == 1

        # Check that all consequences are tracked
        assert stats["molecular_consequences"]["frameshift variant"] == 1
        assert stats["molecular_consequences"]["nonsense"] == 1
        assert stats["molecular_consequences"]["missense variant"] == 1

    def test_consequence_percentage_calculation(self):
        """Test that percentages are calculated correctly."""
        clinvar = ClinVarAnnotationSource(Mock())

        # Create a dataset with known distribution
        variants = [
            {
                "molecular_consequences": ["frameshift variant"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "Deletion",
                "traits": [],
            },
            {
                "molecular_consequences": ["frameshift variant"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "Deletion",
                "traits": [],
            },
            {
                "molecular_consequences": ["missense variant"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
            {
                "molecular_consequences": ["missense variant"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
            {
                "molecular_consequences": ["missense variant"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
            {
                "molecular_consequences": ["synonymous variant"],
                "classification": "benign",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
            {
                "molecular_consequences": ["intron variant"],
                "classification": "benign",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
            {
                "molecular_consequences": ["splice acceptor variant"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },
            {
                "molecular_consequences": ["inframe_deletion"],
                "classification": "pathogenic",
                "review_status": "No data",
                "variant_type": "Deletion",
                "traits": [],
            },
            {
                "molecular_consequences": [],
                "classification": "benign",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            },  # Empty consequences
        ]

        stats = clinvar._aggregate_variants(variants)

        # Check total count
        assert stats["total_count"] == 10

        # Check category counts
        assert (
            stats["consequence_categories"]["truncating"] == 3
        )  # 2 frameshift + 1 splice acceptor
        assert stats["consequence_categories"]["missense"] == 3
        assert stats["consequence_categories"]["synonymous"] == 1
        assert stats["consequence_categories"]["intronic"] == 1
        assert stats["consequence_categories"]["inframe"] == 1

        # Check percentages
        assert stats["truncating_percentage"] == 30.0  # 3/10
        assert stats["missense_percentage"] == 30.0  # 3/10
        assert stats["synonymous_percentage"] == 10.0  # 1/10

    def test_top_molecular_consequences_sorting(self):
        """Test that top consequences are sorted by frequency."""
        clinvar = ClinVarAnnotationSource(Mock())

        # Create variants with varying consequence frequencies
        variants = []
        for _ in range(5):
            variants.append(
                {
                    "molecular_consequences": ["missense variant"],
                    "classification": "pathogenic",
                    "review_status": "No data",
                    "variant_type": "SNV",
                    "traits": [],
                }
            )
        for _ in range(3):
            variants.append(
                {
                    "molecular_consequences": ["frameshift variant"],
                    "classification": "pathogenic",
                    "review_status": "No data",
                    "variant_type": "Deletion",
                    "traits": [],
                }
            )
        for _ in range(2):
            variants.append(
                {
                    "molecular_consequences": ["nonsense"],
                    "classification": "pathogenic",
                    "review_status": "No data",
                    "variant_type": "SNV",
                    "traits": [],
                }
            )
        variants.append(
            {
                "molecular_consequences": ["synonymous variant"],
                "classification": "benign",
                "review_status": "No data",
                "variant_type": "SNV",
                "traits": [],
            }
        )

        stats = clinvar._aggregate_variants(variants)

        # Check that top consequences are sorted by count
        top_consequences = stats["top_molecular_consequences"]
        assert len(top_consequences) > 0
        assert top_consequences[0]["consequence"] == "missense variant"
        assert top_consequences[0]["count"] == 5
        assert top_consequences[1]["consequence"] == "frameshift variant"
        assert top_consequences[1]["count"] == 3
        assert top_consequences[2]["consequence"] == "nonsense"
        assert top_consequences[2]["count"] == 2
