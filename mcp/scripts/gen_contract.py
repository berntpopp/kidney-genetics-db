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
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_SNAPSHOT = _ROOT / "contract" / "openapi.snapshot.json"
_OUT_DIR = _ROOT / "src" / "kidney_genetics_mcp" / "contract"
_PATHS_OUT = _OUT_DIR / "_generated_paths.py"
_ENUMS_OUT = _OUT_DIR / "_generated_enums.py"
_MODELS_OUT = _OUT_DIR / "_generated_models.py"

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


def _run_model_codegen() -> bool:
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
        str(_MODELS_OUT),
    ]
    try:
        subprocess.run(cmd, check=True)  # noqa: S603 — fixed args, pinned dev dep
    except (subprocess.CalledProcessError, OSError):
        return False
    # Prepend the generated-file marker so all contract modules carry it.
    body = _MODELS_OUT.read_text(encoding="utf-8")
    marker = "# GENERATED by scripts/gen_contract.py — do not hand-edit\n"
    if not body.startswith(marker):
        _MODELS_OUT.write_text(marker + body, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Generate the contract modules from the snapshot."""
    spec = json.loads(_SNAPSHOT.read_text(encoding="utf-8"))

    # Paths: the curated exposed allowlist.
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    _PATHS_OUT.write_text(_render_paths(_EXPOSED_PATHS), encoding="utf-8")

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
    _ENUMS_OUT.write_text(_render_enums(described, source_lists), encoding="utf-8")

    # Models: best-effort via datamodel-code-generator.
    models_ok = _run_model_codegen()
    if not models_ok:
        _MODELS_OUT.write_text(_render_models_fallback(), encoding="utf-8")

    # Normalise formatting so output is byte-identical across runs / CI.
    ruff = shutil.which("ruff")
    if ruff is not None:
        subprocess.run(  # noqa: S603 — fixed args, pinned dev dependency
            [
                ruff,
                "format",
                "--quiet",
                str(_PATHS_OUT),
                str(_ENUMS_OUT),
                str(_MODELS_OUT),
            ],
            check=True,
        )

    print(f"wrote {_PATHS_OUT.relative_to(_ROOT)} ({len(_EXPOSED_PATHS)} paths)")
    print(
        f"wrote {_ENUMS_OUT.relative_to(_ROOT)} "
        f"({len(described)} described enums, {len(source_lists)} source lists)"
    )
    print(
        f"wrote {_MODELS_OUT.relative_to(_ROOT)} "
        f"({'datamodel-codegen' if models_ok else 'fallback stub'})"
    )


if __name__ == "__main__":
    main()
