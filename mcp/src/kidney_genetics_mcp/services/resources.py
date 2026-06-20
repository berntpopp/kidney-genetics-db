"""Static MCP resource loading and registration (packaged Markdown docs).

Two static documentation resources are served to MCP clients:

- ``kidney-genetics://schema/overview`` — the domain / data-model primer.
- ``kidney-genetics://schema/tool-guide`` — the tool inventory, canonical
  workflow, citation contract, and safety disclaimer.

Both are packaged Markdown files under :mod:`kidney_genetics_mcp.resources`,
loaded via :mod:`importlib.resources` so they resolve correctly from an installed
wheel. :func:`load_resource` is also used by the capabilities descriptor to
content-hash the tool guide so a warm client can skip re-reading it.
"""

from __future__ import annotations

import importlib.resources
from typing import TYPE_CHECKING

from kidney_genetics_mcp.services.errors import McpToolError

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastmcp import FastMCP

#: Mapping of well-known resource URI → packaged Markdown filename.
RESOURCE_URIS: dict[str, str] = {
    "kidney-genetics://schema/overview": "schema_overview.md",
    "kidney-genetics://schema/tool-guide": "tool_guide.md",
}

#: MIME type advertised for the Markdown resources.
RESOURCE_MIME_TYPE = "text/markdown"


def load_resource(uri: str) -> str:
    """Load a packaged Markdown resource by its URI.

    Args:
        uri: One of the well-known ``kidney-genetics://`` resource URIs defined
            in :data:`RESOURCE_URIS`.

    Returns:
        The UTF-8 text content of the corresponding Markdown file.

    Raises:
        McpToolError: With code ``not_found`` when *uri* is not a known resource.
    """
    if uri not in RESOURCE_URIS:
        raise McpToolError(
            "not_found",
            f"Unknown resource URI: {uri!r}. Available URIs: {sorted(RESOURCE_URIS)}",
        )
    filename = RESOURCE_URIS[uri]
    resource_pkg = importlib.resources.files("kidney_genetics_mcp.resources")
    return resource_pkg.joinpath(filename).read_text(encoding="utf-8")


def register_resources(mcp: FastMCP) -> None:
    """Register the static Markdown documentation resources on *mcp*.

    Registers each URI in :data:`RESOURCE_URIS` as a ``text/markdown`` MCP
    resource whose body is the packaged Markdown file, using the FastMCP
    ``mcp.resource(uri, ...)`` decorator idiom (FastMCP 3.x).

    Args:
        mcp: The FastMCP application instance to register the resources on.
    """

    def _make_resource(resource_uri: str) -> Callable[[], str]:
        def _resource() -> str:
            return load_resource(resource_uri)

        return _resource

    for uri in RESOURCE_URIS:
        mcp.resource(uri, mime_type=RESOURCE_MIME_TYPE)(_make_resource(uri))
