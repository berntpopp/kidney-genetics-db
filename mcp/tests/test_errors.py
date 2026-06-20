"""Tests for the error taxonomy and envelope shape."""

from __future__ import annotations

import pytest

from kidney_genetics_mcp.services.errors import (
    ERROR_CODES,
    McpToolError,
    ambiguous_query,
    invalid_input,
    not_found,
    temporarily_unavailable,
)


def test_envelope_shape() -> None:
    err = McpToolError("invalid_input", "bad", field="tier", hint="use a tier")
    env = err.to_envelope()
    assert env["schema_version"] == "1.0"
    assert env["error"]["code"] == "invalid_input"
    assert env["error"]["message"] == "bad"
    assert env["error"]["field"] == "tier"
    assert env["error"]["hint"] == "use a tier"


def test_none_details_dropped() -> None:
    err = McpToolError("not_found", "x", field=None, hint="h")
    env = err.to_envelope()
    assert "field" not in env["error"]
    assert env["error"]["hint"] == "h"


def test_unknown_code_rejected() -> None:
    with pytest.raises(ValueError):
        McpToolError("nope", "x")


def test_four_codes() -> None:
    assert ERROR_CODES == {
        "invalid_input",
        "not_found",
        "ambiguous_query",
        "temporarily_unavailable",
    }


def test_helpers() -> None:
    assert invalid_input("a", field="f").code == "invalid_input"
    assert not_found("b").code == "not_found"
    amb = ambiguous_query("c", choices=[{"id": 1}])
    assert amb.code == "ambiguous_query"
    assert amb.to_envelope()["error"]["choices"] == [{"id": 1}]
    assert temporarily_unavailable("d").code == "temporarily_unavailable"
