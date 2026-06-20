"""Statistics-family tools: database stats, source provenance, release citation.

Registers (all ``readOnlyHint``/``idempotentHint``/``openWorldHint=False``):

- ``kgdb_get_database_stats`` — database-wide rollup (totals, quality,
  coverage, pairwise source overlaps). HEAVY tool (tighter rate limit).
- ``kgdb_list_sources`` — merged annotation + data source provenance list
  (powers the citation provenance contract).
- ``kgdb_get_release_citation`` — the current published data-release citation
  (recommended_citation + version + dataset DOI + software concept DOI).

Each tool is thin: it declares typed params, resolves the response_mode, and
delegates to its service via ``run_tool``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kidney_genetics_mcp.services import dataclass
from kidney_genetics_mcp.services import releases as releases_service
from kidney_genetics_mcp.services import sources as sources_service
from kidney_genetics_mcp.services import statistics as statistics_service
from kidney_genetics_mcp.services.safe_tool import run_tool
from kidney_genetics_mcp.services.shaping import ResponseMode, resolve_mode

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from kidney_genetics_mcp.client.api_client import ApiClient


def register(mcp: FastMCP, client: ApiClient | None) -> None:
    """Register the statistics-family tools on *mcp*.

    Args:
        mcp: The FastMCP application instance.
        client: The API client, or ``None`` (e.g. during introspection; the
            tools are registered regardless and only touch *client* when run).
    """

    @mcp.tool(
        name="kgdb_get_database_stats",
        annotations={
            "title": "Get Kidney-Genetics Database Statistics",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_get_database_stats(
        response_mode: ResponseMode | None = None,
    ) -> dict[str, Any]:
        """Get the database-wide statistics rollup for Kidney-Genetics-DB.

        Returns a dashboard-style rollup of the curated database:

        - ``overview`` — ``total_genes``, ``active_sources``,
          ``genes_in_all_sources`` (and ``total_intersections``).
        - ``quality`` — ``avg_sources_per_gene``, ``total_evidence_records``,
          ``high_confidence_genes``.
        - ``coverage`` — single-/multi-source gene counts and source variety.
        - ``pairwise_overlaps`` — the source-vs-source overlap matrix (only in
          ``full``; sampled with a meta signal when long).

        Sections widen with ``response_mode``: ``minimal`` returns only
        ``overview``; ``compact`` adds ``quality``; ``standard`` adds
        ``coverage``; ``full`` adds ``pairwise_overlaps``.

        Args:
            response_mode: Budget tier — ``"minimal"``, ``"compact"`` (default),
                ``"standard"``, or ``"full"``.

        Returns:
            A dict with the projected statistics sections, ``data_class``, and
            ``meta``.
        """
        mode = resolve_mode(response_mode)
        return await run_tool(
            lambda: statistics_service.get_database_stats(
                client,  # type: ignore[arg-type]
                response_mode=mode,
            ),
            data_class=dataclass.STATISTICS,
            response_mode=mode,
        )

    @mcp.tool(
        name="kgdb_list_sources",
        annotations={
            "title": "List Kidney-Genetics Data Sources",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_list_sources(
        response_mode: ResponseMode | None = None,
    ) -> dict[str, Any]:
        """List the data sources behind Kidney-Genetics-DB, with provenance.

        Merges the descriptive-annotation source registry and the evidence
        data-source registry into a single provenance list. Each record carries
        ``source_name``, ``display_name``, ``version``, ``url``,
        ``last_update``, and (in wider modes) per-source ``gene_count`` /
        ``evidence_count``. This list powers the citation provenance contract:
        cite each source's display name + version alongside the data-release
        citation from ``kgdb_get_release_citation``.

        Field detail widens with ``response_mode``: ``minimal`` returns name +
        version; ``compact`` adds url + last_update; ``standard`` adds counts;
        ``full`` returns every available field.

        Args:
            response_mode: Budget tier — ``"minimal"``, ``"compact"`` (default),
                ``"standard"``, or ``"full"``.

        Returns:
            A dict with ``sources`` (the merged, projected provenance records),
            ``total``, ``data_class``, and ``meta``.
        """
        mode = resolve_mode(response_mode)
        return await run_tool(
            lambda: sources_service.list_sources(
                client,  # type: ignore[arg-type]
                response_mode=mode,
            ),
            data_class=dataclass.SOURCE,
            response_mode=mode,
        )

    @mcp.tool(
        name="kgdb_get_release_citation",
        annotations={
            "title": "Get Kidney-Genetics Data-Release Citation",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_get_release_citation(
        response_mode: ResponseMode | None = None,
    ) -> dict[str, Any]:
        """Get the citation for the current published Kidney-Genetics data release.

        Returns the latest published data release's dataset citation —
        ``recommended_citation`` (paste verbatim), the CalVer ``version``, the
        dataset ``doi``, and the software ``concept_doi`` — plus key release
        metadata and the export ``export_checksum`` when present. Cite this
        alongside the per-source provenance from ``kgdb_list_sources``.

        Args:
            response_mode: Budget tier — ``"minimal"``, ``"compact"`` (default),
                ``"standard"``, or ``"full"``. The citation payload is a single
                fixed-size record, so the mode is echoed in ``meta`` but does
                not change the fields returned.

        Returns:
            A dict with ``citation``, ``release``, optional ``export_checksum``,
            ``data_class``, and ``meta``.
        """
        mode = resolve_mode(response_mode)
        return await run_tool(
            lambda: releases_service.get_release_citation(
                client,  # type: ignore[arg-type]
                response_mode=mode,
            ),
            data_class=dataclass.RELEASE,
            response_mode=mode,
        )
