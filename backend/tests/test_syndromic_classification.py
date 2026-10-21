#!/usr/bin/env python3
"""
Test syndromic classification implementation.
Verifies the fix for issue #8 and sub-category scoring.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_syndromic_classification_alport():
    """Test that Alport syndrome genes are classified as syndromic."""
    from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

    # Mock session
    session = MagicMock()
    hpo_source = HPOAnnotationSource(session)

    # Mock the descendant lookup to return test data
    hpo_source.get_classification_term_descendants = AsyncMock(
        return_value={
            "neurologic": {"HP:0000407", "HP:0001250", "HP:0001249"},  # Include hearing
            "head_neck": {"HP:0000545", "HP:0007663", "HP:0000365"},  # Include eye/ear
            "growth": {"HP:0001508", "HP:0004322"},
            "skeletal": {"HP:0002652", "HP:0000944"},
        }
    )

    # Alport syndrome phenotypes
    phenotypes = {
        "HP:0000093",  # Proteinuria (kidney)
        "HP:0000112",  # Nephropathy (kidney)
        "HP:0000407",  # Sensorineural hearing impairment (neurologic)
        "HP:0000545",  # Myopia (head_neck)
        "HP:0007663",  # Reduced visual acuity (head_neck)
    }

    result = await hpo_source._assess_syndromic_features(phenotypes)

    # Assertions
    assert result["is_syndromic"] is True, "Alport should be syndromic"
    assert result["syndromic_score"] >= 0.3, "Score should be >= 0.3"
    assert "neurologic" in result["category_scores"], "Should have neurologic score"
    assert "head_neck" in result["category_scores"], "Should have head_neck score"

    # Check sub-category scores
    assert result["category_scores"]["neurologic"] == 0.2  # 1/5 phenotypes
    assert result["category_scores"]["head_neck"] == 0.4  # 2/5 phenotypes
    assert result["syndromic_score"] == 0.6  # Total: 3/5 syndromic


@pytest.mark.asyncio
async def test_syndromic_classification_pkd():
    """Test that PKD genes are classified as isolated."""
    from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

    session = MagicMock()
    hpo_source = HPOAnnotationSource(session)

    # Mock empty syndromic matches
    hpo_source.get_classification_term_descendants = AsyncMock(
        return_value={
            "neurologic": {"HP:0000407", "HP:0001250"},
            "head_neck": {"HP:0000545", "HP:0000365"},
            "growth": {"HP:0001508"},
            "skeletal": {"HP:0002652"},
        }
    )

    # PKD phenotypes (all kidney-related)
    phenotypes = {
        "HP:0000107",  # Renal cyst
        "HP:0000113",  # Polycystic kidney dysplasia
        "HP:0000090",  # Nephronophthisis
        "HP:0003774",  # Stage 5 CKD
    }

    result = await hpo_source._assess_syndromic_features(phenotypes)

    # Assertions
    assert result["is_syndromic"] is False, "PKD should be isolated"
    assert result["syndromic_score"] == 0.0, "Score should be 0"
    assert result["category_scores"] == {}, "No category scores"
    assert result["extra_renal_categories"] == [], "No extra-renal categories"


@pytest.mark.asyncio
async def test_syndromic_classification_mixed():
    """Test mixed phenotypes with sub-category scoring."""
    from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

    session = MagicMock()
    hpo_source = HPOAnnotationSource(session)

    hpo_source.get_classification_term_descendants = AsyncMock(
        return_value={
            "growth": {"HP:0001508", "HP:0004322"},
            "skeletal": {"HP:0000924"},
            "neurologic": {"HP:0001250"},
            "head_neck": {"HP:0000545"},
        }
    )

    # Mixed phenotypes
    phenotypes = {
        "HP:0000093",  # Proteinuria (kidney)
        "HP:0001508",  # Failure to thrive (growth)
        "HP:0000924",  # Skeletal abnormality
        "HP:0001250",  # Seizures (neurologic)
        "HP:0000112",  # Nephropathy (kidney)
    }

    result = await hpo_source._assess_syndromic_features(phenotypes)

    # Assertions
    assert result["is_syndromic"] is True, "Should be syndromic (3/5 = 60%)"
    assert result["syndromic_score"] == 0.6, "Score should be 0.6"

    # Check individual category scores
    assert result["category_scores"]["growth"] == 0.2  # 1/5
    assert result["category_scores"]["skeletal"] == 0.2  # 1/5
    assert result["category_scores"]["neurologic"] == 0.2  # 1/5
    assert "head_neck" not in result["category_scores"]  # No matches

    # Check counts
    assert result["extra_renal_term_counts"]["growth"] == 1
    assert result["extra_renal_term_counts"]["skeletal"] == 1
    assert result["extra_renal_term_counts"]["neurologic"] == 1


@pytest.mark.asyncio
async def test_syndromic_classification_empty():
    """Test edge case with no phenotypes."""
    from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

    session = MagicMock()
    hpo_source = HPOAnnotationSource(session)

    # Mock descendant lookup to avoid real API calls
    hpo_source.get_classification_term_descendants = AsyncMock(
        return_value={
            "neurologic": set(),
            "head_neck": set(),
            "growth": set(),
            "skeletal": set(),
        }
    )

    result = await hpo_source._assess_syndromic_features(set())

    assert result["is_syndromic"] is False
    assert result["syndromic_score"] == 0.0
    assert result["category_scores"] == {}
    assert result["extra_renal_categories"] == []


def test_syndromic_threshold_boundary_is_inclusive():
    """9 of 30 terms extra-renal is exactly 0.3: syndromic (>=), however categories split (#254).

    Per-category rounding (4/30 -> 0.133) used to sum to 0.299 and miss the boundary.
    """
    from app.pipeline.sources.annotations.hpo import score_syndromic_features

    phenotypes = {f"HP:{i:07d}" for i in range(30)}
    terms = sorted(phenotypes)
    descendants = {
        "growth": set(terms[:1]),
        "skeletal": set(terms[1:5]),
        "head_neck": set(terms[5:9]),
    }

    at_boundary = score_syndromic_features(phenotypes, descendants)
    assert at_boundary["syndromic_score"] == 0.3
    assert at_boundary["is_syndromic"] is True

    descendants["head_neck"] = set(terms[5:8])  # 8/30 = 0.267
    assert score_syndromic_features(phenotypes, descendants)["is_syndromic"] is False


def test_term_in_two_categories_counts_once():
    """Overlapping categories share terms; each term adds to the score once (#255)."""
    from app.pipeline.sources.annotations.hpo import score_syndromic_features

    shared = "HP:0000407"  # e.g. hearing impairment: neurologic and head_neck
    phenotypes = {shared, "HP:K1", "HP:K2", "HP:K3", "HP:K4"}
    descendants = {"neurologic": {shared}, "head_neck": {shared}}

    result = score_syndromic_features(phenotypes, descendants)
    assert result["extra_renal_term_counts"] == {"neurologic": 1, "head_neck": 1}
    assert result["syndromic_score"] == 0.2  # 1/5, not 2/5
    assert result["is_syndromic"] is False


def test_syndromic_score_never_exceeds_one():
    from app.pipeline.sources.annotations.hpo import score_syndromic_features

    phenotypes = {"HP:A", "HP:B"}
    descendants = dict.fromkeys(["growth", "skeletal", "neurologic", "head_neck"], phenotypes)
    assert score_syndromic_features(phenotypes, descendants)["syndromic_score"] == 1.0


def test_syndromic_threshold_read_from_config():
    from unittest.mock import patch

    from app.core.datasource_config import get_source_parameter
    from app.pipeline.sources.annotations import hpo

    assert get_source_parameter("HPO", "syndromic_threshold") == 0.3
    phenotypes = {"HP:G1", "HP:K1", "HP:K2", "HP:K3"}  # 0.25
    descendants = {"growth": {"HP:G1"}}
    assert hpo.score_syndromic_features(phenotypes, descendants)["is_syndromic"] is False
    with patch.object(hpo, "get_source_parameter", return_value=0.2) as param:
        assert hpo.score_syndromic_features(phenotypes, descendants)["is_syndromic"] is True
    param.assert_called_with("HPO", "syndromic_threshold", 0.3)


if __name__ == "__main__":
    import asyncio

    # Run tests
    asyncio.run(test_syndromic_classification_alport())
    asyncio.run(test_syndromic_classification_pkd())
    asyncio.run(test_syndromic_classification_mixed())
    asyncio.run(test_syndromic_classification_empty())

    print("All tests passed!")
