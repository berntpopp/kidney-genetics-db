"""Annotations-family tools (stub — replaced in Wave 2B).

Will register ``kgdb_get_gene_annotations``, ``kgdb_get_constraint_summary``,
``kgdb_get_interaction_partners``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from kidney_genetics_mcp.client.api_client import ApiClient


def register(mcp: FastMCP, client: ApiClient | None) -> None:
    """Register the annotations-family tools (no-op stub until Wave 2B).

    Args:
        mcp: The FastMCP application instance.
        client: The API client, or ``None``.
    """
