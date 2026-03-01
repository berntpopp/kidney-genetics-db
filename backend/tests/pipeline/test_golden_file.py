"""
Tests for the golden file validation framework.

This module tests the snapshot export, comparison, and reporting functions
used to validate pipeline data parity during source migrations.
"""

import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation
from app.pipeline.golden_file import (
    compare_snapshots,
    export_golden_snapshot,
    generate_parity_report,
)


def _unique_hgnc_id() -> str:
    """Generate a unique HGNC ID for testing."""
    return f"HGNC:TEST{uuid.uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# Snapshot comparison tests (pure functions, no DB required)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompareIdenticalSnapshots:
    """Zero diffs for identical data."""

    def test_compare_identical_snapshots(self, tmp_path: Path) -> None:
        data = {
            "BRCA1": {
                "gnomad": {"pli": 0.99, "oe_lof": 0.12},
                "hgnc": {"ncbi_gene_id": "672"},
            },
            "PKD1": {
                "gnomad": {"pli": 0.85, "oe_lof": 0.25},
            },
        }
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        before.write_text(json.dumps(data))
        after.write_text(json.dumps(data))

        result = compare_snapshots(str(before), str(after))

        assert result["total_differences"] == 0
        assert result["missing_genes"] == []
        assert result["new_genes"] == []
        assert result["differences"] == []


@pytest.mark.unit
class TestCompareDetectsValueChange:
    """Catches changed annotation values."""

    def test_compare_detects_value_change(self, tmp_path: Path) -> None:
        before_data = {
            "BRCA1": {
                "gnomad": {"pli": 0.99, "oe_lof": 0.12},
            },
        }
        after_data = {
            "BRCA1": {
                "gnomad": {"pli": 0.85, "oe_lof": 0.12},
            },
        }
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        before.write_text(json.dumps(before_data))
        after.write_text(json.dumps(after_data))

        result = compare_snapshots(str(before), str(after))

        assert result["total_differences"] == 1
        assert len(result["differences"]) == 1
        diff = result["differences"][0]
        assert diff["gene"] == "BRCA1"
        assert diff["source"] == "gnomad"
        assert diff["field"] == "pli"
        assert diff["before"] == 0.99
        assert diff["after"] == 0.85


@pytest.mark.unit
class TestCompareFloatTolerance:
    """Floats within tolerance treated as equal."""

    def test_compare_float_tolerance(self, tmp_path: Path) -> None:
        before_data = {
            "BRCA1": {
                "gnomad": {"pli": 0.990000001},
            },
        }
        after_data = {
            "BRCA1": {
                "gnomad": {"pli": 0.990000002},
            },
        }
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        before.write_text(json.dumps(before_data))
        after.write_text(json.dumps(after_data))

        # Default tolerance (1e-6) should treat these as equal
        result = compare_snapshots(str(before), str(after))
        assert result["total_differences"] == 0

        # Tight tolerance should catch the difference
        result_strict = compare_snapshots(
            str(before), str(after), float_tolerance=1e-12
        )
        assert result_strict["total_differences"] == 1


@pytest.mark.unit
class TestCompareDetectsMissingGene:
    """Genes in before but not after are flagged."""

    def test_compare_detects_missing_gene(self, tmp_path: Path) -> None:
        before_data = {
            "BRCA1": {"gnomad": {"pli": 0.99}},
            "PKD1": {"gnomad": {"pli": 0.85}},
        }
        after_data = {
            "BRCA1": {"gnomad": {"pli": 0.99}},
        }
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        before.write_text(json.dumps(before_data))
        after.write_text(json.dumps(after_data))

        result = compare_snapshots(str(before), str(after))

        assert "PKD1" in result["missing_genes"]
        assert result["total_differences"] >= 1


@pytest.mark.unit
class TestCompareDetectsNewGene:
    """Genes in after but not before are flagged."""

    def test_compare_detects_new_gene(self, tmp_path: Path) -> None:
        before_data = {
            "BRCA1": {"gnomad": {"pli": 0.99}},
        }
        after_data = {
            "BRCA1": {"gnomad": {"pli": 0.99}},
            "TP53": {"gnomad": {"pli": 0.95}},
        }
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        before.write_text(json.dumps(before_data))
        after.write_text(json.dumps(after_data))

        result = compare_snapshots(str(before), str(after))

        assert "TP53" in result["new_genes"]
        assert result["total_differences"] >= 1


# ---------------------------------------------------------------------------
# Nested diff tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompareNestedDiff:
    """Recursive dict diffing for nested JSONB data."""

    def test_nested_dict_change(self, tmp_path: Path) -> None:
        before_data = {
            "BRCA1": {
                "hgnc": {
                    "mane_select": {
                        "ensembl_transcript_id": "ENST00000000001",
                        "refseq_transcript_id": "NM_000001.1",
                    }
                }
            },
        }
        after_data = {
            "BRCA1": {
                "hgnc": {
                    "mane_select": {
                        "ensembl_transcript_id": "ENST00000000002",
                        "refseq_transcript_id": "NM_000001.1",
                    }
                }
            },
        }
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        before.write_text(json.dumps(before_data))
        after.write_text(json.dumps(after_data))

        result = compare_snapshots(str(before), str(after))

        assert result["total_differences"] == 1
        diff = result["differences"][0]
        assert "ensembl_transcript_id" in diff["field"]

    def test_list_order_independent(self, tmp_path: Path) -> None:
        before_data = {
            "BRCA1": {
                "hgnc": {"pubmed_ids": ["111", "222", "333"]},
            },
        }
        after_data = {
            "BRCA1": {
                "hgnc": {"pubmed_ids": ["333", "111", "222"]},
            },
        }
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        before.write_text(json.dumps(before_data))
        after.write_text(json.dumps(after_data))

        result = compare_snapshots(str(before), str(after))
        assert result["total_differences"] == 0

    def test_list_content_change(self, tmp_path: Path) -> None:
        before_data = {
            "BRCA1": {
                "hgnc": {"pubmed_ids": ["111", "222"]},
            },
        }
        after_data = {
            "BRCA1": {
                "hgnc": {"pubmed_ids": ["111", "333"]},
            },
        }
        before = tmp_path / "before.json"
        after = tmp_path / "after.json"
        before.write_text(json.dumps(before_data))
        after.write_text(json.dumps(after_data))

        result = compare_snapshots(str(before), str(after))
        assert result["total_differences"] == 1


# ---------------------------------------------------------------------------
# Report generation test
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateParityReport:
    """Human-readable markdown report generation."""

    def test_report_no_differences(self) -> None:
        comparison = {
            "total_differences": 0,
            "missing_genes": [],
            "new_genes": [],
            "differences": [],
        }
        report = generate_parity_report(comparison)
        assert "0 difference" in report.lower()
        assert "PASS" in report or "pass" in report.lower()

    def test_report_with_differences(self) -> None:
        comparison = {
            "total_differences": 2,
            "missing_genes": ["PKD1"],
            "new_genes": [],
            "differences": [
                {
                    "gene": "BRCA1",
                    "source": "gnomad",
                    "field": "pli",
                    "before": 0.99,
                    "after": 0.85,
                },
            ],
        }
        report = generate_parity_report(comparison)
        assert "BRCA1" in report
        assert "PKD1" in report
        assert "gnomad" in report
        assert "FAIL" in report or "fail" in report.lower()

    def test_report_caps_at_50(self) -> None:
        differences = [
            {
                "gene": f"GENE{i}",
                "source": "gnomad",
                "field": "pli",
                "before": 0.1,
                "after": 0.2,
            }
            for i in range(100)
        ]
        comparison = {
            "total_differences": 100,
            "missing_genes": [],
            "new_genes": [],
            "differences": differences,
        }
        report = generate_parity_report(comparison)
        # Should mention truncation
        assert "50" in report or "truncated" in report.lower() or "..." in report


# ---------------------------------------------------------------------------
# Database export test (requires db_session fixture)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestExportCreatesFile:
    """Export produces valid JSON from the database."""

    def test_export_creates_file(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        # Insert test gene
        gene = Gene(
            approved_symbol="GOLDEN_TEST_A",
            hgnc_id=_unique_hgnc_id(),
        )
        db_session.add(gene)
        db_session.flush()

        # Insert test annotation
        annotation = GeneAnnotation(
            gene_id=gene.id,
            source="gnomad",
            version="v4.0",
            annotations={"pli": 0.99, "oe_lof": 0.12},
        )
        db_session.add(annotation)
        db_session.flush()

        output_path = str(tmp_path / "snapshot.json")
        export_golden_snapshot(db_session, output_path)

        # File must exist and contain valid JSON
        assert Path(output_path).exists()
        with open(output_path) as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "GOLDEN_TEST_A" in data
        assert "gnomad" in data["GOLDEN_TEST_A"]
        assert data["GOLDEN_TEST_A"]["gnomad"]["pli"] == 0.99
