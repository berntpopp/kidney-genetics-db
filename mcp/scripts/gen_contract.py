#!/usr/bin/env python3
"""Generate the MCP API contract package from the committed OpenAPI snapshot.

Reads ``contract/openapi.snapshot.json`` (relative to the ``mcp/`` package root)
and writes three deterministic, idempotent modules into
``src/kidney_genetics_mcp/contract/``:

- ``_generated_paths.py`` — named path-template constants (UPPER_SNAKE) for the
  *exposed* read-only GET routes the MCP tools consume, plus ``ALL_PATHS``.
- ``_generated_enums.py`` — gene filter / sort vocabularies (tier, group, sort
  fields) extracted from the OpenAPI parameter descriptions, plus the evidence
  and annotation source name lists from the design spec, emitted as
  :class:`typing.Literal` aliases plus value tuples.
- ``_generated_models.py`` — pydantic response models via datamodel-code-generator
  (best-effort; the KGDB API is JSON:API-shaped with ``dict`` payloads, so this
  is a thin convenience layer — downstream tools tolerate dict payloads).

The script is deterministic (sorted/curated keys) and idempotent: running it
twice on the same snapshot produces byte-identical output. Do NOT hand-edit the
generated files; regenerate via ``make contract`` instead.

Usage::

    uv run python scripts/gen_contract.py
    uv run python scripts/gen_contract.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_SNAPSHOT = _ROOT / "contract" / "openapi.snapshot.json"
_OUT_DIR = _ROOT / "src" / "kidney_genetics_mcp" / "contract"
_GENERATED_FILENAMES = (
    "_generated_paths.py",
    "_generated_enums.py",
    "_generated_models.py",
)

# ---------------------------------------------------------------------------
# Exposed read-only path allowlist (mirrors the MCP tool catalog, spec §4).
#
# Only these GET routes are surfaced by the MCP. The full backend OpenAPI
# carries admin/auth/pipeline/staging/network-write surfaces that are NEVER
# exposed; we curate the path constants here rather than emitting all of them
# so the generated module is itself a readable contract of what the MCP touches.
#
# NOTE: ``/api/genes/resolve`` is added by Wave 1b (backend resolver endpoint)
# and is therefore NOT yet present in the snapshot. It is included here as a
# constant anyway so Wave 2 tools can reference it; the contract-drift test
# tolerates this until the backend endpoint lands.
# ---------------------------------------------------------------------------

_RESOLVE_PATH = "/api/genes/resolve"  # Wave 1b — not yet in the OpenAPI snapshot

_EXPOSED_PATHS: tuple[str, ...] = (
    # genes
    "/api/genes/",
    _RESOLVE_PATH,
    "/api/genes/{gene_symbol}",
    "/api/genes/{gene_symbol}/evidence",
    # annotations
    "/api/annotations/genes/{gene_id}/annotations",
    "/api/annotations/genes/{gene_id}/annotations/summary",
    "/api/annotations/sources",
    # statistics
    "/api/statistics/summary",
    # datasources
    "/api/datasources/",
    # releases
    "/api/releases/",
)

# ---------------------------------------------------------------------------
# Source name vocabularies (spec §4 — the 17 KGDB sources).
#
# These are NOT enumerated in the OpenAPI (they live in the AnnotationSource
# registry / DB rows), so they are hard-coded from the design spec. Update here
# if the source roster changes; the contract-drift test does not (cannot) check
# these against the snapshot.
# ---------------------------------------------------------------------------

_EVIDENCE_SOURCES: list[str] = [
    "PanelApp",
    "HPO",
    "ClinGen",
    "GenCC",
    "PubTator",
    "DiagnosticPanels",
    "Literature",
]

_ANNOTATION_SOURCES: list[str] = [
    "hgnc",
    "gnomad",
    "clinvar",
    "ensembl",
    "uniprot",
    "gtex",
    "mpo_mgi",
    "string_ppi",
    "descartes",
    "hpo",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _const_name(path: str) -> str:
    """Derive a stable UPPER_SNAKE constant name from a path template.

    The ``/api`` prefix is dropped; ``{param}`` placeholders become ``BY_PARAM``;
    other non-alphanumeric runs collapse to a single underscore.
    """
    name = path
    if name.startswith("/api/"):
        name = name[len("/api/") :]
    name = name.strip("/")
    if not name:
        return "ROOT"
    name = re.sub(r"\{([^}]+)\}", r"by_\1", name)
    name = re.sub(r"[^0-9A-Za-z]+", "_", name)
    name = name.strip("_")
    return name.upper()


def _extract_described_enum(description: str | None) -> list[str] | None:
    """Pull a parenthesised, comma-separated vocabulary from a param description.

    KGDB documents the gene ``tier`` / ``group`` allowed values inline, e.g.
    ``"Filter by evidence tier (comprehensive_support, multi_source_support, ...)"``.
    Returns the listed tokens, or ``None`` when no parenthesised list is present.
    """
    if not description:
        return None
    match = re.search(r"\(([^)]+)\)", description)
    if not match:
        return None
    inner = match.group(1)
    parts = [p.strip() for p in inner.split(",")]
    # Keep only bare identifier-like tokens (drop "e.g." style prose fragments).
    tokens = [p for p in parts if re.fullmatch(r"[A-Za-z0-9_]+", p)]
    return tokens or None


def _genes_get_op(spec: dict[str, Any]) -> dict[str, Any]:
    """Return the ``GET /api/genes/`` operation object."""
    op = spec.get("paths", {}).get("/api/genes/", {}).get("get", {})
    return op if isinstance(op, dict) else {}


def _param_description(op: dict[str, Any], name: str) -> str | None:
    """Return the description of parameter *name* on operation *op*."""
    for param in op.get("parameters", []) or []:
        if param.get("name") == name:
            schema = param.get("schema", {})
            desc = param.get("description") or schema.get("description")
            return str(desc) if desc is not None else None
    return None


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

_GEN_HEADER = (
    "# GENERATED by scripts/gen_contract.py — do not hand-edit\n"
    '"""{title}\n\n'
    "GENERATED FILE — do not hand-edit.\n"
    "Regenerate with ``scripts/gen_contract.py`` (``make contract``) from\n"
    "``contract/openapi.snapshot.json``.\n"
    '"""\n'
    "from __future__ import annotations\n"
)


def _render_paths(paths: tuple[str, ...]) -> str:
    title = "Exposed read-only API path-template constants."
    lines = [_GEN_HEADER.format(title=title), ""]
    consts: list[str] = []
    for path in paths:
        const = _const_name(path)
        consts.append(const)
        comment = ""
        if path == _RESOLVE_PATH:
            comment = "  # Wave 1b — not yet in OpenAPI snapshot"
        lines.append(f'{const} = "{path}"{comment}')
    lines.append("")
    lines.append("ALL_PATHS: tuple[str, ...] = (")
    for const in consts:
        lines.append(f"    {const},")
    lines.append(")")
    lines.append("")
    return "\n".join(lines)


def _render_enums(
    described: list[tuple[str, list[str]]],
    source_lists: list[tuple[str, list[str], str]],
) -> str:
    title = "Gene filter / sort vocabularies + source name lists."
    lines = [_GEN_HEADER.format(title=title), "", "from typing import Literal", ""]

    def _emit(alias: str, values_name: str, values: list[str]) -> None:
        literal_args = ", ".join(json.dumps(v) for v in values)
        lines.append(f"{alias} = Literal[{literal_args}]")
        tuple_args = ", ".join(json.dumps(v) for v in values)
        if len(values) == 1:
            tuple_args += ","
        lines.append(f"{values_name}: tuple[str, ...] = ({tuple_args})")
        lines.append("")

    if described:
        lines.append("# --- gene filter / sort vocabularies (from OpenAPI) ---")
        lines.append("")
        for alias, values in described:
            values_name = re.sub(r"(?<!^)(?=[A-Z])", "_", alias).upper() + "_VALUES"
            _emit(alias, values_name, values)

    lines.append("# --- source name lists (hard-coded from design spec §4) ---")
    lines.append("")
    for alias, values, comment in source_lists:
        lines.append(f"# {comment}")
        values_name = re.sub(r"(?<!^)(?=[A-Z])", "_", alias).upper() + "_VALUES"
        _emit(alias, values_name, values)

    return "\n".join(lines)


def _render_models_fallback() -> str:
    """Render a stub ``_generated_models.py`` when codegen is unavailable.

    The KGDB API returns JSON:API ``dict`` payloads; downstream tools tolerate
    raw dicts, so a missing typed-model layer is non-fatal.
    """
    title = "Pydantic response models (datamodel-code-generator was unavailable)."
    return (
        _GEN_HEADER.format(title=title)
        + "\n"
        + "# datamodel-code-generator did not run; the KGDB API is JSON:API-shaped\n"
        + "# (dict payloads) and downstream tools tolerate raw dicts. Regenerate\n"
        + "# with `make contract` once codegen is available.\n"
    )


def _run_model_codegen(models_out: Path) -> bool:
    """Generate ``_generated_models.py`` via datamodel-code-generator.

    Returns ``True`` on success, ``False`` if the tool is unavailable or fails
    (caller writes a fallback stub in that case).
    """
    dmcg = shutil.which("datamodel-codegen")
    if dmcg is None:
        return False
    cmd = [
        dmcg,
        "--input",
        str(_SNAPSHOT),
        "--input-file-type",
        "openapi",
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        "3.11",
        "--use-standard-collections",
        "--enum-field-as-literal",
        "all",
        "--use-annotated",
        "--disable-timestamp",
        "--output",
        str(models_out),
    ]
    try:
        subprocess.run(cmd, check=True)  # noqa: S603 — fixed args, pinned dev dep
    except (subprocess.CalledProcessError, OSError):
        return False
    # Prepend the generated-file marker so all contract modules carry it.
    body = models_out.read_text(encoding="utf-8")
    marker = "# GENERATED by scripts/gen_contract.py — do not hand-edit\n"
    if not body.startswith(marker):
        models_out.write_text(marker + body, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _output_paths(output_dir: Path) -> tuple[Path, Path, Path]:
    """Return the three generated artifact paths under ``output_dir``."""
    return (
        output_dir / _GENERATED_FILENAMES[0],
        output_dir / _GENERATED_FILENAMES[1],
        output_dir / _GENERATED_FILENAMES[2],
    )


def generate_contract(output_dir: Path) -> tuple[Path, Path, Path]:
    """Render all contract artifacts into ``output_dir`` and return their paths."""
    spec = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))
    paths_out, enums_out, models_out = _output_paths(output_dir)

    # Paths: the curated exposed allowlist.
    output_dir.mkdir(parents=True, exist_ok=True)
    paths_out.write_text(_render_paths(_EXPOSED_PATHS), encoding="utf-8")

    # Enums: tier/group from descriptions, sort fields from the gene field map.
    genes_op = _genes_get_op(spec)
    described: list[tuple[str, list[str]]] = []

    tier_vals = _extract_described_enum(_param_description(genes_op, "filter[tier]"))
    if tier_vals:
        described.append(("EvidenceTier", tier_vals))
    group_vals = _extract_described_enum(_param_description(genes_op, "filter[group]"))
    if group_vals:
        described.append(("EvidenceGroup", group_vals))

    # Sort fields: the backend's accepted sort columns (genes endpoint field map).
    # Not enumerated in the OpenAPI parameter schema, so curated here to match
    # backend/app/api/endpoints/genes.py.
    sort_fields = [
        "id",
        "symbol",
        "approved_symbol",
        "hgnc_id",
        "score",
        "evidence_score",
        "count",
        "evidence_count",
        "created_at",
        "updated_at",
        "evidence_tier",
        "evidence_group",
    ]
    described.append(("GeneSortField", sort_fields))

    source_lists = [
        (
            "EvidenceSource",
            _EVIDENCE_SOURCES,
            "7 scored evidence sources (kgdb_get_gene_evidence)",
        ),
        (
            "AnnotationSource",
            _ANNOTATION_SOURCES,
            "10 descriptive annotation sources (kgdb_get_gene_annotations)",
        ),
    ]
    enums_out.write_text(_render_enums(described, source_lists), encoding="utf-8")

    # Models: best-effort via datamodel-code-generator.
    models_ok = _run_model_codegen(models_out)
    if not models_ok:
        models_out.write_text(_render_models_fallback(), encoding="utf-8")

    # Normalise formatting so output is byte-identical across runs / CI.
    ruff = shutil.which("ruff")
    if ruff is not None:
        subprocess.run(  # noqa: S603 — fixed args, pinned dev dependency
            [
                ruff,
                "format",
                "--quiet",
                str(paths_out),
                str(enums_out),
                str(models_out),
            ],
            check=True,
        )
    return paths_out, enums_out, models_out


def verify_contract(committed_dir: Path = _OUT_DIR) -> list[Path]:
    """Return committed artifact paths that differ from fresh temporary output."""
    with tempfile.TemporaryDirectory(prefix="kgdb-contract-check-") as temp_dir:
        generated = generate_contract(Path(temp_dir))
        return [
            committed_dir / path.name
            for path in generated
            if not (committed_dir / path.name).is_file()
            or (committed_dir / path.name).read_bytes() != path.read_bytes()
        ]


def _print_generation_summary(generated: tuple[Path, Path, Path]) -> None:
    """Print the explicit regeneration result for a developer-run command."""
    paths_out, enums_out, models_out = generated
    print(f"wrote {paths_out.relative_to(_ROOT)} ({len(_EXPOSED_PATHS)} paths)")
    print(f"wrote {enums_out.relative_to(_ROOT)}")
    print(f"wrote {models_out.relative_to(_ROOT)}")


def main(argv: Sequence[str] | None = None) -> int:
    """Generate artifacts, or verify them without writing to the source tree."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare fresh temporary output to committed artifacts without writes",
    )
    args = parser.parse_args(argv)

    if args.check:
        stale_paths = verify_contract()
        if stale_paths:
            print("Generated contract artifacts are stale:", file=sys.stderr)
            for path in stale_paths:
                print(f"  {path.relative_to(_ROOT)}", file=sys.stderr)
            return 1
        print("Generated contract artifacts are current.")
        return 0

    _print_generation_summary(generate_contract(_OUT_DIR))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
