"""Token-cost controls: response modes, field projection, sampling, budgets."""

from __future__ import annotations

import json
from typing import Any, Literal

from .errors import McpToolError

#: The ordered response-mode names (narrowest → widest).
MODES: tuple[str, ...] = ("minimal", "compact", "standard", "full")
DEFAULT_MODE = "compact"

#: Schema-visible enum for the ``response_mode`` parameter shared by every tool.
#: Typing a tool param with this ``Literal`` makes the four valid values appear
#: in the tool's JSON input schema (autocomplete + validation), instead of an
#: opaque ``string``. Kept in lockstep with :data:`MODES`.
ResponseMode = Literal["minimal", "compact", "standard", "full"]

#: Default cap for an inline list (interaction partners, source ids, …) shown
#: without an explicit opt-in, so a long list never blows the token budget the
#: rest of the server respects.
DEFAULT_SAMPLE_SIZE = 10


def resolve_mode(requested: str | None) -> str:
    """Validate/normalize a requested ``response_mode``.

    Args:
        requested: The response_mode string to validate, or ``None`` for the
            default.

    Returns:
        A validated response_mode string.

    Raises:
        McpToolError: With code ``invalid_input`` if *requested* is not one of
            :data:`MODES`.
    """
    if requested is None:
        return DEFAULT_MODE
    if requested not in MODES:
        raise McpToolError(
            "invalid_input",
            f"response_mode must be one of {MODES}",
            field="response_mode",
            allowed=list(MODES),
        )
    return requested


def project_fields(
    row: dict[str, Any],
    fields_by_mode: dict[str, tuple[str, ...]],
    mode: str,
) -> dict[str, Any]:
    """Project a record down to the fields allowed for *mode*.

    Each service supplies a ``fields_by_mode`` ladder where each mode lists the
    keys to keep (``minimal ⊊ compact ⊊ standard ⊊ full``). The conventional
    sentinel ``()`` (empty tuple) means "keep ALL fields" — used for ``full`` so
    nothing is dropped. Keys present in the ladder but absent from *row* are
    skipped (no ``KeyError``).

    Args:
        row: The full record to project.
        fields_by_mode: Mapping of mode name → tuple of keys to keep. An empty
            tuple keeps every field.
        mode: The resolved response_mode.

    Returns:
        A new dict containing only the projected keys (or a shallow copy of
        *row* when the ladder selects "all").
    """
    fields = fields_by_mode.get(mode)
    if fields is None or len(fields) == 0:
        return dict(row)
    return {key: row[key] for key in fields if key in row}


def sample_with_signal(
    items: list[Any],
    prefix: str,
    size: int = DEFAULT_SAMPLE_SIZE,
) -> tuple[list[Any], dict[str, Any]]:
    """Down-sample an inline list to a bounded sample with a meta signal.

    When *items* exceeds *size*, return only the first *size* entries plus a
    machine-readable signal block — ``{prefix}_total`` / ``{prefix}_returned`` /
    ``{prefix}_truncated`` / ``{prefix}_note`` — that tells the agent the
    omission happened and how much was dropped. When the list already fits
    (``len(items) <= size``) it is returned whole with an EMPTY signal, so the
    caller never emits a spurious truncation flag.

    Args:
        items: The full list of items.
        prefix: The meta-key prefix (e.g. ``"partners"`` →
            ``partners_total``/``partners_returned``/``partners_truncated``/
            ``partners_note``).
        size: Maximum number of entries to keep (default
            :data:`DEFAULT_SAMPLE_SIZE`).

    Returns:
        ``(sampled, signal)`` — *sampled* is the (possibly shortened) list and
        *signal* is the meta dict to merge (empty when no truncation occurred).
    """
    total = len(items)
    if total <= size:
        return list(items), {}
    sampled = list(items[:size])
    return sampled, {
        f"{prefix}_total": total,
        f"{prefix}_returned": len(sampled),
        f"{prefix}_truncated": True,
        f"{prefix}_note": (
            f"showing {len(sampled)} of {total}; widen response_mode or use the "
            "tool's limit/filter params to retrieve more"
        ),
    }


def _size(obj: Any) -> int:
    """Return the serialized character size of *obj*."""
    return len(json.dumps(obj, default=str))


def apply_budget(
    payload: dict[str, Any],
    max_chars: int,
    keep_min: int = 1,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Trim the largest list fields until *payload* fits *max_chars*.

    Iterates the payload's list-valued keys largest-first, popping trailing
    items until the serialized payload fits *max_chars*. Each list keeps at
    least *keep_min* items so a real match is never reduced to an empty list
    (the "never empty when a match exists" contract). When trimming occurs a
    ``dropped_summary`` is returned for :func:`build_meta` to surface a
    ``truncated`` flag.

    Args:
        payload: The data dict to potentially trim.
        max_chars: Maximum allowed serialized character count.
        keep_min: Minimum number of items to retain in EACH trimmed list, even
            when a single item already exceeds *max_chars*. Defaults to 1.

    Returns:
        ``(shaped_payload, dropped_summary)`` where *dropped_summary* is ``None``
        when no trimming was needed.
    """
    if _size(payload) <= max_chars:
        return payload, None
    shaped: dict[str, Any] = dict(payload)
    list_keys = [k for k, v in shaped.items() if isinstance(v, list)]
    # Largest list first so a single big list is trimmed before small ones.
    list_keys.sort(key=lambda k: _size(shaped[k]), reverse=True)
    dropped = 0
    for key in list_keys:
        items = list(shaped[key])
        while len(items) > keep_min and _size(shaped) > max_chars:
            items.pop()
            dropped += 1
            shaped[key] = items
        if _size(shaped) <= max_chars:
            break
    summary: dict[str, Any] | None = (
        {"dropped_records": dropped, "reason": "max_response_chars"}
        if dropped
        else None
    )
    return shaped, summary


def build_meta(
    mode: str,
    effective_chars: int,
    dropped: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the ``meta`` block echoed in every payload.

    Args:
        mode: The resolved response_mode string.
        effective_chars: Number of characters in the shaped payload (data plus
            ``data_class``; the self-referential ``meta`` block is excluded).
        dropped: Optional ``dropped_summary`` from :func:`apply_budget`. When
            present a ``truncated`` flag is added.
        extra: Optional service-supplied meta fields merged verbatim (e.g.
            ``applied_sort``, ``ignored_params``, sampling signals). ``None``
            values are dropped.

    Returns:
        A meta dict with ``response_mode``, ``effective_chars``, optional
        ``dropped_summary``/``truncated``, and any merged *extra* fields.
    """
    meta: dict[str, Any] = {
        "response_mode": mode,
        "effective_chars": effective_chars,
    }
    if extra:
        for key, value in extra.items():
            if value is not None:
                meta[key] = value
    if dropped:
        meta["dropped_summary"] = dropped
        meta["truncated"] = True
    return meta
