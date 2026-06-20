"""Tests for the code-enforced API allowlist (security boundary)."""

from __future__ import annotations

import pytest

from kidney_genetics_mcp.client.allowlist import (
    assert_allowed,
    is_allowed,
    is_denied,
)

_ALLOWED_GET_PATHS = [
    "/api/genes/resolve",
    "/api/genes",
    "/api/genes/",
    "/api/genes/PKD1",
    "/api/genes/PKD1/evidence",
    "/api/annotations/genes/123/annotations",
    "/api/annotations/genes/123/annotations/summary",
    "/api/annotations/sources",
    "/api/statistics/summary",
    "/api/datasources",
    "/api/datasources/",
    "/api/releases",
    "/api/releases/",
]


@pytest.mark.parametrize("path", _ALLOWED_GET_PATHS)
def test_every_allow_path_passes_for_get(path: str) -> None:
    assert is_allowed("GET", path) is True
    assert_allowed("GET", path)  # no raise


@pytest.mark.parametrize("path", _ALLOWED_GET_PATHS)
def test_post_on_allowed_path_raises(path: str) -> None:
    assert is_allowed("POST", path) is False
    with pytest.raises(PermissionError):
        assert_allowed("POST", path)


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE", "PUT"])
def test_non_get_methods_denied(method: str) -> None:
    with pytest.raises(PermissionError):
        assert_allowed(method, "/api/genes/")


@pytest.mark.parametrize(
    "path",
    [
        "/api/admin/users",
        "/api/auth/login",
        "/api/staging/genes",
        "/api/ingestion/run",
        "/api/progress/123",
        "/api/network",
        "/api/network/build",
    ],
)
def test_denied_paths_raise(path: str) -> None:
    assert is_denied(path) is True
    with pytest.raises(PermissionError):
        assert_allowed("GET", path)


@pytest.mark.parametrize(
    "path",
    [
        "/api/genes/PKD1/curations",
        "/api/annotations/genes/abc/annotations",  # non-digit id not allowed
        "/api/seo/sitemap",
        "/api/unknown",
        "/openapi.json",
    ],
)
def test_unlisted_paths_denied(path: str) -> None:
    assert is_allowed("GET", path) is False
    with pytest.raises(PermissionError):
        assert_allowed("GET", path)
