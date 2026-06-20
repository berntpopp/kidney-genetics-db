"""Source-provenance service: merge annotation + data sources into one list.

KGDB exposes two complementary source registries:

- ``/api/annotations/sources`` — the descriptive-annotation source registry
  (``source_name``, ``display_name``, ``version``, ``url``, ``last_update``).
- ``/api/datasources/`` — the evidence data-source registry with per-source
  counts (``gene_count``, ``evidence_count``, ``last_updated``).

This service merges both into a single per-source provenance record so a client
can cite *one* list — the citation provenance contract — instead of reconciling
two registries. Records are keyed by source name; counts from the datasources
registry enrich the matching annotation-source record, and any datasource with
no annotation-source twin is appended so nothing is silently dropped.
"""

from __future__ import annotations

from typing import Any

from ..client.api_client import ApiClient
from .shaping import project_fields

#: ``/api/annotations/sources`` path (allowlisted, read-only).
_ANNOTATION_SOURCES_PATH = "/api/annotations/sources"
#: ``/api/datasources/`` path (allowlisted, read-only).
_DATASOURCES_PATH = "/api/datasources/"

#: Per-mode field projection for each merged provenance record.
#: ``minimal ⊊ compact ⊊ standard ⊊ full``; ``full=()`` keeps every field.
_FIELDS_BY_MODE: dict[str, tuple[str, ...]] = {
    "minimal": ("source_name", "display_name", "version"),
    "compact": (
        "source_name",
        "display_name",
        "version",
        "url",
        "last_update",
    ),
    "standard": (
        "source_name",
        "display_name",
        "version",
        "url",
        "last_update",
        "gene_count",
        "evidence_count",
    ),
    "full": (),
}


def _norm_name(name: Any) -> str:
    """Return a case-insensitive merge key for a source name.

    Args:
        name: A raw ``source_name`` / ``name`` value.

    Returns:
        The lower-cased, stripped string used to align the two registries.
    """
    return str(name or "").strip().lower()


def _merge(
    annotation_sources: Any,
    datasources: Any,
) -> list[dict[str, Any]]:
    """Merge the annotation-source and datasource registries by name.

    Args:
        annotation_sources: The ``/api/annotations/sources`` payload (a list).
        datasources: The ``/api/datasources/`` payload (a JSON:API dict whose
            ``data.sources`` holds the per-source records).

    Returns:
        A list of merged provenance records (annotation-source records enriched
        with datasource counts, plus datasource-only records appended).
    """
    # Index datasource counts by normalized name.
    ds_by_name: dict[str, dict[str, Any]] = {}
    ds_list: list[Any] = []
    if isinstance(datasources, dict):
        inner = datasources.get("data")
        if isinstance(inner, dict) and isinstance(inner.get("sources"), list):
            ds_list = inner["sources"]
    for ds in ds_list:
        if not isinstance(ds, dict):
            continue
        ds_by_name[_norm_name(ds.get("name"))] = ds

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    ann_list = annotation_sources if isinstance(annotation_sources, list) else []
    for src in ann_list:
        if not isinstance(src, dict):
            continue
        key = _norm_name(src.get("source_name"))
        seen.add(key)
        record: dict[str, Any] = {
            "source_name": src.get("source_name"),
            "display_name": src.get("display_name"),
            "version": src.get("version"),
            "url": src.get("url"),
            "last_update": src.get("last_update"),
        }
        ds = ds_by_name.get(key)
        if ds is not None:
            ds_stats = ds.get("stats")
            if isinstance(ds_stats, dict):
                record["gene_count"] = ds_stats.get("gene_count")
                record["evidence_count"] = ds_stats.get("evidence_count")
        merged.append(record)

    # Append datasource-only entries (no annotation-source twin) so the
    # provenance list never silently drops a registered evidence source.
    for key, ds in ds_by_name.items():
        if key in seen:
            continue
        raw_stats = ds.get("stats")
        stats: dict[str, Any] = raw_stats if isinstance(raw_stats, dict) else {}
        merged.append(
            {
                "source_name": ds.get("name"),
                "display_name": ds.get("display_name"),
                "version": None,
                "url": ds.get("url"),
                "last_update": stats.get("last_updated"),
                "gene_count": stats.get("gene_count"),
                "evidence_count": stats.get("evidence_count"),
            }
        )

    return merged


async def list_sources(
    client: ApiClient,
    *,
    response_mode: str,
) -> dict[str, Any]:
    """Return the merged source-provenance list, projected per *response_mode*.

    Args:
        client: Configured :class:`~kidney_genetics_mcp.client.api_client.ApiClient`.
        response_mode: The resolved response_mode driving field projection.

    Returns:
        A dict with ``sources`` (the merged, projected provenance records) and
        ``total`` (the unprojected count). ``data_class`` and ``meta`` are
        attached by ``run_tool``.
    """
    annotation_sources, datasources = (
        await client.get(_ANNOTATION_SOURCES_PATH),
        await client.get(_DATASOURCES_PATH),
    )
    merged = _merge(annotation_sources, datasources)
    projected = [project_fields(rec, _FIELDS_BY_MODE, response_mode) for rec in merged]
    return {"sources": projected, "total": len(merged)}
