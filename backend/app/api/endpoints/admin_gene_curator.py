"""Admin upload of a Gene Curator export, imported once as KGDB drafts (#448)."""

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.services import gene_curator_import as service

router = APIRouter()


@router.post("/import")
def import_gene_curator(
    file: UploadFile = File(
        ..., description="Gene Curator export v1: one CurationExportPage or a JSON list of pages"
    ),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Create a draft per curation and report what was skipped, rejected or not in KGDB."""
    items = service.parse_export(file.file.read(service.MAX_UPLOAD + 1))
    return service.import_export(db, items, user)
