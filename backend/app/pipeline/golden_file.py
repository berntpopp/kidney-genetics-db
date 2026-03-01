"""
Golden file validation framework for pipeline data parity.

Provides functions to export, compare, and report on gene annotation snapshots.
Used during source migrations to verify that bulk-download approaches produce
identical core scientific values to the old API-based approach.

Usage:
    from app.pipeline.golden_file import (
        export_golden_snapshot,
        compare_snapshots,
        generate_parity_report,
    )

    # Before migration
    export_golden_snapshot(db, "before.json")

    # After migration
    export_golden_snapshot(db, "after.json")

    # Compare
    comparison = compare_snapshots("before.json", "after.json")
    report = generate_parity_report(comparison)
"""

import json
import math
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)

# Maximum number of individual differences shown in the parity report
_MAX_REPORT_DIFFERENCES = 50


def export_golden_snapshot(db: Session, output_path: str) -> str:
    """
    Export the gene_annotations table as a JSON snapshot grouped by
    (gene_symbol, source).

    The output structure is::

        {
            "BRCA1": {
                "gnomad": { ... annotations ... },
                "hgnc": { ... annotations ... }
            },
            "PKD1": { ... }
        }

    Args:
        db: SQLAlchemy database session.
        output_path: Filesystem path where the JSON snapshot will be written.

    Returns:
        The resolved output path (as a string).
    """
    query = text(
        "SELECT g.approved_symbol, ga.source, ga.annotations "
        "FROM gene_annotations ga "
        "JOIN genes g ON g.id = ga.gene_id "
        "ORDER BY g.approved_symbol, ga.source"
    )
    rows = db.execute(query).fetchall()

    snapshot: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol, source, annotations = row[0], row[1], row[2]
        if symbol not in snapshot:
            snapshot[symbol] = {}
        snapshot[symbol][source] = annotations

    resolved = str(Path(output_path).resolve())
    Path(resolved).parent.mkdir(parents=True, exist_ok=True)
    with open(resolved, "w") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True, default=str)

    logger.sync_info(
        "Golden snapshot exported",
        output_path=resolved,
        gene_count=len(snapshot),
        total_rows=len(rows),
    )
    return resolved


def compare_snapshots(
    before_path: str,
    after_path: str,
    float_tolerance: float = 1e-6,
) -> dict[str, Any]:
    """
    Diff two golden-file snapshots and return a structured comparison.

    Compares core annotation values per gene per source using recursive
    dict diffing.  Floats are compared with ``math.isclose`` using
    *float_tolerance* as both ``rel_tol`` and ``abs_tol``.  Lists are
    compared by sorted string representation (order-independent).

    Args:
        before_path: Path to the *before* snapshot JSON.
        after_path: Path to the *after* snapshot JSON.
        float_tolerance: Tolerance for float comparison (default 1e-6).

    Returns:
        A dict with keys ``total_differences``, ``missing_genes``,
        ``new_genes``, and ``differences`` (list of per-field diffs).
    """
    with open(before_path) as f:
        before: dict[str, dict[str, Any]] = json.load(f)
    with open(after_path) as f:
        after: dict[str, dict[str, Any]] = json.load(f)

    before_genes = set(before.keys())
    after_genes = set(after.keys())

    missing_genes = sorted(before_genes - after_genes)
    new_genes = sorted(after_genes - before_genes)

    differences: list[dict[str, Any]] = []

    # Compare genes present in both snapshots
    common_genes = sorted(before_genes & after_genes)
    for gene in common_genes:
        before_sources = before[gene]
        after_sources = after[gene]

        all_sources = sorted(
            set(before_sources.keys()) | set(after_sources.keys())
        )
        for source in all_sources:
            if source not in before_sources:
                differences.append(
                    {
                        "gene": gene,
                        "source": source,
                        "field": "<entire source>",
                        "before": None,
                        "after": after_sources[source],
                    }
                )
                continue
            if source not in after_sources:
                differences.append(
                    {
                        "gene": gene,
                        "source": source,
                        "field": "<entire source>",
                        "before": before_sources[source],
                        "after": None,
                    }
                )
                continue

            _diff_values(
                before_sources[source],
                after_sources[source],
                gene=gene,
                source=source,
                path="",
                float_tolerance=float_tolerance,
                out=differences,
            )

    total = len(differences) + len(missing_genes) + len(new_genes)

    return {
        "total_differences": total,
        "missing_genes": missing_genes,
        "new_genes": new_genes,
        "differences": differences,
    }


def generate_parity_report(comparison: dict[str, Any]) -> str:
    """
    Generate a human-readable markdown parity report.

    The report is capped at 50 individual difference rows for readability.

    Args:
        comparison: The dict returned by :func:`compare_snapshots`.

    Returns:
        A markdown-formatted string.
    """
    total = comparison["total_differences"]
    missing = comparison["missing_genes"]
    new = comparison["new_genes"]
    diffs = comparison["differences"]

    verdict = "PASS" if total == 0 else "FAIL"

    lines: list[str] = []
    lines.append("# Golden File Parity Report")
    lines.append("")
    lines.append(f"**Verdict:** {verdict}")
    lines.append(f"**Total differences:** {total}")
    lines.append("")

    # Missing genes
    if missing:
        lines.append("## Missing Genes (in before, not in after)")
        lines.append("")
        for g in missing:
            lines.append(f"- {g}")
        lines.append("")

    # New genes
    if new:
        lines.append("## New Genes (in after, not in before)")
        lines.append("")
        for g in new:
            lines.append(f"- {g}")
        lines.append("")

    # Value differences
    if diffs:
        lines.append("## Value Differences")
        lines.append("")
        lines.append("| Gene | Source | Field | Before | After |")
        lines.append("|------|--------|-------|--------|-------|")

        shown = diffs[:_MAX_REPORT_DIFFERENCES]
        for d in shown:
            before_val = _fmt(d["before"])
            after_val = _fmt(d["after"])
            lines.append(
                f"| {d['gene']} | {d['source']} | {d['field']} "
                f"| {before_val} | {after_val} |"
            )

        if len(diffs) > _MAX_REPORT_DIFFERENCES:
            remaining = len(diffs) - _MAX_REPORT_DIFFERENCES
            lines.append("")
            lines.append(
                f"... and {remaining} more differences "
                f"(truncated at {_MAX_REPORT_DIFFERENCES})"
            )
        lines.append("")

    if total == 0:
        lines.append("No differences found -- 0 differences. All values match.")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _fmt(value: Any) -> str:
    """Format a value for display in the markdown report table."""
    if value is None:
        return "(none)"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, dict | list):
        raw = json.dumps(value, sort_keys=True, default=str)
        if len(raw) > 60:
            return raw[:57] + "..."
        return raw
    return str(value)


def _diff_values(
    before: Any,
    after: Any,
    *,
    gene: str,
    source: str,
    path: str,
    float_tolerance: float,
    out: list[dict[str, Any]],
) -> None:
    """Recursively diff two annotation values, appending diffs to *out*."""
    if isinstance(before, dict) and isinstance(after, dict):
        all_keys = sorted(set(before.keys()) | set(after.keys()))
        for key in all_keys:
            child_path = f"{path}.{key}" if path else key
            if key not in before:
                out.append(
                    {
                        "gene": gene,
                        "source": source,
                        "field": child_path,
                        "before": None,
                        "after": after[key],
                    }
                )
            elif key not in after:
                out.append(
                    {
                        "gene": gene,
                        "source": source,
                        "field": child_path,
                        "before": before[key],
                        "after": None,
                    }
                )
            else:
                _diff_values(
                    before[key],
                    after[key],
                    gene=gene,
                    source=source,
                    path=child_path,
                    float_tolerance=float_tolerance,
                    out=out,
                )
        return

    if isinstance(before, list) and isinstance(after, list):
        # Order-independent comparison via sorted string representation
        before_sorted = sorted(str(x) for x in before)
        after_sorted = sorted(str(x) for x in after)
        if before_sorted != after_sorted:
            out.append(
                {
                    "gene": gene,
                    "source": source,
                    "field": path or "<root>",
                    "before": before,
                    "after": after,
                }
            )
        return

    if isinstance(before, int | float) and isinstance(after, int | float):
        if not math.isclose(
            float(before),
            float(after),
            rel_tol=float_tolerance,
            abs_tol=float_tolerance,
        ):
            out.append(
                {
                    "gene": gene,
                    "source": source,
                    "field": path or "<root>",
                    "before": before,
                    "after": after,
                }
            )
        return

    # Fall-through: string / bool / None -- exact equality
    if before != after:
        out.append(
            {
                "gene": gene,
                "source": source,
                "field": path or "<root>",
                "before": before,
                "after": after,
            }
        )
