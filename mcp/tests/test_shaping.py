"""Tests for token-cost shaping helpers."""

from __future__ import annotations

import pytest

from kidney_genetics_mcp.services.errors import McpToolError
from kidney_genetics_mcp.services.shaping import (
    apply_budget,
    build_meta,
    project_fields,
    resolve_mode,
    sample_with_signal,
)

_LADDER = {
    "minimal": ("id",),
    "compact": ("id", "symbol"),
    "standard": ("id", "symbol", "score"),
    "full": (),
}
_ROW = {"id": 1, "symbol": "PKD1", "score": 9.5, "extra": "x"}


def test_projection_ladder() -> None:
    assert project_fields(_ROW, _LADDER, "minimal") == {"id": 1}
    assert project_fields(_ROW, _LADDER, "compact") == {"id": 1, "symbol": "PKD1"}
    assert project_fields(_ROW, _LADDER, "standard") == {
        "id": 1,
        "symbol": "PKD1",
        "score": 9.5,
    }
    # full = () keeps all fields (copy, not the same object)
    full = project_fields(_ROW, _LADDER, "full")
    assert full == _ROW
    assert full is not _ROW


def test_projection_missing_key_skipped() -> None:
    ladder = {"minimal": ("id", "absent")}
    assert project_fields({"id": 1}, ladder, "minimal") == {"id": 1}


def test_projection_unknown_mode_keeps_all() -> None:
    assert project_fields(_ROW, _LADDER, "weird") == _ROW


def test_sample_no_truncation() -> None:
    items = [1, 2, 3]
    sampled, signal = sample_with_signal(items, "partners", size=10)
    assert sampled == items
    assert signal == {}


def test_sample_with_signal_fields() -> None:
    items = list(range(25))
    sampled, signal = sample_with_signal(items, "partners", size=10)
    assert sampled == list(range(10))
    assert signal["partners_total"] == 25
    assert signal["partners_returned"] == 10
    assert signal["partners_truncated"] is True
    assert "partners_note" in signal
    assert "10 of 25" in signal["partners_note"]


def test_apply_budget_no_trim() -> None:
    payload = {"items": [1, 2, 3]}
    shaped, dropped = apply_budget(payload, max_chars=10_000)
    assert shaped == payload
    assert dropped is None


def test_apply_budget_trims_to_keep_min() -> None:
    payload = {"items": [{"v": "x" * 50} for _ in range(50)]}
    shaped, dropped = apply_budget(payload, max_chars=200, keep_min=1)
    assert dropped is not None
    assert dropped["reason"] == "max_response_chars"
    assert dropped["dropped_records"] > 0
    # keep_min floor honoured — never fully empty
    assert len(shaped["items"]) >= 1


def test_apply_budget_trims_largest_list_first() -> None:
    payload = {
        "small": [1, 2, 3],
        "big": [{"v": "y" * 40} for _ in range(40)],
    }
    shaped, dropped = apply_budget(payload, max_chars=300, keep_min=1)
    assert dropped is not None
    # the small list should be left intact; trimming hit the big one
    assert shaped["small"] == [1, 2, 3]
    assert len(shaped["big"]) < 40


def test_build_meta_basic() -> None:
    meta = build_meta("compact", 123)
    assert meta == {"response_mode": "compact", "effective_chars": 123}


def test_build_meta_dropped_and_extra() -> None:
    meta = build_meta(
        "full",
        500,
        dropped={"dropped_records": 2, "reason": "max_response_chars"},
        extra={"applied_sort": "score", "ignored": None},
    )
    assert meta["truncated"] is True
    assert meta["dropped_summary"]["dropped_records"] == 2
    assert meta["applied_sort"] == "score"
    assert "ignored" not in meta


def test_resolve_mode() -> None:
    assert resolve_mode(None) == "compact"
    assert resolve_mode("full") == "full"
    with pytest.raises(McpToolError) as exc:
        resolve_mode("nope")
    assert exc.value.code == "invalid_input"
