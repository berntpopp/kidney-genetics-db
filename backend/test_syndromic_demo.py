#!/usr/bin/env python3
"""
Demonstration of the refactored syndromic classification.
Shows how sub-category scores work with real examples.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from app.pipeline.sources.annotations.hpo import HPOAnnotationSource


async def demo_syndromic_classification():
    """Demonstrate the refactored syndromic classification with sub-scores."""

    # Create HPO source with mock session
    session = MagicMock()
    hpo = HPOAnnotationSource(session)

    # Mock the descendant lookup with realistic data
    hpo.get_classification_term_descendants = AsyncMock(return_value={
        "growth": {
            "HP:0001507", "HP:0001508", "HP:0004322", "HP:0000098", "HP:0001548"
        },
        "skeletal": {
            "HP:0000924", "HP:0002652", "HP:0000944", "HP:0009121", "HP:0040068"
        },
        "neurologic": {
            "HP:0000707", "HP:0000407", "HP:0001250", "HP:0001249", "HP:0100543"
        },
        "head_neck": {
            "HP:0000152", "HP:0000478", "HP:0000545", "HP:0000365", "HP:0001999",
            "HP:0007663", "HP:0000518"
        }
    })

    print("=" * 70)
    print("SYNDROMIC CLASSIFICATION DEMONSTRATION")
    print("Showing sub-category scores (matching R implementation)")
    print("=" * 70)

    # Test Case 1: Alport Syndrome (COL4A3/4/5)
    print("\n1. ALPORT SYNDROME (COL4A3/4/5)")
    print("-" * 40)

    alport_phenotypes = {
        "HP:0000093",  # Proteinuria
        "HP:0000112",  # Nephropathy
        "HP:0000407",  # Sensorineural hearing impairment
        "HP:0000545",  # Myopia
        "HP:0007663",  # Reduced visual acuity
        "HP:0000518",  # Cataract
        "HP:0000365",  # Hearing impairment
    }

    result = await hpo._assess_syndromic_features(alport_phenotypes)

    print(f"Phenotypes: {len(alport_phenotypes)} total")
    print(f"Classification: {'SYNDROMIC' if result['is_syndromic'] else 'ISOLATED'}")
    print(f"Overall Score: {result['syndromic_score']:.3f}")
    print("\nSub-category Scores:")
    for category, score in result['category_scores'].items():
        count = result['extra_renal_term_counts'][category]
        print(f"  {category:<12}: {score:.3f} ({count} phenotypes)")

    # Test Case 2: PKD (Should be isolated)
    print("\n2. POLYCYSTIC KIDNEY DISEASE (PKD1/PKD2)")
    print("-" * 40)

    pkd_phenotypes = {
        "HP:0000107",  # Renal cyst
        "HP:0000113",  # Polycystic kidney dysplasia
        "HP:0000090",  # Nephronophthisis
        "HP:0003774",  # Stage 5 chronic kidney disease
    }

    result = await hpo._assess_syndromic_features(pkd_phenotypes)

    print(f"Phenotypes: {len(pkd_phenotypes)} total")
    print(f"Classification: {'SYNDROMIC' if result['is_syndromic'] else 'ISOLATED'}")
    print(f"Overall Score: {result['syndromic_score']:.3f}")
    if result['category_scores']:
        print("\nSub-category Scores:")
        for category, score in result['category_scores'].items():
            count = result['extra_renal_term_counts'][category]
            print(f"  {category:<12}: {score:.3f} ({count} phenotypes)")
    else:
        print("No syndromic features detected")

    # Test Case 3: Mixed syndrome
    print("\n3. MIXED SYNDROME EXAMPLE")
    print("-" * 40)

    mixed_phenotypes = {
        # Kidney
        "HP:0000093",  # Proteinuria
        "HP:0000112",  # Nephropathy
        # Growth
        "HP:0001508",  # Failure to thrive
        "HP:0004322",  # Short stature
        # Skeletal
        "HP:0000924",  # Skeletal abnormality
        # Neurologic
        "HP:0001250",  # Seizures
        "HP:0000407",  # Hearing loss
    }

    result = await hpo._assess_syndromic_features(mixed_phenotypes)

    print(f"Phenotypes: {len(mixed_phenotypes)} total")
    print(f"Classification: {'SYNDROMIC' if result['is_syndromic'] else 'ISOLATED'}")
    print(f"Overall Score: {result['syndromic_score']:.3f}")
    print("\nSub-category Scores:")
    for category, score in result['category_scores'].items():
        count = result['extra_renal_term_counts'][category]
        print(f"  {category:<12}: {score:.3f} ({count} phenotypes)")

    # Show JSON output format
    print("\n" + "=" * 70)
    print("JSON OUTPUT FORMAT (as stored in database):")
    print("-" * 40)

    example_output = {
        "classification": {
            "syndromic_assessment": {
                "is_syndromic": result["is_syndromic"],
                "syndromic_score": result["syndromic_score"],
                "category_scores": result["category_scores"],
                "extra_renal_categories": result["extra_renal_categories"],
                "extra_renal_term_counts": result["extra_renal_term_counts"]
            }
        }
    }

    print(json.dumps(example_output, indent=2))

    print("\n" + "=" * 70)
    print("KEY IMPROVEMENTS:")
    print("1. ✓ Fixed: Now checks ALL phenotypes (not filtering kidney)")
    print("2. ✓ Added: Sub-category scores for each system")
    print("3. ✓ Matches: R implementation logic")
    print("4. ✓ API: Sub-scores included in response")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_syndromic_classification())