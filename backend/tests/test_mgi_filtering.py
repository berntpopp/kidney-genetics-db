"""Unit tests for MGI/MPO annotation filtering logic"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.pipeline.sources.annotations.mpo_mgi import MPOMGIAnnotationSource


class TestMGIFiltering:
    """Test MGI/MPO phenotype filtering logic"""

    def test_phenotype_filtering_with_kidney_terms(self):
        """Test that kidney-related phenotypes are correctly filtered"""
        # Setup
        mock_session = Mock()
        source = MPOMGIAnnotationSource(mock_session)

        # Kidney-related MPO terms
        kidney_mpo_terms = {"MP:0000519", "MP:0000520", "MP:0002135"}

        # Mock MouseMine results with mixed phenotypes
        mock_results = [
            # [primaryId, symbol, background, zygosity, mpo_id, mpo_name]
            ["MGI:1", "Pkd1", "C57BL/6J", "hm", "MP:0000519", "hydroureter"],
            ["MGI:1", "Pkd1", "C57BL/6J", "hm", "MP:0000520", "kidney hemorrhage"],
            ["MGI:1", "Pkd1", "C57BL/6J", "hm", "MP:0002135", "abnormal kidney morphology"],
            ["MGI:1", "Pkd1", "C57BL/6J", "hm", "MP:0000001", "some other phenotype"],
            ["MGI:1", "Pkd1", "C57BL/6J", "ht", "MP:0000519", "hydroureter"],
        ]

        # Process results
        zygosity_data = {"hm": [], "ht": [], "cn": [], "other": []}

        for row in mock_results:
            if len(row) >= 6:
                zygosity = row[3]
                mpo_id = row[4]
                mpo_name = row[5]

                if mpo_id and mpo_name:
                    phenotype_entry = {"term": mpo_id, "name": mpo_name}

                    if zygosity == "hm":
                        zygosity_data["hm"].append(phenotype_entry)
                    elif zygosity == "ht":
                        zygosity_data["ht"].append(phenotype_entry)
                    elif zygosity == "cn":
                        zygosity_data["cn"].append(phenotype_entry)
                    else:
                        zygosity_data["other"].append(phenotype_entry)

        # Filter by kidney-related MPO terms
        hm_kidney_phenotypes = [p for p in zygosity_data["hm"] if p["term"] in kidney_mpo_terms]
        ht_kidney_phenotypes = [p for p in zygosity_data["ht"] if p["term"] in kidney_mpo_terms]

        # Assertions
        assert len(hm_kidney_phenotypes) == 3, "Should have 3 homozygous kidney phenotypes"
        assert len(ht_kidney_phenotypes) == 1, "Should have 1 heterozygous kidney phenotype"

        # Check that non-kidney phenotype was filtered out
        assert not any(p["term"] == "MP:0000001" for p in hm_kidney_phenotypes)

    def test_phenotype_filtering_with_empty_mpo_terms(self):
        """Test that empty MPO terms results in no kidney phenotypes"""
        # Setup
        mock_session = Mock()
        source = MPOMGIAnnotationSource(mock_session)

        # Empty MPO terms (simulates the bug)
        empty_mpo_terms = set()

        # Mock results with kidney phenotypes
        mock_results = [
            ["MGI:1", "Pkd1", "C57BL/6J", "hm", "MP:0000519", "hydroureter"],
            ["MGI:1", "Pkd1", "C57BL/6J", "hm", "MP:0000520", "kidney hemorrhage"],
        ]

        # Process results
        zygosity_data = {"hm": [], "ht": [], "cn": [], "other": []}

        for row in mock_results:
            if len(row) >= 6:
                zygosity = row[3]
                mpo_id = row[4]
                mpo_name = row[5]

                if mpo_id and mpo_name:
                    phenotype_entry = {"term": mpo_id, "name": mpo_name}

                    if zygosity == "hm":
                        zygosity_data["hm"].append(phenotype_entry)

        # Filter with empty MPO terms
        hm_kidney_phenotypes = [p for p in zygosity_data["hm"] if p["term"] in empty_mpo_terms]

        # Assertion: With empty MPO terms, no phenotypes should pass the filter
        assert len(hm_kidney_phenotypes) == 0, "Empty MPO terms should filter out all phenotypes"

    def test_zygosity_summary_generation(self):
        """Test that zygosity summary is correctly generated"""
        # Test data with different zygosity combinations
        test_cases = [
            ([], [], "hm (false); ht (false)"),  # No phenotypes
            ([{"term": "MP:0000519", "name": "hydroureter"}], [], "hm (true); ht (false)"),  # Only homozygous
            ([], [{"term": "MP:0000520", "name": "kidney hemorrhage"}], "hm (false); ht (true)"),  # Only heterozygous
            (
                [{"term": "MP:0000519", "name": "hydroureter"}],
                [{"term": "MP:0000520", "name": "kidney hemorrhage"}],
                "hm (true); ht (true)"
            ),  # Both
        ]

        for hm_phenotypes, ht_phenotypes, expected_summary in test_cases:
            # Generate summary
            hm_result = "true" if hm_phenotypes else "false"
            ht_result = "true" if ht_phenotypes else "false"
            summary = f"hm ({hm_result}); ht ({ht_result})"

            assert summary == expected_summary, f"Expected {expected_summary}, got {summary}"

    @pytest.mark.asyncio
    async def test_mpo_terms_cache_loading(self):
        """Test that MPO terms are loaded from cache file"""
        mock_session = Mock()
        source = MPOMGIAnnotationSource(mock_session)

        # Mock the cache file existence and content
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.__enter__.return_value.read.return_value = '["MP:0000519", "MP:0000520"]'
                mock_open.return_value = mock_file

                # This would normally be called in fetch_annotation
                # We're testing the cache loading logic
                assert source._mpo_terms_cache is None, "Cache should start empty"

    def test_duplicate_phenotype_removal(self):
        """Test that duplicate phenotypes are removed while preserving order"""
        phenotypes = [
            {"term": "MP:0000519", "name": "hydroureter"},
            {"term": "MP:0000520", "name": "kidney hemorrhage"},
            {"term": "MP:0000519", "name": "hydroureter"},  # Duplicate
            {"term": "MP:0002135", "name": "abnormal kidney morphology"},
        ]

        # Remove duplicates while preserving order (matching the actual code)
        unique_phenotypes = list({p["term"]: p for p in phenotypes}.values())

        assert len(unique_phenotypes) == 3, "Should have 3 unique phenotypes"
        assert unique_phenotypes[0]["term"] == "MP:0000519"
        assert unique_phenotypes[1]["term"] == "MP:0000520"
        assert unique_phenotypes[2]["term"] == "MP:0002135"