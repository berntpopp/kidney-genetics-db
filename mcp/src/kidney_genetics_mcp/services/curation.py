"""Curated-associations service: published expert-reviewed gene-disease records (#437).

Reads the public ``/api/curation/associations/`` list (published records only).
These records are curated and reviewed by people; they never feed the KGDB
evidence score or tier.
"""

from __future__ import annotations

from typing import Any

from ..client.api_client import ApiClient

#: Public list endpoint (allowlisted, read-only).
_LIST_PATH = "/api/curation/associations/"

_MINIMAL = (
    "gene_symbol",
    "disease_id",
    "disease_name",
    "relationship_type",
    "evidence_strength",
    "moi",
)
_COMPACT = (
    *_MINIMAL,
    "moi_label",
    "methodology",
    "methodology_version",
    "source",
    "external_url",
    "published_at",
)
_STANDARD = (
    *_COMPACT,
    "evidence_summary",
    "external_curator",
    "external_reviewer",
    "scores",
)
_FIELDS = {"minimal": _MINIMAL, "compact": _COMPACT, "standard": _STANDARD}


async def list_curated_associations(
    client: ApiClient,
    *,
    gene_symbol: str | None,
    relationship_type: str | None,
    response_mode: str,
) -> dict[str, Any]:
    """Return published associations, optionally for one gene and relationship type.

    Args:
        client: Configured API client.
        gene_symbol: Approved symbol to filter on (server side), or ``None``.
        relationship_type: ``mendelian`` or ``susceptibility`` (filtered here),
            or ``None``.
        response_mode: ``full`` returns every field incl. citations and
            diagnostics.

    Returns:
        ``{"associations": [...], "total": int}``.
    """
    # ponytail: one page of 1000 (the API maximum); page through meta.total if published
    # curations ever exceed that
    params: dict[str, Any] = {"limit": 1000}
    if gene_symbol:
        params["gene_symbol"] = gene_symbol
    payload: Any = await client.get(_LIST_PATH, params=params)
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    rows = [
        r
        for r in rows
        if isinstance(r, dict)
        and (
            relationship_type is None or r.get("relationship_type") == relationship_type
        )
    ]
    fields = _FIELDS.get(response_mode)
    if fields is not None:
        rows = [{k: r.get(k) for k in fields} for r in rows]
    return {"associations": rows, "total": len(rows)}
