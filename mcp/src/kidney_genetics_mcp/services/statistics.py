"""Database-statistics service: rollup of totals, quality, coverage, overlaps.

Wraps the KGDB ``/api/statistics/summary`` endpoint, projecting the rollup to
the requested ``response_mode`` so a warm client never pays for the full
pairwise-overlap matrix when it only wants the headline totals.
"""

from __future__ import annotations

from typing import Any

from ..client.api_client import ApiClient
from .shaping import sample_with_signal

#: ``/api/statistics/summary`` path (allowlisted, read-only).
_SUMMARY_PATH = "/api/statistics/summary"

#: Per-mode projection of which rollup sections to surface. ``minimal`` keeps
#: only the headline overview; widening modes add quality, coverage, then the
#: pairwise-overlap matrix. ``minimal ⊊ compact ⊊ standard ⊊ full``.
_SECTIONS_BY_MODE: dict[str, tuple[str, ...]] = {
    "minimal": ("overview",),
    "compact": ("overview", "quality"),
    "standard": ("overview", "quality", "coverage"),
    "full": ("overview", "quality", "coverage", "pairwise_overlaps"),
}


async def get_database_stats(
    client: ApiClient,
    *,
    response_mode: str,
) -> dict[str, Any]:
    """Fetch the database-wide statistics rollup, projected per *response_mode*.

    Reads ``/api/statistics/summary`` and returns the JSON:API ``data`` block
    projected to the sections allowed for *response_mode* (see
    :data:`_SECTIONS_BY_MODE`). The pairwise-overlap matrix only appears in
    ``full`` and is sampled to a bounded inline list with a meta signal so a
    long matrix never blows the token budget.

    Args:
        client: Configured :class:`~kidney_genetics_mcp.client.api_client.ApiClient`.
        response_mode: The resolved response_mode driving section projection.

    Returns:
        A dict with the projected statistics sections, ``data_class`` (attached
        by ``run_tool``), and an optional ``_meta`` block carrying overlap
        sampling signals.
    """
    payload: Any = await client.get(_SUMMARY_PATH)
    data: dict[str, Any] = {}
    if isinstance(payload, dict):
        inner = payload.get("data")
        if isinstance(inner, dict):
            data = inner

    sections = _SECTIONS_BY_MODE.get(response_mode, _SECTIONS_BY_MODE["compact"])
    out: dict[str, Any] = {}
    meta_signals: dict[str, Any] = {}

    for section in sections:
        value = data.get(section)
        if value is None:
            continue
        if section == "pairwise_overlaps" and isinstance(value, list):
            sampled, signal = sample_with_signal(value, "pairwise_overlaps")
            out["pairwise_overlaps"] = sampled
            meta_signals.update(signal)
        else:
            out[section] = value

    if meta_signals:
        out["_meta"] = meta_signals
    return out
