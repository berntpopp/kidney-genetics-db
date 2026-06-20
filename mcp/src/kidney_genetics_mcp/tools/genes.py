"""Gene-family tools (stub — replaced in Wave 2A).

Will register ``kgdb_resolve_gene``, ``kgdb_search_genes``, ``kgdb_get_gene``,
``kgdb_get_gene_evidence``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from kidney_genetics_mcp.client.api_client import ApiClient


def register(mcp: FastMCP, client: ApiClient | None) -> None:
    """Register the gene-family tools (no-op stub until Wave 2A).

    Args:
        mcp: The FastMCP application instance.
        client: The API client, or ``None``.
    """
