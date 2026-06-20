"""Gene search + detail services.

``search_genes`` browses ``GET /api/genes/`` with bracket-style JSON:API filter /
sort / pagination params and returns a list of shaped hits (field-laddered per
response mode), each carrying a ``resolve_with`` handoff to ``kgdb_get_gene``.
``get_gene`` fetches ``GET /api/genes/{symbol}`` and returns the score / tier /
group / source-score detail, field-laddered per response mode.
"""

from __future__ import annotations

from typing import Any

from ..client.api_client import ApiClient
from ..config import Settings
from ..contract import (
    EVIDENCE_GROUP_VALUES,
    EVIDENCE_TIER_VALUES,
    GENE_SORT_FIELD_VALUES,
    GENES,
    GENES_BY_GENE_SYMBOL,
)
from .errors import invalid_input
from .shaping import apply_budget, project_fields

# The detail tool each search hit hands off to.
_RESOLVE_WITH_TOOL = "kgdb_get_gene"

_VALID_TIER = frozenset(EVIDENCE_TIER_VALUES)
_VALID_GROUP = frozenset(EVIDENCE_GROUP_VALUES)
_VALID_SORT = frozenset(GENE_SORT_FIELD_VALUES)

# Per-mode field ladder for a search-result row (minimal ⊊ compact ⊊ standard;
# full = () keeps every field). ``id`` / ``approved_symbol`` anchor every row so
# a hit is always identifiable and chainable.
_SEARCH_FIELDS_BY_MODE: dict[str, tuple[str, ...]] = {
    "minimal": ("id", "approved_symbol", "hgnc_id", "evidence_score", "evidence_tier"),
    "compact": (
        "id",
        "approved_symbol",
        "hgnc_id",
        "evidence_score",
        "evidence_tier",
        "evidence_group",
    ),
    "standard": (
        "id",
        "approved_symbol",
        "hgnc_id",
        "evidence_score",
        "evidence_tier",
        "evidence_group",
        "sources",
    ),
    "full": (),  # () == keep every field
}

# Per-mode field ladder for the single-gene detail payload. ``minimal`` is the
# core score fields; ``full`` keeps everything (including score_breakdown +
# source_scores). The identity keys are always retained via ``_DETAIL_ALWAYS``.
_DETAIL_ALWAYS = ("id", "approved_symbol", "hgnc_id")
_DETAIL_FIELDS_BY_MODE: dict[str, tuple[str, ...]] = {
    "minimal": _DETAIL_ALWAYS
    + ("evidence_score", "evidence_tier", "evidence_group", "evidence_count"),
    "compact": _DETAIL_ALWAYS
    + (
        "evidence_score",
        "evidence_tier",
        "evidence_group",
        "evidence_count",
        "sources",
    ),
    "standard": _DETAIL_ALWAYS
    + (
        "evidence_score",
        "evidence_tier",
        "evidence_group",
        "evidence_count",
        "sources",
        "score_breakdown",
    ),
    "full": (),  # () == keep every field (adds source_scores)
}


def _validate_enum(value: str | None, valid: frozenset[str], field: str) -> None:
    """Raise ``invalid_input`` when *value* is set but outside *valid*.

    Args:
        value: The caller-supplied value to check, or ``None`` to skip.
        valid: The accepted value set (from the generated contract).
        field: The parameter name embedded in the error for self-correction.

    Raises:
        McpToolError: ``invalid_input`` when *value* is not accepted.
    """
    if value is not None and value not in valid:
        raise invalid_input(
            f"invalid value {value!r} for {field!r}",
            field=field,
            allowed=sorted(valid),
            hint=f"use one of the allowed values for {field!r}",
        )


def _shape_hit(item: dict[str, Any]) -> dict[str, Any]:
    """Map a raw JSON:API gene list item to a flat search hit (all fields).

    Args:
        item: A raw ``{type, id, attributes}`` gene object.

    Returns:
        A flat dict with the canonical search-hit fields.
    """
    attrs: dict[str, Any] = item.get("attributes") or {}
    return {
        "id": item.get("id"),
        "approved_symbol": attrs.get("approved_symbol"),
        "hgnc_id": attrs.get("hgnc_id"),
        "evidence_score": attrs.get("evidence_score"),
        "evidence_tier": attrs.get("evidence_tier"),
        "evidence_group": attrs.get("evidence_group"),
        "sources": attrs.get("sources") or [],
    }


def _resolve_with(symbol: str | None) -> dict[str, Any]:
    """Build the per-hit handoff descriptor pointing at ``kgdb_get_gene``.

    Args:
        symbol: The hit's approved symbol (the argument the detail tool takes).

    Returns:
        ``{"tool", "argument", "value"}`` naming the exact next call.
    """
    return {
        "tool": _RESOLVE_WITH_TOOL,
        "argument": "gene_symbol",
        "value": symbol,
    }


def _pagination_meta(meta: dict[str, Any], page: int, page_size: int) -> dict[str, Any]:
    """Extract a normalized pagination block from the backend list ``meta``.

    The backend list meta is ``{total, page, per_page, page_count}``; this maps
    it to a stable ``{total, page, page_size, page_count, has_more}`` block,
    tolerating missing keys.

    Args:
        meta: The raw ``meta`` block from the list response.
        page: The requested 1-based page number (fallback).
        page_size: The requested page size (fallback).

    Returns:
        A normalized pagination dict.
    """
    total = int(meta.get("total") or 0)
    current_page = int(meta.get("page") or page)
    per_page = int(meta.get("per_page") or page_size)
    page_count = int(meta.get("page_count") or 0)
    if page_count == 0 and total and per_page:
        page_count = -(-total // per_page)  # ceil division
    return {
        "total": total,
        "page": current_page,
        "page_size": per_page,
        "page_count": page_count,
        "has_more": current_page < page_count if page_count else False,
    }


async def search_genes(
    client: ApiClient,
    *,
    query: str | None = None,
    tier: str | None = None,
    group: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    source: str | None = None,
    sort: str | None = None,
    page: int = 1,
    page_size: int = 20,
    response_mode: str = "compact",
) -> dict[str, Any]:
    """Browse ``GET /api/genes/`` with filters, sort, and pagination.

    Validates *tier* / *group* / *sort* against the generated contract
    vocabularies before issuing the request, then maps the caller's friendly
    params to the backend's bracket-style JSON:API params
    (``filter[search]``/``filter[tier]``/``filter[group]``/``filter[min_score]``/
    ``filter[max_score]``/``filter[source]``/``sort``/``page[number]``/
    ``page[size]``). Each returned hit carries an explicit ``resolve_with``
    handoff to ``kgdb_get_gene``.

    Args:
        client: Authenticated :class:`ApiClient` instance.
        query: Free-text search → ``filter[search]``.
        tier: Evidence tier filter → ``filter[tier]`` (must be an
            :data:`EVIDENCE_TIER_VALUES` member).
        group: Evidence group filter → ``filter[group]`` (must be an
            :data:`EVIDENCE_GROUP_VALUES` member).
        min_score: Minimum evidence score (0–100) → ``filter[min_score]``.
        max_score: Maximum evidence score (0–100) → ``filter[max_score]``.
        source: Restrict to genes with evidence from this source →
            ``filter[source]``.
        sort: Sort field (a :data:`GENE_SORT_FIELD_VALUES` member, optionally
            ``-``-prefixed for descending) → ``sort``.
        page: 1-based page number → ``page[number]`` (default 1).
        page_size: Results per page → ``page[size]`` (default 20).
        response_mode: One of ``minimal``/``compact``/``standard``/``full``;
            controls the per-hit field set.

    Returns:
        A dict with keys ``genes`` (the shaped hits), ``pagination`` (a
        normalized ``{total, page, page_size, page_count, has_more}`` block),
        and ``guidance``.

    Raises:
        McpToolError: ``invalid_input`` for an out-of-vocabulary tier/group/sort
            value; ``temporarily_unavailable`` / ``not_found`` propagated from
            the client.
    """
    _validate_enum(tier, _VALID_TIER, "tier")
    _validate_enum(group, _VALID_GROUP, "group")
    if sort is not None:
        bare = sort[1:] if sort.startswith("-") else sort
        _validate_enum(bare, _VALID_SORT, "sort")

    params: dict[str, Any] = {
        "page[number]": page,
        "page[size]": page_size,
    }
    if query is not None:
        params["filter[search]"] = query
    if tier is not None:
        params["filter[tier]"] = tier
    if group is not None:
        params["filter[group]"] = group
    if min_score is not None:
        params["filter[min_score]"] = min_score
    if max_score is not None:
        params["filter[max_score]"] = max_score
    if source is not None:
        params["filter[source]"] = source
    if sort is not None:
        params["sort"] = sort

    raw: dict[str, Any] = await client.get(GENES, params=params)
    data: list[dict[str, Any]] = raw.get("data") or []
    meta: dict[str, Any] = raw.get("meta") or {}

    hits: list[dict[str, Any]] = []
    for item in data:
        full = _shape_hit(item)
        projected = project_fields(full, _SEARCH_FIELDS_BY_MODE, response_mode)
        projected["resolve_with"] = _resolve_with(full.get("approved_symbol"))
        hits.append(projected)

    result: dict[str, Any] = {
        "genes": hits,
        "pagination": _pagination_meta(meta, page, page_size),
        "guidance": (
            "Each hit carries a 'resolve_with' object naming the tool and argument"
            " (kgdb_get_gene / gene_symbol) to fetch its full record — call it"
            " verbatim."
        ),
    }

    # Enforce the advertised char budget on the (potentially large) hit list.
    max_chars = Settings().mode_char_budgets.get(response_mode, 12000)
    result, dropped = apply_budget(result, max_chars)
    if dropped is not None:
        result["_dropped"] = dropped

    return result


async def get_gene(
    client: ApiClient,
    gene_symbol: str,
    *,
    response_mode: str = "compact",
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch and shape the single-gene overview for *gene_symbol*.

    Calls ``GET /api/genes/{gene_symbol}`` and projects the attributes to the
    per-mode field ladder (``minimal`` = core score fields, ``full`` = all,
    including ``score_breakdown`` + ``source_scores``). An optional explicit
    *fields* allow-list is applied on top of the mode for precise token control.

    Args:
        client: Authenticated :class:`ApiClient` instance.
        gene_symbol: The approved gene symbol to fetch (case-insensitive
            upstream).
        response_mode: One of ``minimal``/``compact``/``standard``/``full``.
        fields: Optional explicit top-level field allow-list applied after the
            mode projection. The identity keys (``id``/``approved_symbol``/
            ``hgnc_id``) are always retained.

    Returns:
        A dict with the projected gene attributes plus a ``uri`` identifier.

    Raises:
        McpToolError: ``not_found`` (re-raised richly with the offending symbol)
            when no gene matches; ``temporarily_unavailable`` on upstream
            errors.
    """
    raw: dict[str, Any] = await client.get(
        GENES_BY_GENE_SYMBOL.format(gene_symbol=gene_symbol)
    )
    data: dict[str, Any] = raw.get("data") or {}
    attrs: dict[str, Any] = data.get("attributes") or {}

    full: dict[str, Any] = {
        "id": data.get("id"),
        "approved_symbol": attrs.get("approved_symbol"),
        "hgnc_id": attrs.get("hgnc_id"),
        "evidence_score": attrs.get("evidence_score"),
        "evidence_tier": attrs.get("evidence_tier"),
        "evidence_group": attrs.get("evidence_group"),
        "evidence_count": attrs.get("evidence_count"),
        "sources": attrs.get("sources") or [],
        "score_breakdown": attrs.get("score_breakdown") or {},
        "source_scores": attrs.get("source_scores") or {},
        "uri": f"kidney-genetics://gene/{attrs.get('approved_symbol')}",
    }

    projected = project_fields(full, _DETAIL_FIELDS_BY_MODE, response_mode)
    # Identity + uri must survive even narrow modes so the record stays chainable.
    for key in (*_DETAIL_ALWAYS, "uri"):
        if key not in projected and key in full:
            projected[key] = full[key]

    if fields:
        keep = set(fields) | set(_DETAIL_ALWAYS) | {"uri"}
        projected = {k: v for k, v in projected.items() if k in keep}

    return projected
