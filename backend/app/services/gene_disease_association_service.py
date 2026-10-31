"""Workflow rules for expert-reviewed gene-disease associations (#26).

draft -> in_review -> published. Only the author edits or submits a draft; a
different curator/admin publishes or returns a record to draft. Published
records are immutable until a reviewer returns them to draft. Every action
appends the resulting record to gene_disease_association_events.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import PermissionDeniedError, ResourceConflictError
from app.core.exceptions import ValidationError as DomainValidationError
from app.crud.gene import gene_crud
from app.models.gene import Gene
from app.models.gene_disease_association import MOI_TERMS
from app.models.gene_disease_association import GeneDiseaseAssociation as GDA
from app.models.user import User
from app.schemas.gene_disease_association import (
    AssociationCreate,
    AssociationUpdate,
    ReviewDecision,
    check_classification,
    check_provenance,
)


def to_response(record: GDA) -> dict[str, Any]:
    data = {c.name: getattr(record, c.name) for c in GDA.__table__.columns}
    data["gene_symbol"] = record.gene.approved_symbol
    data["moi_label"] = MOI_TERMS.get(record.moi) if record.moi else None
    return data


def list_records(
    db: Session,
    *,
    published_only: bool,
    gene_symbol: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[GDA], int]:
    query = db.query(GDA).join(Gene, GDA.gene_id == Gene.id)
    if published_only:
        query = query.filter(GDA.status == "published")
    elif status:
        query = query.filter(GDA.status == status)
    if gene_symbol:
        query = query.filter(func.upper(Gene.approved_symbol) == gene_symbol.upper())
    total = query.count()
    rows = query.order_by(Gene.approved_symbol, GDA.disease_id).limit(limit).offset(offset).all()
    return rows, total


def _locked(db: Session, record_id: int) -> GDA:
    record = db.query(GDA).filter(GDA.id == record_id).with_for_update().first()
    if record is None:
        raise HTTPException(status_code=404, detail="Association not found")
    return record


def _require_status(record: GDA, *allowed: str) -> None:
    if record.status not in allowed:
        raise ResourceConflictError(
            "Association", f"status is '{record.status}', expected {' or '.join(allowed)}"
        )


def _require_author(record: GDA, user: User) -> None:
    if record.curator_id != user.id:
        raise PermissionDeniedError("record author", "editing or submitting this association")


def _require_reviewer(record: GDA, user: User) -> None:
    if record.curator_id == user.id:
        raise PermissionDeniedError("a reviewer other than the author", "reviewing this record")


def _require_seen(record: GDA, decision: ReviewDecision) -> None:
    # The reviewer must decide on the version they read, not one changed since (four eyes)
    if record.updated_at != decision.expected_updated_at:
        raise ResourceConflictError(
            "Association", "the record changed since you loaded it; reload and review it again"
        )


def _log(db: Session, record: GDA, action: str, user: User) -> None:
    """Stamp the new version and append the record as it is now to the event trace."""
    # Wall clock, not now(): updated_at is the version a reviewer confirms (_require_seen)
    record.updated_at = datetime.now(UTC)
    db.flush()
    db.execute(
        text(
            "INSERT INTO gene_disease_association_events (association_id, action, user_id, snapshot)"
            " SELECT id, :action, :user_id, to_jsonb(g) FROM gene_disease_associations g"
            " WHERE id = :id"
        ),
        {"id": record.id, "action": action, "user_id": user.id},
    )


def _ensure_unique(db: Session, record: GDA) -> None:
    """Gene + disease + MOI (NULL MOIs equal) + relationship type and source + external_id
    identify one record."""
    query = db.query(GDA.id).filter(
        GDA.gene_id == record.gene_id,
        GDA.disease_id == record.disease_id,
        GDA.moi.is_(None) if record.moi is None else GDA.moi == record.moi,
        GDA.relationship_type == record.relationship_type,
    )
    if record.id is not None:
        query = query.filter(GDA.id != record.id)
    if query.first():
        raise ResourceConflictError("Association", _duplicate(record))
    if record.external_id is not None:
        query = db.query(GDA.id).filter(
            GDA.source == record.source, GDA.external_id == record.external_id
        )
        if record.id is not None:
            query = query.filter(GDA.id != record.id)
        if query.first():
            raise ResourceConflictError(
                "Association", f"{record.source} record {record.external_id} is already imported"
            )


def _duplicate(record: GDA) -> str:
    moi = f" with MOI {record.moi}" if record.moi else " without an MOI"
    return f"{record.disease_id}{moi} is already recorded for gene as {record.relationship_type}"


def _commit_unique(db: Session, record: GDA, action: str, user: User) -> None:
    """Log and commit; a concurrent duplicate that passed _ensure_unique hits the unique key."""
    message = _duplicate(record)
    try:
        _log(db, record, action, user)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        if "uq_gda" not in str(e):  # only a unique key is a duplicate; re-raise check failures
            raise
        raise ResourceConflictError("Association", message) from e


def create(db: Session, payload: AssociationCreate, user: User) -> GDA:
    gene = gene_crud.get_by_symbol(db, payload.gene_symbol)
    if gene is None:
        raise DomainValidationError("gene_symbol", f"unknown gene '{payload.gene_symbol}'")
    record = GDA(
        gene_id=gene.id,
        curator_id=user.id,
        status="draft",
        # mode="json": diagnostics dates must be JSON-serialisable for JSONB
        **payload.model_dump(mode="json", exclude={"gene_symbol"}),
    )
    with db.no_autoflush:  # the new record must not match itself
        _ensure_unique(db, record)
    db.add(record)
    _commit_unique(db, record, "create", user)
    db.refresh(record)
    return record


def update(db: Session, record_id: int, payload: AssociationUpdate, user: User) -> GDA:
    record = _locked(db, record_id)
    _require_author(record, user)
    _require_status(record, "draft")
    changes = payload.model_dump(mode="json", exclude_unset=True)
    for key, value in changes.items():
        setattr(record, key, value)
    # A PATCH may change one side only (e.g. relationship_type): check the merged record
    try:
        check_classification(record.relationship_type, record.evidence_strength)
        check_provenance(record.source, record.external_id, record.external_url)
    except ValueError as e:
        db.rollback()
        raise DomainValidationError("association", str(e)) from e
    with db.no_autoflush:
        _ensure_unique(db, record)
    _commit_unique(db, record, "update", user)
    db.refresh(record)
    return record


def submit(db: Session, record_id: int, user: User) -> GDA:
    record = _locked(db, record_id)
    _require_author(record, user)
    _require_status(record, "draft")
    record.status = "in_review"
    record.submitted_at = datetime.now(UTC)
    _log(db, record, "submit", user)
    db.commit()
    db.refresh(record)
    return record


def publish(db: Session, record_id: int, decision: ReviewDecision, user: User) -> GDA:
    record = _locked(db, record_id)
    _require_status(record, "in_review")
    _require_reviewer(record, user)
    _require_seen(record, decision)
    now = datetime.now(UTC)
    record.status = "published"
    record.reviewer_id = user.id
    record.reviewed_at = now
    record.published_at = now
    _log(db, record, "publish", user)
    db.commit()
    db.refresh(record)
    return record


def return_to_draft(db: Session, record_id: int, decision: ReviewDecision, user: User) -> GDA:
    record = _locked(db, record_id)
    _require_status(record, "in_review", "published")
    _require_reviewer(record, user)
    _require_seen(record, decision)
    record.status = "draft"
    record.reviewer_id = user.id
    record.reviewed_at = datetime.now(UTC)
    record.submitted_at = None
    record.published_at = None
    _log(db, record, "return", user)
    db.commit()
    db.refresh(record)
    return record
