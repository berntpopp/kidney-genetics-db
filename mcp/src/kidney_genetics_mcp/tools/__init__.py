"""MCP tools exposed by the Kidney-Genetics-DB server.

``register_all`` imports each tool module named in :data:`_MODULES` and calls
its ``register(mcp, client)``. Wave 2 agents only *replace* their own module
files; this registry is never edited downstream, so the families register in
parallel without merge conflicts.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from kidney_genetics_mcp.client.api_client import ApiClient

#: Tool-module names (under ``kidney_genetics_mcp.tools``) registered at startup.
_MODULES: tuple[str, ...] = ("genes", "annotations", "statistics", "capabilities")


def register_all(mcp: FastMCP, client: ApiClient | None) -> None:
    """Register every tool module on the given FastMCP instance.

    Imports each module named in :data:`_MODULES` and invokes its ``register``
    function. Tolerates ``client=None`` (tools that need the client guard
    against this themselves).

    Args:
        mcp: The FastMCP application instance to register tools on.
        client: The API client, or ``None`` (e.g. during introspection).
    """
    for name in _MODULES:
        module = importlib.import_module(f"kidney_genetics_mcp.tools.{name}")
        module.register(mcp, client)
