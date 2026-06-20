"""Tool module: kgdb_get_capabilities — server discovery and metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kidney_genetics_mcp.services import dataclass
from kidney_genetics_mcp.services.capabilities import build_capabilities
from kidney_genetics_mcp.services.safe_tool import run_tool

if TYPE_CHECKING:
    from fastmcp import FastMCP

    from kidney_genetics_mcp.client.api_client import ApiClient


def register(mcp: FastMCP, client: ApiClient | None) -> None:  # noqa: ARG001
    """Register the kgdb_get_capabilities tool on the given FastMCP instance.

    Args:
        mcp: The FastMCP application instance to register the tool on.
        client: The API client (unused for this tool; may be ``None``). The
            capabilities descriptor is assembled from server-local data with no
            API call.
    """

    @mcp.tool(
        name="kgdb_get_capabilities",
        annotations={
            "title": "Kidney-Genetics: Capabilities & Tool Inventory",
            "readOnlyHint": True,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    async def kgdb_get_capabilities() -> dict[str, Any]:
        """Return server capabilities, tool inventory, and operational metadata.

        Discover what the Kidney-Genetics-DB MCP server can do: canonical
        workflows, the full 11-tool inventory with per-tool summaries, the
        enum-constrained filterable fields per tool, supported payload modes with
        character budgets, pagination limits, the canonical identifier forms, the
        citation contract, error codes (with one worked example each), the
        data-class taxonomy, v1 exclusions, safety notices, and the two packaged
        documentation resources.

        Calling this is RECOMMENDED for orientation in a new/cold session but is
        OPTIONAL: tools with enum-constrained filters advertise them in
        ``filterable_fields``, so many valid calls can be built without a cold
        capabilities load. A warm client should compare the returned
        ``capabilities_version`` content hash and skip re-fetching this
        descriptor when it is unchanged, and inspect ``descriptor_chars`` (also
        echoed as ``meta.descriptor_chars``) for the current serialized size. No
        arguments are required and NO API call is made — the response is
        assembled from server-local data.

        Returns:
            A dict with keys ``canonical_workflows``, ``tools``,
            ``filterable_fields`` (per-tool valid filter params + their allowed
            enum values — read this to construct valid calls), ``payload_modes``,
            ``limits``, ``identifiers``, ``pagination_semantics``,
            ``citation_contract``, ``error_codes``, ``data_classes``,
            ``exclusions``, ``safety``, ``resources``, ``concept_doi``,
            ``capabilities_version`` (a content hash a warm client can compare to
            skip re-fetching), ``descriptor_chars``, ``data_class``, and
            ``meta``.
        """

        async def handler() -> dict[str, Any]:
            descriptor = build_capabilities()
            descriptor["_meta"] = {"descriptor_chars": descriptor["descriptor_chars"]}
            return descriptor

        return await run_tool(
            handler,
            data_class=dataclass.OPERATIONAL_METADATA,
            response_mode="full",
        )
