"""Statistics-family tools (stub — replaced in Wave 2C).

Will register ``kgdb_get_database_stats``, ``kgdb_list_sources``,
``kgdb_get_release_citation``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from kidney_genetics_mcp.client.api_client import ApiClient


def register(mcp: FastMCP, client: ApiClient | None) -> None:
    """Register the statistics-family tools (no-op stub until Wave 2C).

    Args:
        mcp: The FastMCP application instance.
        client: The API client, or ``None``.
    """
