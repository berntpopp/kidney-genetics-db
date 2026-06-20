"""Gene resolution service — free-text/ID → canonical gene identity.

Calls the backend ``GET /api/genes/resolve`` and maps its JSON:API body to a
small typed identity payload, or — when the backend reports the query was
ambiguous — raises :class:`~kidney_genetics_mcp.services.errors.McpToolError`
with code ``ambiguous_query`` carrying the candidate ``choices``.
"""

from __future__ import annotations

from typing import Any

from ..client.api_client import ApiClient
from ..contract import GENES_RESOLVE
from .errors import ambiguous_query, invalid_input

#: The detail tool a resolved identity should hand off to.
_RESOLVE_WITH_TOOL = "kgdb_get_gene"


async def resolve_gene(
    client: ApiClient,
    query: str,
    *,
    response_mode: str = "compact",  # noqa: ARG001 — identity payload is already minimal
) -> dict[str, Any]:
    """Resolve a free-text/ID *query* to a canonical gene identity.

    Calls ``GET /api/genes/resolve?query=<query>``. The backend returns one of:

    * single match — ``{data: {type, id, attributes: {hgnc_id, approved_symbol,
      matched_on, match_type}}, meta: {...}}`` (HTTP 200);
    * ambiguous — ``{data: null, meta: {ambiguous: true, candidates: [...]}}``
      (HTTP 200), or an HTTP 300 the :class:`ApiClient` already maps to
      ``ambiguous_query``;
    * no match — HTTP 404, mapped by the client to ``not_found``.

    On a single match this returns a flat identity dict plus an explicit
    ``resolve_with`` handoff so the model never loses the chain to
    ``kgdb_get_gene``. On the ambiguous body it raises ``ambiguous_query`` with
    the candidate ``choices`` (mirroring the client's HTTP-300 path).

    Args:
        client: Authenticated :class:`ApiClient` instance.
        query: The free-text or identifier string to resolve (non-empty).
        response_mode: Accepted for interface consistency; the identity payload
            is already minimal so it does not change the output.

    Returns:
        ``{"gene": {id, hgnc_id, approved_symbol, match_type}, "resolve_with":
        {tool, argument, value}}``.

    Raises:
        McpToolError: ``invalid_input`` for an empty query; ``ambiguous_query``
            (with ``choices``) when the query matched multiple genes;
            ``not_found`` / ``temporarily_unavailable`` propagated from the
            client.
    """
    if not query or not query.strip():
        raise invalid_input(
            "query must be a non-empty string",
            field="query",
            hint=(
                "provide a gene symbol, alias, HGNC/Ensembl/NCBI id, or UniProt"
                " accession"
            ),
        )

    raw: dict[str, Any] = await client.get(
        GENES_RESOLVE, params={"query": query.strip()}
    )

    data = raw.get("data") if isinstance(raw, dict) else None
    meta: dict[str, Any] = (raw.get("meta") or {}) if isinstance(raw, dict) else {}

    # Ambiguous body (HTTP 200 with data:null + candidates). The HTTP-300 path is
    # handled upstream by ApiClient, so this covers the 200 variant the backend
    # actually returns.
    if data is None:
        candidates = meta.get("candidates")
        choices: list[Any] = list(candidates) if isinstance(candidates, list) else []
        raise ambiguous_query(
            f"the query {query.strip()!r} matched multiple genes; choose one and "
            "re-resolve by its approved_symbol or HGNC id",
            choices=choices,
        )

    attributes: dict[str, Any] = data.get("attributes") or {}
    approved_symbol = attributes.get("approved_symbol")

    gene: dict[str, Any] = {
        "id": data.get("id"),
        "hgnc_id": attributes.get("hgnc_id"),
        "approved_symbol": approved_symbol,
        "match_type": attributes.get("match_type"),
    }

    return {
        "gene": gene,
        "resolve_with": {
            "tool": _RESOLVE_WITH_TOOL,
            "argument": "gene_symbol",
            "value": approved_symbol,
        },
    }
