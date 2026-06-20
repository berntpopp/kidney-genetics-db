"""MCP resource registration (stub — replaced in Wave 2D).

Wave 2D will register the static ``kidney-genetics://schema/overview`` and
``kidney-genetics://schema/tool-guide`` Markdown resources here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_resources(mcp: FastMCP) -> None:
    """Register the static documentation resources (no-op stub until Wave 2D).

    Args:
        mcp: The FastMCP application instance.
    """
