"""Uniform tool execution wrapper: timing, meta, data_class, error envelopes."""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from .errors import McpToolError
from .shaping import build_meta


async def run_tool(
    coro_factory: Callable[[], Awaitable[dict[str, Any]]],
    *,
    data_class: str,
    response_mode: str,
) -> dict[str, Any]:
    """Execute a service handler, attaching meta/data_class or an error envelope.

    Times the handler, attaches the ``data_class`` tag and a ``meta`` block, and
    consumes the internal ``_dropped``/``_meta`` channels a service may set:

    - ``_dropped`` — a ``dropped_summary`` from
      :func:`~kidney_genetics_mcp.services.shaping.apply_budget` (signals
      truncation).
    - ``_meta`` — extra meta fields to surface (sampling signals,
      ``applied_sort``, ``ignored_params``, …) so no server behavior stays
      silent.

    A :class:`~kidney_genetics_mcp.services.errors.McpToolError` is returned as
    its error envelope with ``is_error: True``. Any other (unexpected) exception
    is mapped to a ``temporarily_unavailable`` envelope so an internal bug never
    leaks a stack trace or internal route to the client.

    Args:
        coro_factory: A zero-arg callable returning the awaitable service
            handler (so timing wraps the actual work, not coroutine creation).
        data_class: The ``data_class`` tag for the payload.
        response_mode: The resolved response_mode echoed in ``meta``.

    Returns:
        The success payload (with ``data_class`` + ``meta``) or an error
        envelope (with ``is_error: True``).
    """
    start = time.monotonic()
    try:
        result = await coro_factory()
    except McpToolError as exc:
        envelope = exc.to_envelope()
        envelope["is_error"] = True
        return envelope
    except Exception:  # noqa: BLE001 — never leak an internal error to clients
        envelope = McpToolError(
            "temporarily_unavailable",
            "the request could not be completed; please retry shortly",
        ).to_envelope()
        envelope["is_error"] = True
        return envelope
    elapsed_ms = round((time.monotonic() - start) * 1000, 1)
    dropped = result.pop("_dropped", None)
    extra_meta = result.pop("_meta", None)
    # Attach data_class before measuring so effective_chars reflects the real
    # serialized payload (everything except the self-referential meta block).
    result["data_class"] = data_class
    effective_chars = len(json.dumps(result, default=str))
    meta = build_meta(
        mode=response_mode,
        effective_chars=effective_chars,
        dropped=dropped,
        extra=extra_meta,
    )
    meta["elapsed_ms"] = elapsed_ms
    result["meta"] = meta
    return result
