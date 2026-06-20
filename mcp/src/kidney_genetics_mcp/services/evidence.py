"""Per-source scored evidence service.

``get_gene_evidence`` fetches ``GET /api/genes/{symbol}/evidence`` and shapes
each record to ``{source_name, source_detail, normalized_score, evidence_date,
evidence_data}``. The bulky ``evidence_data`` JSONB is projected out in the
narrow modes (dropped in ``minimal``/``compact``, kept in ``standard``/``full``).
An optional ``sources`` filter restricts the records by ``source_name``, and the
record list is sampled / budget-trimmed to stay within the mode's char budget.
"""

from __future__ import annotations

from typing import Any

from ..client.api_client import ApiClient
from ..config import Settings
from ..contract import GENES_BY_GENE_SYMBOL_EVIDENCE
from .shaping import apply_budget, sample_with_signal

# Per-mode field ladder for one evidence record. ``evidence_data`` (the bulky
# JSONB) is dropped in minimal/compact and kept in standard/full; the scalar
# provenance fields are always present so a record stays interpretable.
_RECORD_ALWAYS = ("source_name", "source_detail", "normalized_score", "evidence_date")
_EVIDENCE_FIELDS_BY_MODE: dict[str, tuple[str, ...]] = {
    "minimal": _RECORD_ALWAYS,
    "compact": _RECORD_ALWAYS,
    "standard": _RECORD_ALWAYS + ("evidence_data",),
    "full": (),  # () == keep every field
}


def _shape_record(item: dict[str, Any]) -> dict[str, Any]:
    """Map a raw JSON:API evidence item to a flat record (all fields).

    Args:
        item: A raw ``{type, id, attributes}`` evidence object.

    Returns:
        A flat evidence dict with the canonical fields.
    """
    attrs: dict[str, Any] = item.get("attributes") or {}
    return {
        "id": item.get("id"),
        "source_name": attrs.get("source_name"),
        "source_detail": attrs.get("source_detail"),
        "normalized_score": attrs.get("normalized_score"),
        "evidence_date": attrs.get("evidence_date"),
        "evidence_data": attrs.get("evidence_data"),
    }


def _project_record(record: dict[str, Any], mode: str) -> dict[str, Any]:
    """Project one evidence record to the field set allowed for *mode*.

    Args:
        record: A fully-shaped evidence dict (output of :func:`_shape_record`).
        mode: One of ``minimal``/``compact``/``standard``/``full``.

    Returns:
        A new dict keeping only the permitted fields (full keeps all).
    """
    allowed = _EVIDENCE_FIELDS_BY_MODE.get(mode, ())
    if not allowed:
        return dict(record)
    return {key: record[key] for key in allowed if key in record}


async def get_gene_evidence(
    client: ApiClient,
    gene_symbol: str,
    *,
    sources: list[str] | None = None,
    response_mode: str = "compact",
) -> dict[str, Any]:
    """Fetch and shape per-source scored evidence for *gene_symbol*.

    Calls ``GET /api/genes/{gene_symbol}/evidence``. Each record is shaped to
    ``{source_name, source_detail, normalized_score, evidence_date,
    evidence_data}``; the bulky ``evidence_data`` JSONB is dropped in
    ``minimal``/``compact`` and retained in ``standard``/``full`` (per-mode
    projection). An optional *sources* list filters records by ``source_name``.
    The record list is sampled to a bounded inline cap and then trimmed to the
    mode's char budget so a heavily-evidenced gene never blows the token budget.

    Args:
        client: Authenticated :class:`ApiClient` instance.
        gene_symbol: The approved gene symbol whose evidence is requested.
        sources: Optional list of ``source_name`` values to keep (others are
            filtered out); ``None`` keeps every source.
        response_mode: One of ``minimal``/``compact``/``standard``/``full``;
            controls the per-record field set.

    Returns:
        A dict with keys ``gene_symbol``, ``evidence`` (the shaped records),
        and ``evidence_count`` (the count after filtering).

    Raises:
        McpToolError: ``not_found`` when the gene does not exist;
            ``temporarily_unavailable`` on upstream errors.
    """
    raw: dict[str, Any] = await client.get(
        GENES_BY_GENE_SYMBOL_EVIDENCE.format(gene_symbol=gene_symbol)
    )
    data: list[dict[str, Any]] = raw.get("data") or []
    meta: dict[str, Any] = raw.get("meta") or {}

    wanted: frozenset[str] | None = frozenset(sources) if sources else None
    records: list[dict[str, Any]] = []
    for item in data:
        shaped = _shape_record(item)
        if wanted is not None and shaped.get("source_name") not in wanted:
            continue
        records.append(_project_record(shaped, response_mode))

    # Authoritative count comes from the filtered set we actually return; fall
    # back to the upstream meta count for the unfiltered case.
    if wanted is not None:
        evidence_count = len(records)
    else:
        evidence_count = int(meta.get("evidence_count") or len(records))

    # Cap the inline list to a bounded sample with a machine-readable signal so a
    # gene with many evidence records does not dump them all in one response.
    sampled, signal = sample_with_signal(records, "evidence")

    result: dict[str, Any] = {
        "gene_symbol": meta.get("gene_symbol") or gene_symbol,
        "evidence": sampled,
        "evidence_count": evidence_count,
    }
    if signal:
        result["_meta"] = signal

    # Enforce the advertised char budget (evidence_data JSONB can be large even
    # after sampling, especially in standard/full).
    max_chars = Settings().mode_char_budgets.get(response_mode, 12000)
    result, dropped = apply_budget(result, max_chars)
    if dropped is not None:
        result["_dropped"] = dropped

    return result
