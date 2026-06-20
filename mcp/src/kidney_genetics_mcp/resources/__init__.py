"""Packaged Markdown documentation resources for the KGDB MCP server.

This subpackage holds the static schema-overview and tool-guide Markdown files
served as MCP resources. It is a package (not a bare directory) so that
``importlib.resources.files("kidney_genetics_mcp.resources")`` can locate the
packaged ``.md`` files at runtime.
"""

from __future__ import annotations
