"""Release-citation service: the current published data-release citation.

Reads ``/api/releases/?status=published`` (releases are returned newest-first by
version), takes the latest published release, and builds the dataset citation —
``recommended_citation`` + version + dataset DOI + software concept DOI — via
:func:`~kidney_genetics_mcp.services.citation.build_release_citation`. The export
checksum is surfaced when present so a client can pin the exact data snapshot it
cited.
"""

from __future__ import annotations

from typing import Any

from ..client.api_client import ApiClient
from .citation import build_release_citation
from .errors import not_found

#: ``/api/releases/`` path (allowlisted, read-only).
_RELEASES_PATH = "/api/releases/"

#: Release fields surfaced in the citation payload (beyond the citation block).
_RELEASE_DETAIL_FIELDS: tuple[str, ...] = (
    "version",
    "status",
    "release_date",
    "published_at",
    "gene_count",
    "total_evidence_count",
)


async def get_release_citation(
    client: ApiClient,
    *,
    response_mode: str,  # noqa: ARG001 — uniform signature; payload is fixed-size
) -> dict[str, Any]:
    """Return the citation for the current published data release.

    Fetches the published releases (newest-first), takes the latest, and
    assembles its dataset citation (with the software concept DOI) plus the
    export checksum when available.

    Args:
        client: Configured :class:`~kidney_genetics_mcp.client.api_client.ApiClient`.
        response_mode: The resolved response_mode (accepted for a uniform tool
            signature; the citation payload is a single fixed-size record).

    Returns:
        A dict with ``citation`` (the assembled citation block), ``release``
        (key release-metadata fields), and ``export_checksum`` when present.
        ``data_class`` and ``meta`` are attached by ``run_tool``.

    Raises:
        McpToolError: ``not_found`` when no published release exists.
    """
    payload: Any = await client.get(_RELEASES_PATH, params={"status": "published"})

    releases: list[Any] = []
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        releases = payload["data"]
    elif isinstance(payload, list):
        releases = payload

    published = [
        r
        for r in releases
        if isinstance(r, dict) and str(r.get("status") or "").lower() == "published"
    ]
    if not published:
        raise not_found(
            "no published data release is available to cite",
            hint="a release must be published before it can be cited",
        )

    # The endpoint returns releases newest-first (version desc); the first
    # published entry is the current release.
    latest = published[0]

    citation = build_release_citation(latest)
    release_detail = {
        field: latest.get(field) for field in _RELEASE_DETAIL_FIELDS if field in latest
    }

    out: dict[str, Any] = {"citation": citation, "release": release_detail}
    checksum = latest.get("export_checksum")
    if checksum:
        out["export_checksum"] = checksum
    return out
