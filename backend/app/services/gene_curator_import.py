"""One-shot import of an uploaded Gene Curator export as KGDB drafts (#448).

Curations made in Gene Curator are exported once and uploaded here; from then on they
live and are edited only in KGDB, and Gene Curator never updates or retracts them. KGDB
never calls Gene Curator. The upload must match the pinned export v1 schema
(backend/contract/gene_curator_export.snapshot.json); fields added within v1 are ignored.

Each row becomes a draft authored by the inactive `gene-curator-import` account, so one
KGDB curator can take it over, submit and publish it. A curation_id already imported is
skipped. Unknown classes, MOIs and relationship types are rejected, not guessed.
"""

import json
import secrets
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceConflictError
from app.core.exceptions import ValidationError as DomainValidationError
from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.models.gene import Gene
from app.models.gene_disease_association import MOI_TERMS
from app.models.gene_disease_association import GeneDiseaseAssociation as GDA
from app.models.user import User
from app.schemas.gene_disease_association import (
    AssociationCreate,
    Detectability,
    Diagnostics,
    RecommendedTranscript,
    Resource,
)
from app.services.gene_disease_association_service import IMPORT_USERNAME, _commit_unique

logger = get_logger(__name__)

SNAPSHOT = Path(__file__).resolve().parents[2] / "contract" / "gene_curator_export.snapshot.json"
SCHEMAS: dict[str, Any] = json.loads(SNAPSHOT.read_text())["schemas"]
MAX_UPLOAD = 20 * 1024 * 1024
SOURCE = "gene_curator"
IMPORT = "gc_import"
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
SCOPE = "kidney-genetics"  # the only Gene Curator scope KGDB imports
UNDETERMINED_MOI = {"", "undetermined"}  # moi_hpo_id is null for these; anything else is unmapped


def _parses(parse: Callable[[str], Any]) -> Callable[[str], bool]:
    def check(value: str) -> bool:
        try:
            parse(value)
            return True
        except ValueError:
            return False

    return check


_TYPES: dict[str, Callable[[Any], bool]] = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, int | float) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
}
_FORMATS = {"uuid": _parses(UUID), "date-time": _parses(datetime.fromisoformat)}


def schema_errors(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Check value against the pinned schema: the JSON Schema subset its OpenAPI uses.

    Undeclared properties pass (additive v1 fields)."""
    if "$ref" in schema:
        return schema_errors(value, SCHEMAS[schema["$ref"].rsplit("/", 1)[1]], path)
    if "anyOf" in schema:
        if any(not schema_errors(value, option, path) for option in schema["anyOf"]):
            return []
        return [f"{path}: matches no allowed type"]
    if "const" in schema and value != schema["const"]:
        return [f"{path}: must be {schema['const']!r}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}: must be one of {schema['enum']}"]
    kind = schema.get("type")
    if kind and not _TYPES[kind](value):
        return [f"{path}: expected {kind}"]
    fmt = schema.get("format", "")
    if kind == "string" and fmt in _FORMATS and not _FORMATS[fmt](value):
        return [f"{path}: not a {fmt}"]
    if kind == "array":
        item = schema.get("items", {})
        return [e for i, v in enumerate(value) for e in schema_errors(v, item, f"{path}[{i}]")]
    if kind == "object":
        errors = [f"{path}.{k}: required" for k in schema.get("required", []) if k not in value]
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                errors += schema_errors(value[key], sub, f"{path}.{key}")
        return errors
    return []


def parse_export(content: bytes) -> list[dict[str, Any]]:
    """The rows of an uploaded export page, or list of pages; 422 unless it matches v1."""
    if len(content) > MAX_UPLOAD:
        raise DomainValidationError("file", f"larger than {MAX_UPLOAD // 2**20} MB")
    try:
        doc = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as e:
        raise DomainValidationError("file", f"not JSON ({e})") from e
    pages = doc if isinstance(doc, list) else [doc]
    page_schema = {"$ref": "#/components/schemas/CurationExportPage"}
    errors = [e for i, p in enumerate(pages) for e in schema_errors(p, page_schema, f"$[{i}]")]
    if errors:
        shown = "; ".join(errors[:20]) + (
            f"; ... {len(errors) - 20} more" if len(errors) > 20 else ""
        )
        raise DomainValidationError(
            "file", f"not a Gene Curator export v1: {shown}", context={"errors": errors[:20]}
        )
    return [item for page in pages for item in page["items"]]


def import_account(db: Session) -> User:
    """The inactive author of imported drafts; it cannot log in (random, discarded password)."""
    user = db.query(User).filter(User.username == IMPORT_USERNAME).first()
    if user is None:
        new = User(
            username=IMPORT_USERNAME,
            email=f"{IMPORT_USERNAME}@kidney-genetics.local",
            full_name="Gene Curator import",
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            role="viewer",
            is_active=False,
        )
        db.add(new)
        try:
            db.commit()
        except IntegrityError:  # a concurrent upload created it first
            db.rollback()
        user = db.query(User).filter(User.username == IMPORT_USERNAME).one()
    if user.is_active or user.role != "viewer":
        raise ResourceConflictError("User", f"{IMPORT_USERNAME} must be an inactive viewer account")
    return user


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
    """Keep the keys KGDB's strict Diagnostics schema has; report the rest."""
    dropped += [f"{path}.{k}" for k in data if k not in model.model_fields]
    return {k: v for k, v in data.items() if k in model.model_fields}


def _tool(text: Any) -> dict[str, Any] | None:
    """`name | url | pmid_or_doi` evidence-table text -> KGDB DetectabilityTool."""
    if not isinstance(text, str):
        raise ValueError("evidence.diagnostics.detectability[].tools[] must be text")
    name, url, ref = ([part.strip() for part in text.split(" | ")] + ["", ""])[:3]
    return {"name": name, "url": url or None, "pmid_or_doi": ref or None} if name else None


TRANSCRIPT = ".diagnostics.recommended_transcript"


def _shaped(value: Any, kind: type, path: str) -> Any:
    """The evidence is free JSON in the export: check each part before reshaping it."""
    if not isinstance(value, kind):
        raise ValueError(f"evidence{path} must be a{'n object' if kind is dict else ' list'}")
    return value


def _diagnostics(evidence: dict[str, Any], dropped: list[str]) -> dict[str, Any] | None:
    """Reshape evidence.diagnostics per Gene Curator's KGDB mapping (kidney-genetics/README)."""
    notes = _clean(_shaped(evidence.get("diagnostics_notes") or {}, dict, ".diagnostics_notes"))
    raw = _clean(_shaped(evidence.get("diagnostics") or {}, dict, ".diagnostics"))
    if note := notes.pop("detectability_note", None):
        raw["detectability_note"] = note
    if via := notes.pop("transcript_verified_via", None):
        raw["recommended_transcript"] = {
            **_shaped(raw.get("recommended_transcript", {}), dict, TRANSCRIPT),
            "verified_via": via,
        }
    dropped += [f"diagnostics_notes.{k}" for k in notes]
    if not raw:
        return None
    out = _known(Diagnostics, raw, "diagnostics", dropped)
    if transcript := out.get("recommended_transcript"):
        transcript = {"mane_status": "not_checked", **_shaped(transcript, dict, TRANSCRIPT)}
        out["recommended_transcript"] = _known(
            RecommendedTranscript, transcript, TRANSCRIPT[1:], dropped
        )
    else:
        out.pop("recommended_transcript", None)  # every key blank
    rows = []
    for row in _shaped(out.get("detectability", []), list, ".diagnostics.detectability"):
        path = "diagnostics.detectability[]"
        row = _known(Detectability, _shaped(row, dict, f".{path}"), path, dropped)
        tools = _shaped(row.get("tools", []), list, f".{path}.tools")
        row["tools"] = [t for t in map(_tool, tools) if t]
        rows.append(row)
    resources = []
    for resource in _shaped(out.get("resources", []), list, ".diagnostics.resources"):
        resource = dict(_shaped(resource, dict, ".diagnostics.resources[]"))
        verified = {"method": resource.pop("verified_method", None)}
        verified["date"] = resource.pop("verified_date", None)
        resource["verified"] = verified
        resources.append(_known(Resource, resource, "diagnostics.resources[]", dropped))
    return {**out, "detectability": rows, "resources": resources}


def _values(item: dict[str, Any], dropped: list[str]) -> dict[str, Any]:
    """Map an export row to KGDB fields; ValueError for anything KGDB cannot hold as is."""
    if item["scope_name"] != SCOPE:
        raise ValueError(f"scope {item['scope_name']!r} is not {SCOPE!r}")
    if item["status"] != "active":
        raise ValueError(
            f"curation is {item['status']} in Gene Curator ({item.get('archive_reason')})"
        )
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
    evidence = _shaped(item.get("evidence") or {}, dict, "")
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
            external_id=_curation_id(item),
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
    return payload.model_dump(mode="json", exclude={"gene_symbol"})


def _curation_id(item: dict[str, Any]) -> str:
    return str(UUID(item["curation_id"]))  # one spelling for storage and lookup


def _import_row(
    db: Session, item: dict[str, Any], author: User, admin: User, report: dict[str, Any]
) -> None:
    ref = {
        "curation_id": _curation_id(item),
        "gene_symbol": item["approved_symbol"],
        "hgnc_id": item["hgnc_id"],
        "entity_key": item["entity_key"],
    }
    done = db.query(GDA.id).filter_by(source=SOURCE, external_id=ref["curation_id"]).scalar()
    if done:
        report["already_imported"].append({**ref, "record_id": done})
        return
    gene = db.query(Gene).filter(Gene.hgnc_id == item["hgnc_id"]).first()
    if gene is None:
        report["genes_not_in_kgdb"].append(ref)
        return
    dropped: list[str] = []
    try:
        values = _values(item, dropped)
    except (ValueError, TypeError, AttributeError) as e:
        report["rejected"].append({**ref, "reason": str(e)})
        return
    if dropped:
        report["dropped_fields"].append({**ref, "fields": sorted(set(dropped))})
    # The unique key: gene + disease + MOI (NULL MOIs equal) + relationship type (0018)
    moi = values["moi"]
    existing = (
        db.query(GDA)
        .filter(
            GDA.gene_id == gene.id,
            GDA.disease_id == values["disease_id"],
            GDA.moi.is_(None) if moi is None else GDA.moi == moi,
            GDA.relationship_type == values["relationship_type"],
        )
        .first()
    )
    if existing is not None:
        report["conflicts"].append(
            {
                **ref,
                "reason": "a KGDB record already exists for this gene, disease, MOI and "
                "relationship type; compare them",
                "existing_record_id": existing.id,
                "existing_source": existing.source,
                "existing_status": existing.status,
            }
        )
        return
    record = GDA(gene_id=gene.id, curator_id=author.id, status="draft", **values)
    db.add(record)
    try:
        _commit_unique(db, record, IMPORT, admin)  # event by the admin who uploaded
    except ResourceConflictError as e:  # a concurrent upload took the key
        report["conflicts"].append({**ref, "reason": e.message})
        return
    except (IntegrityError, DataError) as e:  # a database check the schema does not mirror
        db.rollback()
        report["rejected"].append({**ref, "reason": str(e.orig)})
        return
    report["created"].append({**ref, "record_id": record.id})


def import_export(db: Session, items: list[dict[str, Any]], admin: User) -> dict[str, Any]:
    """Create a draft per export row; nothing existing is changed."""
    report: dict[str, Any] = {
        "rows": len(items),
        "created": [],
        "already_imported": [],
        "conflicts": [],
        "rejected": [],
        "genes_not_in_kgdb": [],
        "dropped_fields": [],
    }
    author = import_account(db)
    for item in {_curation_id(i): i for i in items}.values():  # pages may overlap
        _import_row(db, item, author, admin, report)
    logger.sync_info(
        "Gene Curator import finished",
        rows=len(items),
        **{k: len(v) for k, v in report.items() if isinstance(v, list)},
    )
    return report
