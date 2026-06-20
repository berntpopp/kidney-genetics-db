"""Gene-family MCP tools.

Registers ``kgdb_resolve_gene``, ``kgdb_search_genes``, ``kgdb_get_gene``, and
``kgdb_get_gene_evidence``. Each tool is thin: it declares typed params + a
docstring, validates/normalizes the response mode, and delegates to its service
via :func:`~kidney_genetics_mcp.services.safe_tool.run_tool`, which attaches the
uniform ``data_class`` + ``meta`` envelope (or an error envelope).
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.contract import EvidenceGroup, EvidenceTier, GeneSortField
from kidney_genetics_mcp.services import dataclass
from kidney_genetics_mcp.services import evidence as evidence_service
from kidney_genetics_mcp.services import genes as genes_service
from kidney_genetics_mcp.services import resolve as resolve_service
from kidney_genetics_mcp.services.safe_tool import run_tool
from kidney_genetics_mcp.services.shaping import ResponseMode, resolve_mode


def register(mcp: FastMCP, client: ApiClient | None) -> None:
    """Register the four gene-family tools on *mcp*.

    Args:
        mcp: The :class:`~fastmcp.FastMCP` application instance.
        client: The :class:`~kidney_genetics_mcp.client.api_client.ApiClient`
            used to communicate with the KGDB REST API, or ``None`` during
            registration-only scenarios (e.g. capability introspection).
    """

    @mcp.tool(
        name="kgdb_resolve_gene",
        annotations={
            "title": "Resolve Gene (free-text/ID → canonical identity)",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_resolve_gene(
        query: str,
        response_mode: ResponseMode | None = None,
    ) -> dict[str, Any]:
        """Resolve a free-text gene name or identifier to a canonical identity.

        Accepts an approved symbol, alias / previous symbol, HGNC id
        (``HGNC:9008``), Ensembl gene id (``ENSG...``), NCBI/Entrez id (bare
        digits), or a UniProt accession, and returns the canonical
        ``{id, hgnc_id, approved_symbol, match_type}`` plus a ``resolve_with``
        handoff naming the exact next call (``kgdb_get_gene`` with the
        ``approved_symbol``). When the query matches multiple genes the tool
        returns an ``ambiguous_query`` error carrying the candidate ``choices``;
        an unknown query returns ``not_found``.

        Args:
            query: The free-text or identifier string to resolve (non-empty).
            response_mode: Accepted for interface consistency; the identity
                payload is already minimal so this does not change the output.

        Returns:
            A dict with ``gene`` (the canonical identity) and ``resolve_with``
            (the explicit handoff to ``kgdb_get_gene``), plus ``data_class`` and
            ``meta``.
        """
        mode = resolve_mode(response_mode)
        return await run_tool(
            lambda: resolve_service.resolve_gene(
                client,  # type: ignore[arg-type]
                query,
                response_mode=mode,
            ),
            data_class=dataclass.GENE_IDENTITY,
            response_mode=mode,
        )

    @mcp.tool(
        name="kgdb_search_genes",
        annotations={
            "title": "Search Genes (filtered)",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_search_genes(
        query: str | None = None,
        tier: EvidenceTier | None = None,
        group: EvidenceGroup | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
        source: str | None = None,
        sort: GeneSortField | None = None,
        page: int = 1,
        page_size: int = 20,
        response_mode: ResponseMode | None = None,
    ) -> dict[str, Any]:
        """Search curated kidney-disease genes with filters, sort, and paging.

        Browses the gene list with optional free-text search and structured
        filters, returning a page of hits each shaped to ``{id,
        approved_symbol, hgnc_id, evidence_score, evidence_tier, evidence_group,
        sources}`` (field-laddered by ``response_mode``) with a per-hit
        ``resolve_with`` handoff to ``kgdb_get_gene``.

        Args:
            query: Free-text search over symbol / HGNC id / tier / group.
            tier: Filter by evidence tier (an ``EvidenceTier`` value).
            group: Filter by evidence group (an ``EvidenceGroup`` value).
            min_score: Minimum evidence score (0–100).
            max_score: Maximum evidence score (0–100).
            source: Restrict to genes with evidence from this source name.
            sort: Sort field (a ``GeneSortField`` value, optionally
                ``-``-prefixed for descending, e.g. ``-evidence_score``).
            page: 1-based page number (default 1).
            page_size: Results per page (default 20).
            response_mode: Response verbosity — ``minimal``/``compact``/
                ``standard``/``full`` (default ``compact``); controls the
                per-hit field set.

        Returns:
            A dict with ``genes`` (the hits), ``pagination`` (``{total, page,
            page_size, page_count, has_more}``), ``guidance``, plus
            ``data_class`` and ``meta``.
        """
        mode = resolve_mode(response_mode)
        return await run_tool(
            lambda: genes_service.search_genes(
                client,  # type: ignore[arg-type]
                query=query,
                tier=tier,
                group=group,
                min_score=min_score,
                max_score=max_score,
                source=source,
                sort=sort,
                page=page,
                page_size=page_size,
                response_mode=mode,
            ),
            data_class=dataclass.GENE,
            response_mode=mode,
        )

    @mcp.tool(
        name="kgdb_get_gene",
        annotations={
            "title": "Get Gene (overview: score, tier, sources)",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_get_gene(
        gene_symbol: str,
        response_mode: ResponseMode | None = None,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fetch a single gene's curated overview by approved symbol.

        Returns the gene's evidence score, tier, group, evidence count,
        contributing sources, score breakdown, and per-source scores
        (field-laddered by ``response_mode``: ``minimal`` = core score fields,
        ``full`` = all). Obtain ``gene_symbol`` from ``kgdb_resolve_gene`` or
        ``kgdb_search_genes``.

        Args:
            gene_symbol: The approved gene symbol (case-insensitive upstream).
            response_mode: Response verbosity — ``minimal``/``compact``/
                ``standard``/``full`` (default ``compact``).
            fields: Optional explicit top-level field allow-list applied on top
                of the mode; identity keys are always retained.

        Returns:
            A dict with the projected gene attributes (and a ``uri``), plus
            ``data_class`` and ``meta``.
        """
        mode = resolve_mode(response_mode)
        return await run_tool(
            lambda: genes_service.get_gene(
                client,  # type: ignore[arg-type]
                gene_symbol,
                response_mode=mode,
                fields=fields,
            ),
            data_class=dataclass.GENE,
            response_mode=mode,
        )

    @mcp.tool(
        name="kgdb_get_gene_evidence",
        annotations={
            "title": "Get Gene Evidence (per-source scored)",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_get_gene_evidence(
        gene_symbol: str,
        sources: list[str] | None = None,
        response_mode: ResponseMode | None = None,
    ) -> dict[str, Any]:
        """Fetch per-source scored evidence records for a gene.

        Returns each evidence record as ``{source_name, source_detail,
        normalized_score, evidence_date, evidence_data}``. The bulky
        ``evidence_data`` JSONB is dropped in ``minimal``/``compact`` and kept in
        ``standard``/``full``. Obtain ``gene_symbol`` from ``kgdb_resolve_gene``
        or ``kgdb_search_genes``.

        Args:
            gene_symbol: The approved gene symbol whose evidence is requested.
            sources: Optional list of ``source_name`` values to keep (others are
                filtered out); ``None`` keeps every source.
            response_mode: Response verbosity — ``minimal``/``compact``/
                ``standard``/``full`` (default ``compact``); controls whether
                ``evidence_data`` is included.

        Returns:
            A dict with ``gene_symbol``, ``evidence`` (the records),
            ``evidence_count``, plus ``data_class`` and ``meta``.
        """
        mode = resolve_mode(response_mode)
        return await run_tool(
            lambda: evidence_service.get_gene_evidence(
                client,  # type: ignore[arg-type]
                gene_symbol,
                sources=sources,
                response_mode=mode,
            ),
            data_class=dataclass.EVIDENCE,
            response_mode=mode,
        )
