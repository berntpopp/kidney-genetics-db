"""Annotations-family tools: descriptive annotations, constraint, interactions.

Registers ``kgdb_get_gene_annotations``, ``kgdb_get_constraint_summary``, and
``kgdb_get_interaction_partners``. All three key by the *numeric* gene database
id (not the symbol); callers obtain it from ``kgdb_resolve_gene`` /
``kgdb_search_genes``.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

import kidney_genetics_mcp.services.annotations as annotations_service
import kidney_genetics_mcp.services.network as network
from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.contract import AnnotationSource
from kidney_genetics_mcp.services import dataclass
from kidney_genetics_mcp.services.safe_tool import run_tool
from kidney_genetics_mcp.services.shaping import ResponseMode, resolve_mode


def register(mcp: FastMCP, client: ApiClient | None) -> None:
    """Register the annotations-family tools on *mcp*.

    Args:
        mcp: The :class:`~fastmcp.FastMCP` application instance.
        client: The :class:`~kidney_genetics_mcp.client.api_client.ApiClient`
            used to reach the KGDB REST API, or ``None`` during
            registration-only scenarios (e.g. capability introspection).
    """

    @mcp.tool(
        name="kgdb_get_gene_annotations",
        annotations={
            "title": "Get Gene Descriptive Annotations",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_get_gene_annotations(
        gene_id: int,
        source: AnnotationSource | None = None,
        response_mode: ResponseMode | None = None,
    ) -> dict[str, Any]:
        """Return descriptive (non-scored) annotations for a gene by numeric id.

        Fetches the per-source descriptive annotations from the 10 annotation
        sources (HGNC, gnomAD, ClinVar, Ensembl, UniProt, GTEx, MPO/MGI,
        STRING-PPI, Descartes, HPO). Each source yields one or more records with
        a free-form ``data`` blob, a ``version``, source ``metadata``, and an
        ``updated_at`` timestamp.

        ``gene_id`` is the NUMERIC KGDB gene database id — obtain it from
        ``kgdb_resolve_gene`` or ``kgdb_search_genes`` (it is NOT the gene
        symbol or HGNC id).

        Token discipline: ``response_mode`` controls how much of each record's
        ``data`` blob is surfaced — ``minimal`` returns only source names +
        versions, ``compact`` (default) returns a small per-record summary,
        ``standard`` adds the full ``data`` blob, and ``full`` returns every
        field verbatim. The result is then trimmed to the mode's char budget.

        Args:
            gene_id: The numeric KGDB gene database id (from
                ``kgdb_resolve_gene`` / ``kgdb_search_genes``).
            source: Optional annotation-source filter (one of the 10 sources).
                Omit to return every source.
            response_mode: Response verbosity — ``minimal``, ``compact``,
                ``standard``, or ``full``. Defaults to ``compact``.

        Returns:
            A dict with ``gene``, ``annotations`` (a ``{source: [record, ...]}``
            map), ``uri``, ``data_class``, and ``meta``.
        """
        mode = resolve_mode(response_mode)
        return await run_tool(
            lambda: annotations_service.get_gene_annotations(
                client,  # type: ignore[arg-type]
                gene_id=gene_id,
                source=source,
                response_mode=mode,
            ),
            data_class=dataclass.ANNOTATION,
            response_mode=mode,
        )

    @mcp.tool(
        name="kgdb_get_constraint_summary",
        annotations={
            "title": "Get Gene Constraint Summary",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_get_constraint_summary(
        gene_id: int,
        response_mode: ResponseMode | None = None,
    ) -> dict[str, Any]:
        """Return the fast gnomAD-constraint summary for a gene by numeric id.

        A single fast lookup (from the ``gene_annotations_summary`` materialized
        view) returning the headline gnomAD constraint metrics — pLI, oe_lof and
        its confidence bounds (oe_lof_upper / oe_lof_lower), the LoF/missense/
        synonymous Z-scores (lof_z / mis_z / syn_z), and oe_mis / oe_syn — plus
        the canonical cross-reference identifiers (NCBI gene id, Ensembl gene id,
        and MANE Select transcript).

        ``gene_id`` is the NUMERIC KGDB gene database id — obtain it from
        ``kgdb_resolve_gene`` or ``kgdb_search_genes``.

        Args:
            gene_id: The numeric KGDB gene database id (from
                ``kgdb_resolve_gene`` / ``kgdb_search_genes``).
            response_mode: Response verbosity — ``minimal``, ``compact``,
                ``standard``, or ``full``. The summary is small and fixed, so the
                mode is echoed in ``meta`` but the field set does not change.
                Defaults to ``compact``.

        Returns:
            A dict with ``gene``, ``identifiers``, ``constraint``, ``uri``,
            ``data_class``, and ``meta``.
        """
        mode = resolve_mode(response_mode)
        return await run_tool(
            lambda: annotations_service.get_constraint_summary(
                client,  # type: ignore[arg-type]
                gene_id=gene_id,
                response_mode=mode,
            ),
            data_class=dataclass.ANNOTATION,
            response_mode=mode,
        )

    @mcp.tool(
        name="kgdb_get_interaction_partners",
        annotations={
            "title": "Get STRING Interaction Partners",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_get_interaction_partners(
        gene_id: int,
        min_string_score: int = 400,
        limit: int = 25,
        response_mode: ResponseMode | None = None,
    ) -> dict[str, Any]:
        """Return ranked STRING-PPI interaction partners for a gene by numeric id.

        Reads the locally-stored STRING physical-interaction record for the gene
        (no live external call, no graph build), filters partners by STRING
        combined score, ranks them descending by score, and returns the top
        partners. Each partner carries a ``resolve_with`` directive pointing at
        ``kgdb_get_gene`` so the partner symbol can be chased back into the gene
        tools. A ``summary`` block reports the gene's total interaction count,
        PPI degree, and PPI percentile when present.

        ``gene_id`` is the NUMERIC KGDB gene database id — obtain it from
        ``kgdb_resolve_gene`` or ``kgdb_search_genes``.

        Args:
            gene_id: The numeric KGDB gene database id (from
                ``kgdb_resolve_gene`` / ``kgdb_search_genes``).
            min_string_score: Minimum STRING combined score (0-1000) a partner
                must meet to be included. Defaults to ``400``.
            limit: Maximum number of partners to return. Defaults to ``25``.
            response_mode: Response verbosity — ``minimal``, ``compact``,
                ``standard``, or ``full``. Defaults to ``compact``.

        Returns:
            A dict with ``gene``, ``summary``, ``partners`` (each carrying
            ``resolve_with``), ``uri``, ``data_class``, and ``meta``.
        """
        mode = resolve_mode(response_mode)
        return await run_tool(
            lambda: network.get_interaction_partners(
                client,  # type: ignore[arg-type]
                gene_id=gene_id,
                min_string_score=min_string_score,
                limit=limit,
                response_mode=mode,
            ),
            data_class=dataclass.INTERACTION,
            response_mode=mode,
        )
