"""Annotation service: descriptive annotations + fast constraint summary.

Backs ``kgdb_get_gene_annotations`` and ``kgdb_get_constraint_summary``. Both
KGDB annotation endpoints key by the *numeric* gene database id (not the symbol),
which the caller obtains from ``kgdb_resolve_gene`` / ``kgdb_search_genes``.

The annotations endpoint returns a per-source map of records whose ``data`` is a
free-form JSONB blob that varies wildly by source (and can be very large). The
``response_mode`` ladder therefore controls *how much of each record's ``data``*
is surfaced rather than picking a fixed field set:

- ``minimal`` — source names + the version of each record only (no ``data``).
- ``compact`` — a small per-record summary (version, updated_at, a handful of
  scalar/summary fields lifted out of ``data``).
- ``standard`` — the same summary plus the full ``data`` blob.
- ``full`` — every field of every record verbatim (version, data, metadata,
  updated_at).

After projection the payload is trimmed to the response-mode character budget
with :func:`~kidney_genetics_mcp.services.shaping.apply_budget`.
"""

from __future__ import annotations

from typing import Any

from ..client.api_client import ApiClient
from ..config import Settings
from ..contract import ANNOTATION_SOURCE_VALUES
from ..contract._generated_paths import (
    ANNOTATIONS_GENES_BY_GENE_ID_ANNOTATIONS,
    ANNOTATIONS_GENES_BY_GENE_ID_ANNOTATIONS_SUMMARY,
)
from .errors import McpToolError
from .shaping import apply_budget

_HARD_CAP = 80_000

#: Scalar keys lifted out of a record's ``data`` blob to build the ``compact``
#: per-record summary. These are the small, high-signal fields shared across many
#: sources; a key absent from a given ``data`` blob is simply skipped. The
#: nested ``summary`` sub-object (if present) is always carried in compact mode.
_DATA_SUMMARY_KEYS: tuple[str, ...] = (
    "symbol",
    "name",
    "accession",
    "ppi_score",
    "ppi_degree",
    "ppi_percentile",
    "pli",
    "oe_lof",
    "clinvar_total",
    "pathogenic_count",
    "ensembl_gene_id",
    "ncbi_gene_id",
    "mane_select_transcript",
)


def _summarize_data(data: Any) -> dict[str, Any]:
    """Lift a small set of high-signal scalar fields out of a ``data`` blob.

    Args:
        data: The record's ``data`` JSONB value (usually a dict, but a source
            may store a list/scalar — those yield an empty summary).

    Returns:
        A dict of the recognised summary keys present in *data*, plus the nested
        ``summary`` sub-object when present. Empty when *data* is not a dict.
    """
    if not isinstance(data, dict):
        return {}
    summary: dict[str, Any] = {
        key: data[key] for key in _DATA_SUMMARY_KEYS if key in data
    }
    nested = data.get("summary")
    if isinstance(nested, dict):
        summary["summary"] = nested
    return summary


def _project_record(record: dict[str, Any], mode: str) -> dict[str, Any]:
    """Project a single annotation record down to the *mode* shape.

    Args:
        record: One ``{version, data, metadata, updated_at}`` annotation record.
        mode: The resolved response_mode.

    Returns:
        A new record dict shaped for *mode* (see module docstring for the
        ladder).
    """
    version = record.get("version")
    if mode == "minimal":
        return {"version": version}

    if mode == "full":
        return dict(record)

    shaped: dict[str, Any] = {
        "version": version,
        "updated_at": record.get("updated_at"),
        "summary": _summarize_data(record.get("data")),
    }
    if mode == "standard":
        # standard = compact summary + the full data blob (metadata stays out).
        shaped["data"] = record.get("data")
    return shaped


async def get_gene_annotations(
    client: ApiClient,
    gene_id: int,
    source: str | None = None,
    response_mode: str = "compact",
) -> dict[str, Any]:
    """Fetch descriptive annotations for a gene by its numeric database id.

    Args:
        client: The shared :class:`ApiClient` instance.
        gene_id: The numeric KGDB gene id (from ``kgdb_resolve_gene`` /
            ``kgdb_search_genes``).
        source: Optional annotation-source filter; must be one of
            :data:`~kidney_genetics_mcp.contract.ANNOTATION_SOURCE_VALUES` when
            given.
        response_mode: One of ``minimal``, ``compact``, ``standard``, ``full``;
            controls how much of each record's ``data`` blob is surfaced and the
            char budget used to trim the result.

    Returns:
        A dict with keys ``gene`` (``{id, symbol, hgnc_id}``), ``annotations``
        (a ``{source: [projected_record, ...]}`` map), and ``uri``.

    Raises:
        McpToolError: ``invalid_input`` when *source* is not a known annotation
            source; ``not_found`` (propagated from the client) when the gene id
            is absent.
    """
    if source is not None and source not in ANNOTATION_SOURCE_VALUES:
        raise McpToolError(
            "invalid_input",
            f"source must be one of {list(ANNOTATION_SOURCE_VALUES)}",
            field="source",
            allowed=sorted(ANNOTATION_SOURCE_VALUES),
        )

    params: dict[str, Any] | None = {"source": source} if source else None
    payload: dict[str, Any] = await client.get(
        ANNOTATIONS_GENES_BY_GENE_ID_ANNOTATIONS.format(gene_id=gene_id),
        params=params,
    )

    gene = payload.get("gene") or {}
    raw_annotations = payload.get("annotations") or {}

    annotations: dict[str, list[dict[str, Any]]] = {}
    for source_name, records in raw_annotations.items():
        if not isinstance(records, list):
            continue
        annotations[source_name] = [
            _project_record(rec, response_mode)
            for rec in records
            if isinstance(rec, dict)
        ]

    result: dict[str, Any] = {
        "gene": gene,
        "annotations": annotations,
        "uri": f"kidney-genetics://gene/{gene.get('symbol')}",
    }

    settings = Settings()
    max_chars = min(settings.mode_char_budgets.get(response_mode, 12000), _HARD_CAP)
    # Each annotation source is its own list; flatten to per-source list keys so
    # apply_budget can trim the largest source list first while keeping at least
    # one record per source (the "never empty when a match exists" floor).
    trimmable = {key: val for key, val in annotations.items()}
    shaped_lists, dropped = apply_budget(trimmable, max_chars, keep_min=1)
    result["annotations"] = shaped_lists
    if dropped is not None:
        result["_dropped"] = dropped

    return result


async def get_constraint_summary(
    client: ApiClient,
    gene_id: int,
    response_mode: str = "compact",
) -> dict[str, Any]:
    """Fetch the fast gnomAD-constraint summary for a gene by numeric id.

    Returns a flat block of the headline gnomAD constraint metrics plus the
    canonical cross-reference identifiers (NCBI / Ensembl gene id and the MANE
    Select transcript). Sourced from the ``gene_annotations_summary``
    materialized view, so it is a single fast lookup (no JSONB parsing).

    Args:
        client: The shared :class:`ApiClient` instance.
        gene_id: The numeric KGDB gene id (from ``kgdb_resolve_gene`` /
            ``kgdb_search_genes``).
        response_mode: One of ``minimal``, ``compact``, ``standard``, ``full``.
            The summary is small and fixed, so the mode is echoed in meta but the
            field set does not change.

    Returns:
        A dict with ``gene`` (``{id, symbol, hgnc_id}``), ``identifiers``
        (``ncbi_gene_id``, ``ensembl_gene_id``, ``mane_select_transcript``),
        ``constraint`` (pLI, oe_lof + bounds, lof_z/mis_z/syn_z, oe_mis/oe_syn),
        and ``uri``.

    Raises:
        McpToolError: ``not_found`` (propagated from the client) when the gene id
            is absent from the summary view.
    """
    payload: dict[str, Any] = await client.get(
        ANNOTATIONS_GENES_BY_GENE_ID_ANNOTATIONS_SUMMARY.format(gene_id=gene_id)
    )

    identifiers = payload.get("identifiers") or {}
    constraint = payload.get("constraint_scores") or {}

    return {
        "gene": {
            "id": payload.get("gene_id"),
            "symbol": payload.get("symbol"),
            "hgnc_id": payload.get("hgnc_id"),
        },
        "identifiers": {
            "ncbi_gene_id": identifiers.get("ncbi_gene_id"),
            "ensembl_gene_id": identifiers.get("ensembl_gene_id"),
            "mane_select_transcript": identifiers.get("mane_select_transcript"),
        },
        "constraint": {
            "pli": constraint.get("pli"),
            "oe_lof": constraint.get("oe_lof"),
            "oe_lof_upper": constraint.get("oe_lof_upper"),
            "oe_lof_lower": constraint.get("oe_lof_lower"),
            "lof_z": constraint.get("lof_z"),
            "mis_z": constraint.get("mis_z"),
            "syn_z": constraint.get("syn_z"),
            "oe_mis": constraint.get("oe_mis"),
            "oe_syn": constraint.get("oe_syn"),
        },
        "uri": f"kidney-genetics://gene/{payload.get('symbol')}",
    }
