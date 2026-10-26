"""Expert-reviewed gene-disease association endpoints (#26).

Public reads return published records only; every write and the workflow
listing require a curator or admin.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_curator
from app.models.user import User
from app.schemas.gene_disease_association import (
    AssociationCreate,
    AssociationList,
    AssociationResponse,
    AssociationStatus,
    AssociationUpdate,
)
from app.services import gene_disease_association_service as service

router = APIRouter()


def _page(rows: list[Any], total: int, limit: int, offset: int) -> dict[str, Any]:
    return {
        "data": [service.to_response(r) for r in rows],
        "meta": {"total": total, "limit": limit, "offset": offset},
    }


@router.get("/", response_model=AssociationList)
def list_published(
    db: Session = Depends(get_db),
    gene_symbol: str | None = Query(None, max_length=100, description="Approved gene symbol"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Published expert-reviewed associations (public)."""
    rows, total = service.list_records(
        db, published_only=True, gene_symbol=gene_symbol, status=None, limit=limit, offset=offset
    )
    return _page(rows, total, limit, offset)


@router.get("/workflow", response_model=AssociationList)
def list_workflow(
    db: Session = Depends(get_db),
    _: User = Depends(require_curator),
    gene_symbol: str | None = Query(None, max_length=100),
    status: AssociationStatus | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """All associations in any status (curators and admins)."""
    rows, total = service.list_records(
        db, published_only=False, gene_symbol=gene_symbol, status=status, limit=limit, offset=offset
    )
    return _page(rows, total, limit, offset)


@router.post("/", response_model=AssociationResponse, status_code=201)
def create_association(
    payload: AssociationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_curator),
) -> dict[str, Any]:
    return service.to_response(service.create(db, payload, user))


@router.patch("/{record_id}", response_model=AssociationResponse)
def update_association(
    record_id: int,
    payload: AssociationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_curator),
) -> dict[str, Any]:
    return service.to_response(service.update(db, record_id, payload, user))


@router.post("/{record_id}/submit", response_model=AssociationResponse)
def submit_association(
    record_id: int, db: Session = Depends(get_db), user: User = Depends(require_curator)
) -> dict[str, Any]:
    return service.to_response(service.submit(db, record_id, user))


@router.post("/{record_id}/publish", response_model=AssociationResponse)
def publish_association(
    record_id: int, db: Session = Depends(get_db), user: User = Depends(require_curator)
) -> dict[str, Any]:
    return service.to_response(service.publish(db, record_id, user))


@router.post("/{record_id}/return-to-draft", response_model=AssociationResponse)
def return_association_to_draft(
    record_id: int, db: Session = Depends(get_db), user: User = Depends(require_curator)
) -> dict[str, Any]:
    return service.to_response(service.return_to_draft(db, record_id, user))
