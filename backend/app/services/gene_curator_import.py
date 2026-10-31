"""Import Gene Curator's curation export as KGDB drafts (#448).

Contract: backend/contract/gene_curator_export.snapshot.json (export v1; Gene Curator's
docs/EXPORT.md). A Gene Curator entity (scope, gene, entity_key) is one KGDB record:
source gene_curator + gene + disease + MOI + relationship type, with the curation_id as
its current version (external_id), so a re-curation updates the record in place.

Imported records are drafts that a KGDB curator other than the importer must publish
(the existing workflow). A record that left draft, or that a KGDB curator changed since
its last import, is never overwritten: the difference is reported. Unknown classes, MOIs
and relationship types are rejected, not guessed. A full sync (no updated_since) retracts
imported records whose curation Gene Curator no longer returns (hard deletes never appear).
"""

from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ResourceConflictError
from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.models.gene_disease_association import MOI_TERMS
from app.models.gene_disease_association import GeneDiseaseAssociation as GDA
from app.models.gene_disease_association import GeneDiseaseAssociationEvent as Event
from app.models.user import User
from app.schemas.gene_disease_association import (
    AssociationCreate,
    Detectability,
    Diagnostics,
    RecommendedTranscript,
    Resource,
)
from app.services.gene_disease_association_service import _commit_unique, _ensure_unique, _log

logger = get_logger(__name__)

EXPORT_PATH = "/api/v1/export/curations"
SOURCE = "gene_curator"
IMPORT, RETRACT = "gc_import", "gc_retract"  # event actions written only by this importer
# Gene Curator class keys (trimmed, lowercase, spaces/hyphens as underscores) -> KGDB classes
CLASSES = {
    "mendelian": {
        "definitive": "Definitive",
        "strong": "Strong",
        "moderate": "Moderate",
        "limited": "Limited",
        "disputed": "Disputed",
        "refuted": "Refuted",
        "no_known": "No Known Disease Relationship",
        "no_known_disease_relationship": "No Known Disease Relationship",  # the label as a key
    },
    # Provisional tiers (#473), imported as-is from KGDB's SUSCEPTIBILITY_STRENGTHS
    "susceptibility": {
        "established": "Established association",
        "likely": "Likely association",
        "uncertain": "Uncertain association",
    },
}
UNDETERMINED_MOI = {"", "undetermined"}  # moi_hpo_id is null for these; anything else is unmapped
# What an import writes and compares (everything a curator can edit)
FIELDS = (
    "disease_id",
    "disease_name",
    "relationship_type",
    "evidence_strength",
    "moi",
    "methodology",
    "methodology_version",
    "external_id",
    "external_url",
    "external_curator",
    "external_reviewer",
    "scores",
    "diagnostics",
    "citations",
    "evidence_summary",
)


def fetch_export(updated_since: datetime | None) -> list[dict[str, Any]]:
    """Every page of the export for the configured scope (member token: archived rows too)."""
    if not settings.GENE_CURATOR_URL or not settings.GENE_CURATOR_TOKEN:
        raise HTTPException(503, "Set GENE_CURATOR_URL and GENE_CURATOR_TOKEN to import")
    params: dict[str, Any] = {"scope_name": settings.GENE_CURATOR_SCOPE, "limit": 500}
    if updated_since:
        params["updated_since"] = updated_since.isoformat()
    headers = {"Authorization": f"Bearer {settings.GENE_CURATOR_TOKEN.get_secret_value()}"}

    @retry_with_backoff(RetryConfig(max_retries=3))
    def get_page(client: httpx.Client) -> dict[str, Any]:
        response = client.get(EXPORT_PATH, params=params)
        response.raise_for_status()
        return response.json()

    items: list[dict[str, Any]] = []
    try:
        with httpx.Client(base_url=settings.GENE_CURATOR_URL, headers=headers, timeout=60) as c:
            while True:
                page = get_page(c)
                if page.get("export_version") != "1":
                    raise HTTPException(
                        502,
                        f"Unsupported Gene Curator export_version {page.get('export_version')!r}",
                    )
                items += page["items"]
                if not page.get("next_cursor"):
                    return items
                params["cursor"] = page["next_cursor"]
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Gene Curator export failed: {e}") from e


def _key(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _clean(value: Any) -> Any:
    """Drop blank optional keys (null or "") before validating, as Gene Curator advises."""
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items() if v is not None and v != ""}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def _known(model: type[BaseModel], data: dict[str, Any], path: str, dropped: list[str]) -> Any:
    """Keep the keys KGDB's strict Diagnostics schema has; report the rest (#474)."""
    dropped += [f"{path}.{k}" for k in data if k not in model.model_fields]
    return {k: v for k, v in data.items() if k in model.model_fields}


def _tool(text: Any) -> dict[str, Any] | None:
    """`name | url | pmid_or_doi` evidence-table text -> KGDB DetectabilityTool."""
    name, url, ref = ([part.strip() for part in str(text).split(" | ")] + ["", ""])[:3]
    return {"name": name, "url": url or None, "pmid_or_doi": ref or None} if name else None


def _diagnostics(evidence: dict[str, Any], dropped: list[str]) -> dict[str, Any] | None:
    """Reshape evidence.diagnostics per Gene Curator's KGDB mapping (kidney-genetics/README)."""
    notes = evidence.get("diagnostics_notes") or {}
    dropped += [f"diagnostics_notes.{k}" for k, v in _clean(notes).items()]
    raw = _clean(evidence.get("diagnostics") or {})
    if not raw:
        return None
    out = _known(Diagnostics, raw, "diagnostics", dropped)
    if transcript := out.get("recommended_transcript"):
        transcript = {"mane_status": "not_checked", **transcript}
        path = "diagnostics.recommended_transcript"
        out["recommended_transcript"] = _known(RecommendedTranscript, transcript, path, dropped)
    else:
        out.pop("recommended_transcript", None)  # every key blank
    rows = []
    for row in out.get("detectability", []):
        row = _known(Detectability, row, "diagnostics.detectability[]", dropped)
        row["tools"] = [t for t in map(_tool, row.get("tools", [])) if t]
        rows.append(row)
    resources = []
    for resource in out.get("resources", []):
        resource = dict(resource)
        verified = {"method": resource.pop("verified_method", None)}
        verified["date"] = resource.pop("verified_date", None)
        resource["verified"] = verified
        resources.append(_known(Resource, resource, "diagnostics.resources[]", dropped))
    return {**out, "detectability": rows, "resources": resources}


def _values(item: dict[str, Any], dropped: list[str]) -> dict[str, Any]:
    """Map an export row to KGDB fields; ValueError for anything KGDB cannot hold as is."""
    relationship = item.get("relationship_type") or "mendelian"
    if relationship not in CLASSES:
        raise ValueError(f"unknown relationship_type {relationship!r}")
    strength = CLASSES[relationship].get(_key(item.get("final_classification")))
    if strength is None:
        raise ValueError(
            f"classification {item.get('final_classification')!r} is not a {relationship} "
            f"class KGDB supports ({', '.join(CLASSES[relationship])})"
        )
    moi = item.get("moi_hpo_id")
    if moi is None and _key(item.get("mode_of_inheritance")) not in UNDETERMINED_MOI:
        raise ValueError(f"mode of inheritance {item.get('mode_of_inheritance')!r} has no HPO term")
    if moi is not None and moi.upper() not in MOI_TERMS:
        raise ValueError(f"unknown MOI {moi!r}")
    evidence = item.get("evidence") or {}
    methodology = item.get("methodology") or {}
    scores = {
        "genetic": item.get("genetic_score"),
        "experimental": item.get("experimental_score"),
        "total": item.get("total_score"),
    }
    try:
        payload = AssociationCreate(
            gene_symbol=item["approved_symbol"],
            disease_id=item.get("mondo_id") or "",
            disease_name=item.get("disease_name") or "",
            relationship_type=relationship,
            evidence_strength=strength,
            moi=moi.upper() if moi else None,
            methodology=methodology.get("schema_name") or None,
            methodology_version=(
                str(methodology["version"]) if methodology.get("version") is not None else None
            ),
            source=SOURCE,
            external_id=str(item["curation_id"]),
            external_url=item["url"],
            external_curator=item.get("curator_name") or None,
            external_reviewer=item.get("reviewer_name") or None,
            scores=scores if any(v is not None for v in scores.values()) else None,
            diagnostics=_diagnostics(evidence, dropped),
            citations=item.get("pmids") or [],
            evidence_summary=evidence.get("evidence_summary") or None,
        )
    except PydanticValidationError as e:
        reasons = (f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())
        raise ValueError("; ".join(reasons)) from e
    return payload.model_dump(mode="json", include=set(FIELDS))


def _existing(db: Session, gene: Gene, item: dict[str, Any]) -> GDA | None:
    """The record of this curation, or of its entity after a re-curation (sync note 3)."""
    record = db.query(GDA).filter_by(source=SOURCE, external_id=str(item["curation_id"])).first()
    if record:
        return record
    moi = (item.get("moi_hpo_id") or "").upper() or None
    return (
        db.query(GDA)
        .filter(
            GDA.source == SOURCE,
            GDA.gene_id == gene.id,
            GDA.disease_id == (item.get("mondo_id") or "").strip().upper(),
            GDA.relationship_type == (item.get("relationship_type") or "mendelian"),
            GDA.moi.is_(None) if moi is None else GDA.moi == moi,
        )
        .first()
    )


def _last_import(db: Session, record: GDA) -> dict[str, Any] | None:
    row = (
        db.query(Event.snapshot)
        .filter(Event.association_id == record.id, Event.action == IMPORT)
        .order_by(Event.id.desc())
        .first()
    )
    return row.snapshot if row else None


def _blocked(db: Session, record: GDA) -> str | None:
    """Why an update must not overwrite this record, or None."""
    if record.status != "draft":
        return f"record is {record.status}; return it to draft to take the Gene Curator update"
    snapshot = _last_import(db, record)
    if snapshot is None:
        return "record was not created by the Gene Curator import"
    if any(snapshot.get(f) != getattr(record, f) for f in FIELDS):
        return "a KGDB curator edited the record since its last import"
    return None


def _import_row(
    db: Session, item: dict[str, Any], user: User, report: dict[str, Any], matched: set[int]
) -> None:
    ref = {
        "curation_id": str(item["curation_id"]),
        "gene_symbol": item.get("approved_symbol"),
        "hgnc_id": item.get("hgnc_id"),
        "entity_key": item.get("entity_key"),
    }
    gene = db.query(Gene).filter(Gene.hgnc_id == item.get("hgnc_id")).first()
    if gene is None:
        report["genes_not_in_kgdb"].append(ref)
        return
    record = _existing(db, gene, item)
    if record is not None:
        matched.add(record.id)  # the entity still exists, even if this row is rejected
    dropped: list[str] = []
    try:
        values = _values(item, dropped)
    except ValueError as e:
        report["rejected"].append({**ref, "reason": str(e)})
        return
    if dropped:
        report["dropped_fields"].append({**ref, "fields": sorted(set(dropped))})
    try:
        if record is None:
            record = GDA(
                gene_id=gene.id, curator_id=user.id, status="draft", source=SOURCE, **values
            )
            with db.no_autoflush:  # the new record must not match itself
                _ensure_unique(db, record)
            db.add(record)
            _commit_unique(db, record, IMPORT, user)
            matched.add(record.id)
            report["created"].append({**ref, "record_id": record.id})
            return
        differences = {
            f: {"kgdb": getattr(record, f), "gene_curator": values[f]}
            for f in FIELDS
            if getattr(record, f) != values[f]
        }
        if not differences:
            report["unchanged"] += 1
            return
        if reason := _blocked(db, record):
            conflict = {**ref, "record_id": record.id, "reason": reason}
            report["conflicts"].append({**conflict, "differences": differences})
            return
        for field, value in values.items():
            setattr(record, field, value)
        with db.no_autoflush:
            _ensure_unique(db, record)
        _commit_unique(db, record, IMPORT, user)
        report["updated"].append({**ref, "record_id": record.id, "fields": sorted(differences)})
    except ResourceConflictError as e:
        db.rollback()
        report["conflicts"].append({**ref, "record_id": record.id, "reason": e.message})


def _retract(db: Session, record: GDA, user: User, reason: str, report: dict[str, Any]) -> None:
    """Take the record offline (draft) and trace why; content stays for the curator to see."""
    last = db.query(Event.action).filter(Event.association_id == record.id)
    if record.status == "draft" and last.order_by(Event.id.desc()).first() == (RETRACT,):
        return  # already retracted by an earlier sync
    was = record.status
    record.status = "draft"
    record.submitted_at = None
    record.published_at = None
    _log(db, record, RETRACT, user)
    db.commit()
    report["retracted"].append(
        {"record_id": record.id, "curation_id": record.external_id, "was": was, "reason": reason}
    )


def import_export(
    db: Session, items: list[dict[str, Any]], user: User, *, full: bool
) -> dict[str, Any]:
    """Upsert export rows as drafts; ``full`` (the whole export) also retracts absent ones."""
    report: dict[str, Any] = {
        "full_sync": full,
        "rows": len(items),
        "created": [],
        "updated": [],
        "unchanged": 0,
        "retracted": [],
        "conflicts": [],
        "rejected": [],
        "genes_not_in_kgdb": [],
        "dropped_fields": [],
    }
    rows = {str(i["curation_id"]): i for i in items}  # overlapping sync windows repeat rows
    active = {cid: i for cid, i in rows.items() if i.get("status") == "active"}
    matched: set[int] = set()
    for item in active.values():
        _import_row(db, item, user, report, matched)
    for cid, item in rows.items():
        # A replaced curation is handled by its active successor (sync note 3)
        if item.get("status") == "archived" and item.get("archive_reason") != (
            "Replaced by new active curation"
        ):
            record = db.query(GDA).filter_by(source=SOURCE, external_id=cid).first()
            if record:
                reason = item.get("archive_reason") or "archived in Gene Curator"
                _retract(db, record, user, reason, report)
    if full:
        # Deletions never appear in the feed (sync note 4): retract imports no longer returned
        absent = db.query(GDA).filter(
            GDA.source == SOURCE,
            GDA.id.in_(select(Event.association_id).where(Event.action == IMPORT)),
            GDA.id.notin_(matched),
            GDA.external_id.notin_(list(active)),
        )
        for record in absent.all():
            _retract(db, record, user, "no longer in the Gene Curator export", report)
    logger.sync_info(
        "Gene Curator import finished",
        full_sync=full,
        rows=len(items),
        **{k: len(v) for k, v in report.items() if isinstance(v, list)},
    )
    return report
