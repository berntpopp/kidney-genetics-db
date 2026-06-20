"""Tests that every tool module imports and exposes ``register``."""

from __future__ import annotations

import importlib

from kidney_genetics_mcp.tools import _MODULES, register_all


def test_modules_list() -> None:
    assert _MODULES == ("genes", "annotations", "statistics", "capabilities")


def test_each_module_imports_and_has_register() -> None:
    for name in _MODULES:
        module = importlib.import_module(f"kidney_genetics_mcp.tools.{name}")
        assert hasattr(module, "register")
        assert callable(module.register)


def test_register_all_callable_with_none_client() -> None:
    from fastmcp import FastMCP

    mcp = FastMCP("test")
    # stubs are no-ops; should not raise with client=None
    register_all(mcp, None)
