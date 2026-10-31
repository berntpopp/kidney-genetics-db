"""Admin-triggered import of Gene Curator curations as KGDB drafts (#448)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.services import gene_curator_import as service

router = APIRouter()


@router.post("/import")
def import_gene_curator(
    updated_since: datetime | None = Query(
        None,
        description="Incremental sync from this time (start a few minutes early). Omit for a "
        "full sync, which also retracts imported records Gene Curator no longer returns.",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Upsert the configured scope's curations as drafts and report what was not imported."""
    items = service.fetch_export(updated_since)
    return service.import_export(db, items, user, full=updated_since is None)
