"""Curated-associations tool: published expert-reviewed associations (#437).

Registers ``kgdb_list_curated_associations`` (``readOnlyHint``/``idempotentHint``/
``openWorldHint=False``). Thin: typed params, resolved response_mode, then the
service via ``run_tool``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from kidney_genetics_mcp.services import curation as curation_service
from kidney_genetics_mcp.services import dataclass
from kidney_genetics_mcp.services.safe_tool import run_tool
from kidney_genetics_mcp.services.shaping import ResponseMode, resolve_mode

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from kidney_genetics_mcp.client.api_client import ApiClient


def register(mcp: FastMCP, client: ApiClient | None) -> None:
    """Register the curated-associations tool on *mcp*.

    Args:
        mcp: The FastMCP application instance.
        client: The API client, or ``None`` (introspection only).
    """

    @mcp.tool(
        name="kgdb_list_curated_associations",
        annotations={
            "title": "List Published Curated Gene-Disease Associations",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_list_curated_associations(
        gene_symbol: str | None = None,
        relationship_type: Literal["mendelian", "susceptibility"] | None = None,
        response_mode: ResponseMode | None = None,
    ) -> dict[str, Any]:
        """List published expert-reviewed gene-disease associations.

        Each record was curated (in KGDB or Gene Curator) and confirmed by a
        KGDB curator other than its author.
        These records are not part of the evidence score or tier.
        A ``susceptibility`` record is a risk association, never a Mendelian
        validity class.

        ``minimal`` returns gene, disease, relationship type, strength and MOI;
        ``compact`` (default) adds methodology and provenance; ``standard`` adds
        summary, external curator/reviewer and points; ``full`` returns every
        field including citations and the diagnostics section (transcript,
        detectability, resources).

        Args:
            gene_symbol: Approved HGNC symbol to filter on (e.g. ``"PKD1"``).
            relationship_type: ``"mendelian"`` or ``"susceptibility"``.
            response_mode: ``"minimal"``, ``"compact"`` (default),
                ``"standard"`` or ``"full"``.

        Returns:
            A dict with ``associations``, ``total``, ``data_class`` and ``meta``.
        """
        mode = resolve_mode(response_mode)
        return await run_tool(
            lambda: curation_service.list_curated_associations(
                client,  # type: ignore[arg-type]
                gene_symbol=gene_symbol,
                relationship_type=relationship_type,
                response_mode=mode,
            ),
            data_class=dataclass.CURATED_ASSOCIATION,
            response_mode=mode,
        )
