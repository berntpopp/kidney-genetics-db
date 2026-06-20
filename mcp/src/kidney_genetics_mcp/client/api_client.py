"""Read-only httpx client restricted to the endpoint allowlist, with a TTL cache."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ..contract import (
    ANNOTATION_SOURCE_VALUES,
    EVIDENCE_GROUP_VALUES,
    EVIDENCE_TIER_VALUES,
    GENE_SORT_FIELD_VALUES,
)
from ..services.errors import McpToolError
from .allowlist import assert_allowed

#: Map upstream query-parameter names → the contract enum that constrains them,
#: so a 422 error envelope can surface ``allowed`` values and a calling LLM can
#: self-correct in a single retry.
_FIELD_ALLOWED: dict[str, list[str]] = {
    "tier": sorted(EVIDENCE_TIER_VALUES),
    "group": sorted(EVIDENCE_GROUP_VALUES),
    "sort": sorted(GENE_SORT_FIELD_VALUES),
    "source": sorted(ANNOTATION_SOURCE_VALUES),
}


def _build_422_error(resp: httpx.Response) -> McpToolError:
    """Translate an upstream 422 into an actionable ``invalid_input`` error.

    Parses the FastAPI validation body
    (``{"detail":[{"loc":[...],"msg":"...","input":...}]}``) to name the
    offending field and value, attaching ``field``, ``allowed`` (when the field
    maps to a known contract enum), ``hint``, and the raw ``upstream_detail`` so
    a consuming model can correct its call without fetching raw schemas.

    Args:
        resp: The 422 :class:`httpx.Response` returned by the upstream API.

    Returns:
        A populated :class:`McpToolError` with code ``invalid_input``.
    """
    try:
        body: Any = resp.json()
    except (json.JSONDecodeError, ValueError):
        body = None

    detail = body.get("detail") if isinstance(body, dict) else None

    if isinstance(detail, list) and detail and isinstance(detail[0], dict):
        first = detail[0]
        loc = first.get("loc") or []
        field = str(loc[-1]) if loc else "unknown"
        upstream_msg = str(first.get("msg") or "value not permitted by the data API")
        bad_value = first.get("input")
        allowed = _FIELD_ALLOWED.get(field)

        if bad_value is not None:
            message = f"invalid value {bad_value!r} for '{field}': {upstream_msg}"
        else:
            message = f"invalid value for '{field}': {upstream_msg}"

        if allowed is not None:
            hint = f"use one of the allowed values for '{field}'"
        else:
            hint = "check the parameter against kgdb_get_capabilities filterable_fields"

        return McpToolError(
            "invalid_input",
            message,
            field=field,
            allowed=allowed,
            hint=hint,
            upstream_detail=detail,
        )

    return McpToolError(
        "invalid_input",
        "the data API rejected the request parameters",
        field="unknown",
        hint="check parameters against kgdb_get_capabilities filterable_fields",
        upstream_detail=detail if detail is not None else body,
    )


class ApiClient:
    """Async client for the public KGDB ``/api`` surface (allowlisted GETs)."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        cache_ttl: int = 300,
    ) -> None:
        """Initialize the client with a base URL, request timeout, and cache TTL.

        Args:
            base_url: Base URL for the API (e.g. ``http://localhost:8000``).
            timeout: HTTP request timeout in seconds.
            cache_ttl: Time-to-live for cached responses in seconds.
        """
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, Any]] = {}

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET an allowlisted path and return the parsed JSON body.

        Args:
            path: The API path relative to ``base_url`` (must be allowlisted).
            params: Optional query parameters forwarded to the request.

        Returns:
            The deserialized JSON response body.

        Raises:
            PermissionError: If a ``GET`` on *path* is not on the allowlist.
            McpToolError: On 404 (``not_found``), 422/400/409
                (``invalid_input``), 300 (``ambiguous_query``), or 5xx / other
                4xx / network errors (``temporarily_unavailable``). Messages are
                domain-framed and never echo the internal route/host.
        """
        assert_allowed("GET", path)
        key = path + "?" + json.dumps(params or {}, sort_keys=True)
        now = time.monotonic()
        hit = self._cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
        try:
            resp = await self._client.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise McpToolError(
                "temporarily_unavailable", "upstream API timed out"
            ) from exc
        except httpx.HTTPError as exc:
            raise McpToolError("temporarily_unavailable", "upstream API error") from exc

        if resp.status_code == 300:
            # Multiple candidates — surface the body's candidates as choices so
            # the caller can disambiguate.
            choices = _extract_choices(resp)
            raise McpToolError(
                "ambiguous_query",
                "the query matched multiple records; choose one",
                choices=choices,
            )
        if resp.status_code == 404:
            raise McpToolError(
                "not_found",
                "the requested record was not found",
                hint=(
                    "verify the identifier via kgdb_resolve_gene or"
                    " kgdb_search_genes before fetching"
                ),
            )
        if resp.status_code == 422:
            raise _build_422_error(resp)
        if resp.status_code >= 500:
            raise McpToolError("temporarily_unavailable", "upstream API unavailable")
        if 400 <= resp.status_code < 500:
            if resp.status_code in (400, 409):
                raise McpToolError(
                    "invalid_input",
                    "the data API rejected the request parameters",
                    hint=(
                        "check the parameter values against"
                        " kgdb_get_capabilities filterable_fields"
                    ),
                )
            raise McpToolError(
                "temporarily_unavailable",
                "the data API rejected the request",
            )
        resp.raise_for_status()
        data = resp.json()
        self._cache[key] = (now + self._cache_ttl, data)
        return data

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()


def _extract_choices(resp: httpx.Response) -> list[Any]:
    """Pull a ``candidates`` list out of a 300 response body (best-effort).

    Args:
        resp: The 300 :class:`httpx.Response`.

    Returns:
        The candidate list when present, otherwise an empty list.
    """
    try:
        body: Any = resp.json()
    except (json.JSONDecodeError, ValueError):
        return []
    if isinstance(body, dict):
        meta = body.get("meta")
        if isinstance(meta, dict) and isinstance(meta.get("candidates"), list):
            return list(meta["candidates"])
        if isinstance(body.get("candidates"), list):
            return list(body["candidates"])
    return []
