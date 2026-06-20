"""Tests for the read-only API client (respx-mocked)."""

from __future__ import annotations

import httpx
import pytest
import respx

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services.errors import McpToolError

_BASE = "http://test-backend"


@respx.mock
async def test_200_and_cache_hit() -> None:
    route = respx.get(f"{_BASE}/api/statistics/summary").mock(
        return_value=httpx.Response(200, json={"total_genes": 5080})
    )
    client = ApiClient(base_url=_BASE)
    try:
        first = await client.get("/api/statistics/summary")
        second = await client.get("/api/statistics/summary")
        assert first == {"total_genes": 5080}
        assert second == first
        # cache hit means only one upstream call
        assert route.call_count == 1
    finally:
        await client.aclose()


@respx.mock
async def test_404_maps_to_not_found() -> None:
    respx.get(f"{_BASE}/api/genes/NOPE").mock(return_value=httpx.Response(404))
    client = ApiClient(base_url=_BASE)
    try:
        with pytest.raises(McpToolError) as exc:
            await client.get("/api/genes/NOPE")
        assert exc.value.code == "not_found"
        # message must not leak the internal route
        assert "/api/genes/NOPE" not in exc.value.message
    finally:
        await client.aclose()


@respx.mock
async def test_422_maps_to_invalid_input_with_field() -> None:
    body = {
        "detail": [
            {
                "loc": ["query", "tier"],
                "msg": "value is not a valid enumeration member",
                "input": "platinum",
            }
        ]
    }
    respx.get(f"{_BASE}/api/genes/").mock(return_value=httpx.Response(422, json=body))
    client = ApiClient(base_url=_BASE)
    try:
        with pytest.raises(McpToolError) as exc:
            await client.get("/api/genes/", params={"tier": "platinum"})
        err = exc.value
        assert err.code == "invalid_input"
        assert err.details["field"] == "tier"
        assert err.details["allowed"] is not None
        assert "platinum" in err.message
    finally:
        await client.aclose()


@respx.mock
async def test_300_maps_to_ambiguous_query() -> None:
    body = {"data": None, "meta": {"candidates": [{"id": 1}, {"id": 2}]}}
    respx.get(f"{_BASE}/api/genes/resolve").mock(
        return_value=httpx.Response(300, json=body)
    )
    client = ApiClient(base_url=_BASE)
    try:
        with pytest.raises(McpToolError) as exc:
            await client.get("/api/genes/resolve", params={"query": "x"})
        assert exc.value.code == "ambiguous_query"
        assert exc.value.details["choices"] == [{"id": 1}, {"id": 2}]
    finally:
        await client.aclose()


@respx.mock
async def test_500_maps_to_temporarily_unavailable() -> None:
    respx.get(f"{_BASE}/api/statistics/summary").mock(
        return_value=httpx.Response(503)
    )
    client = ApiClient(base_url=_BASE)
    try:
        with pytest.raises(McpToolError) as exc:
            await client.get("/api/statistics/summary")
        assert exc.value.code == "temporarily_unavailable"
    finally:
        await client.aclose()


async def test_disallowed_path_raises_permission_error() -> None:
    client = ApiClient(base_url=_BASE)
    try:
        with pytest.raises(PermissionError):
            await client.get("/api/admin/users")
    finally:
        await client.aclose()
