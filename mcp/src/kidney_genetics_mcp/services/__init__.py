"""Service layer for the Kidney-Genetics-DB MCP server.

Cross-cutting helpers (errors, shaping, dataclass, citation, safe_tool) live
here alongside the per-domain service modules added by later waves. This package
deliberately exports no cross-imports so domain modules can be added without
merge conflicts; import the helpers directly from their submodules.
"""

from __future__ import annotations
