"""Capabilities tool (stub — replaced in Wave 2D).

Will register ``kgdb_get_capabilities``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from kidney_genetics_mcp.client.api_client import ApiClient


def register(mcp: FastMCP, client: ApiClient | None) -> None:
    """Register the capabilities tool (no-op stub until Wave 2D).

    Args:
        mcp: The FastMCP application instance.
        client: The API client, or ``None``.
    """
