"""Network service: STRING-PPI ranked interaction partners (local data).

Backs ``kgdb_get_interaction_partners``. STRING physical-interaction partners
for a gene are stored as a single ``string_ppi`` annotation record whose ``data``
blob carries the per-partner list and degree/percentile summary. This service
reads that local record (no live external STRING call, no graph build), filters
by STRING combined score, ranks by score, samples to a bounded set, and tags
each partner with a ``resolve_with`` directive so the model can chase a partner
back into the gene tools without losing the resolution chain.
"""

from __future__ import annotations

from typing import Any

from ..client.api_client import ApiClient
from ..config import Settings
from ..contract._generated_paths import ANNOTATIONS_GENES_BY_GENE_ID_ANNOTATIONS
from .errors import McpToolError
from .shaping import apply_budget, sample_with_signal

_HARD_CAP = 80_000

#: Default STRING combined-score floor (matches the backend ingestion default).
_DEFAULT_MIN_STRING_SCORE = 400
#: Default number of partners returned before sampling/budget trimming.
_DEFAULT_LIMIT = 25


def _resolve_with(partner_symbol: str) -> dict[str, Any]:
    """Build the cross-tool resolution directive for a partner symbol.

    Args:
        partner_symbol: The partner gene's HGNC symbol.

    Returns:
        A ``resolve_with`` directive pointing at ``kgdb_get_gene``.
    """
    return {
        "tool": "kgdb_get_gene",
        "argument": "gene_symbol",
        "value": partner_symbol,
    }


async def get_interaction_partners(
    client: ApiClient,
    gene_id: int,
    min_string_score: int = _DEFAULT_MIN_STRING_SCORE,
    limit: int = _DEFAULT_LIMIT,
    response_mode: str = "compact",
) -> dict[str, Any]:
    """Return ranked STRING-PPI partners for a gene by its numeric id.

    Args:
        client: The shared :class:`ApiClient` instance.
        gene_id: The numeric KGDB gene id (from ``kgdb_resolve_gene`` /
            ``kgdb_search_genes``).
        min_string_score: Minimum STRING combined score (0-1000) a partner must
            meet to be included. Defaults to ``400``.
        limit: Maximum number of partners to return after filtering/ranking.
            Defaults to ``25``.
        response_mode: One of ``minimal``, ``compact``, ``standard``, ``full``;
            controls the char budget used to trim the partner list.

    Returns:
        A dict with ``gene`` (``{id, symbol, hgnc_id}``), ``summary``
        (``total_interactions`` / ``ppi_degree`` / ``ppi_percentile`` when
        present), ``partners`` (the ranked, sampled list — each entry carries
        ``resolve_with``), and ``uri``.

    Raises:
        McpToolError: ``invalid_input`` when *min_string_score* or *limit* is out
            of range; ``not_found`` (propagated from the client) when the gene id
            is absent.
    """
    if not 0 <= min_string_score <= 1000:
        raise McpToolError(
            "invalid_input",
            "min_string_score must be between 0 and 1000",
            field="min_string_score",
        )
    if limit < 1:
        raise McpToolError(
            "invalid_input",
            "limit must be a positive integer",
            field="limit",
        )

    payload: dict[str, Any] = await client.get(
        ANNOTATIONS_GENES_BY_GENE_ID_ANNOTATIONS.format(gene_id=gene_id),
        params={"source": "string_ppi"},
    )

    gene = payload.get("gene") or {}
    records = (payload.get("annotations") or {}).get("string_ppi") or []
    data: dict[str, Any] = {}
    if records and isinstance(records[0], dict):
        candidate = records[0].get("data")
        if isinstance(candidate, dict):
            data = candidate

    raw_interactions = data.get("interactions")
    interactions: list[dict[str, Any]] = (
        [i for i in raw_interactions if isinstance(i, dict)]
        if isinstance(raw_interactions, list)
        else []
    )

    # Filter by STRING score, then rank descending by STRING score.
    filtered = [
        i
        for i in interactions
        if isinstance(i.get("string_score"), (int, float))
        and i["string_score"] >= min_string_score
    ]
    filtered.sort(key=lambda i: i["string_score"], reverse=True)

    # sample_with_signal both caps to ``limit`` and emits a truncation signal
    # when more partners matched than were returned, so the model learns to widen
    # ``limit`` rather than assuming it saw the complete partner set.
    sampled, signal = sample_with_signal(filtered, "partners", size=limit)

    partners: list[dict[str, Any]] = []
    for partner in sampled:
        entry = dict(partner)
        symbol = entry.get("partner_symbol")
        if symbol:
            entry["resolve_with"] = _resolve_with(str(symbol))
        partners.append(entry)

    # Summary: prefer the nested summary block's total_interactions, falling back
    # to the top-level ppi_degree. ppi_degree / ppi_percentile are top-level.
    nested_summary = data.get("summary")
    total_interactions = None
    if isinstance(nested_summary, dict):
        total_interactions = nested_summary.get("total_interactions")
    if total_interactions is None:
        total_interactions = data.get("ppi_degree")

    summary: dict[str, Any] = {}
    if total_interactions is not None:
        summary["total_interactions"] = total_interactions
    if "ppi_degree" in data:
        summary["ppi_degree"] = data.get("ppi_degree")
    if "ppi_percentile" in data:
        summary["ppi_percentile"] = data.get("ppi_percentile")

    result: dict[str, Any] = {
        "gene": gene,
        "summary": summary,
        "partners": partners,
        "uri": f"kidney-genetics://gene/{gene.get('symbol')}",
    }
    if signal:
        result["_meta"] = signal

    settings = Settings()
    max_chars = min(settings.mode_char_budgets.get(response_mode, 12000), _HARD_CAP)
    result, dropped = apply_budget(result, max_chars, keep_min=1)
    if dropped is not None:
        result["_dropped"] = dropped

    return result
